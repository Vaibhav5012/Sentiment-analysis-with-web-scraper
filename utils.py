import re
import threading
from datetime import datetime
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import os
from models import model_loader

# Initialize thread-local storage
thread_local = threading.local()

def get_transformer_sentiment(text):
    try:
        result = model_loader.sentiment_transformer(text[:512])[0]
        score = float(result['score'])
        label = float(result['label'].split()[0])  # Convert '1/2/3/4/5
        
        # Adjust thresholds and confidence scaling
        if label >= 4.0:
            return "POSITIVE", score
        elif label <= 2.5:
            return "NEGATIVE", score
        else:
            return "NEUTRAL", score
    except Exception as e:
        return "NEUTRAL", 0.0

def get_vader_sentiment(text):
    scores = model_loader.vader_analyzer.polarity_scores(text)
    if scores['compound'] >= 0.1:
        return "POSITIVE", scores['compound']
    elif scores['compound'] <= -0.02:
        return "NEGATIVE", scores['compound']
    else:
        return "NEUTRAL", scores['compound']

def is_non_review_content(text):
    """Check if text is likely not a review but website navigation, footer, etc."""
    # Common patterns in non-review content
    non_review_patterns = [
        r'^Certified Buyer$',
        r'^\d+ months? ago$',
        r'^[0-5]★$',
        r'^\d+\.\d+★$',
        r'^Most (Helpful|Recent)$',
        r'^ABOUT Contact Us$',
        r'^Terms Of Use$',
        r'^Privacy$',
        r'^Copyright ©',
        r'^All Rights Reserved$',
    ]
    
    # Check if text matches any non-review pattern
    for pattern in non_review_patterns:
        if re.search(pattern, text, re.IGNORECASE):
            return True
    
    # Check for common website navigation elements (only if they appear alone)
    navigation_elements = [
        'home', 'about', 'contact', 'login', 'register', 'cart', 'checkout',
        'account', 'profile', 'settings', 'help', 'support', 'faq', 'search',
        'menu', 'categories', 'products', 'services', 'blog', 'news'
    ]
    
    # If text consists only of navigation elements, it's likely not a review
    words = text.lower().split()
    if words and len(words) <= 2 and all(word in navigation_elements for word in words):
        return True
            
    # Check if text is too short to be a meaningful review
    if len(text.split()) < 4:
        return True
    
    # Check if text contains too many non-alphabetic characters
    alpha_ratio = sum(c.isalpha() for c in text) / len(text) if text else 0
    if alpha_ratio < 0.4 and len(text) > 20:  # If less than 40% of chars are letters
        return True
    
    return False

def clean_csv_data(df):
    """
    Clean DataFrame by removing entries that are likely not reviews.
    
    Args:
        df (DataFrame): Pandas DataFrame containing review data
    
    Returns:
        DataFrame: Cleaned DataFrame with non-review content removed
    """
    if df is None or len(df) == 0:
        return df, 0
        
    # Define patterns for non-review content
    non_review_patterns = [
        # Navigation and category patterns
        r'^Shop by (Price|Features|Identity)',
        r'Under \d+',
        r'Above \d+',
        # Product listings
        r'^[a-zA-Z]+ (Headphones|Speakers|Earbuds|Soundbars|Smartwatch|Power Bank)',
        r'^\w+ [A-Z]\w+ \d+',
        # Footer content
        r'^© \d+ .* All Rights Reserved',
        r'^Address Unit No',
        r'^For Consumer Complaints',
        # Q&A sections that aren't reviews
        r'^Q\.\s',
        # Product specifications
        r'^Net Content \d+ UNIT',
        # Promotional content
        r'^Get \d+% OFF',
        r'^Redeem upto \d+% off',
        # Sort options and filters
        r'^Most Recent Highest Rating Lowest Rating',
        # Download instructions
        r'^Download user manual',
    ]
    
    # Function to check if a text matches any non-review pattern
    def is_not_review(text):
        if not isinstance(text, str):
            return True
            
        # Check against patterns
        for pattern in non_review_patterns:
            if re.search(pattern, text):
                return True
            
        # Check if it's a product description (long text with specifications)
        if len(text) > 100 and ('mAh' in text or 'Bluetooth' in text) and ('hours' in text.lower() or 'playback' in text.lower()):
            product_spec_indicators = ['equipped with', 'designed for', 'features', 'technology', 'battery capacity']
            if any(indicator in text.lower() for indicator in product_spec_indicators):
                return True
            
        # Check for website navigation elements
        nav_elements = ['home', 'about', 'contact', 'login', 'register', 'cart', 'checkout', 'search']
        words = text.lower().split()
        if len(words) <= 3 and any(word in nav_elements for word in words):
            return True
            
        # Check for product categories
        if text.count('|') > 0 and ('wireless' in text.lower() or 'bluetooth' in text.lower()):
            return True
            
        return False
    
    # Filter out non-review content
    original_count = len(df)
    df_cleaned = df[~df['text'].apply(is_not_review)]
    removed_count = original_count - len(df_cleaned)
    
    return df_cleaned, removed_count

def process_review_batch(reviews):
    """Process a batch of reviews to extract sentiment"""
    results = []
    
    # Initialize thread-local storage if not already done
    if not hasattr(thread_local, 'seen_texts'):
        thread_local.seen_texts = set()
    
    for text in reviews:
        # Skip empty or very short texts
        cleaned_text = ' '.join(text.split())
        if len(cleaned_text) < 20:
            continue
            
        # Skip if we've seen this text before
        if cleaned_text in thread_local.seen_texts:
            continue
        thread_local.seen_texts.add(cleaned_text)
        
        # Skip if text is likely not a review
        if is_non_review_content(cleaned_text):
            continue
            
        # Get sentiment from both analyzers
        vader_sentiment, vader_confidence = get_vader_sentiment(cleaned_text)
        transformer_sentiment, transformer_confidence = get_transformer_sentiment(cleaned_text)
        
        # Combine results - if both agree, use that sentiment
        # If they disagree, use the one with higher confidence
        if vader_sentiment == transformer_sentiment:
            sentiment = vader_sentiment
            confidence = max(vader_confidence, transformer_confidence)
        else:
            # If they disagree, use the one with higher confidence
            if abs(vader_confidence) > transformer_confidence:
                sentiment = vader_sentiment
                confidence = abs(vader_confidence)
            else:
                sentiment = transformer_sentiment
                confidence = transformer_confidence
        
        # Skip neutral reviews
        if sentiment == "NEUTRAL":
            continue
        
        # Extract source (website domain)
        source = "Web"
        
        # Current date/time
        current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        # Placeholder for user ID and location
        user_id = "Unknown"
        location = "Unknown"
        
        # Use the original text for the results to preserve context
        results.append([cleaned_text, sentiment, source, current_time, user_id, location, confidence])
    
    return results

def clean_text(text):
    """Clean review text by removing metadata and formatting"""
    # Remove user identifiers like "BO Bonnie US • 1 review 13 hours ago"
    text = re.sub(r'^[A-Z]{1,2}\s+[\w\s]+•\s+\d+\s+reviews?\s+.*?ago', '', text)
    # Remove date of experience
    text = re.sub(r'Date of experience:.*?$', '', text)
    # Remove "Useful Share" and similar endings
    text = re.sub(r'Useful\s+Share\s*$', '', text)
    # Remove any remaining leading/trailing whitespace
    text = text.strip()
    return text

def summarize_sentiment_results(csv_file):
    """Generate a summary of sentiment analysis results from a CSV file"""
    import pandas as pd
    import matplotlib.pyplot as plt
    import os
    
    try:
        # Load the data
        df = pd.read_csv(csv_file)
        
        # Check if DataFrame is empty
        if df.empty:
            return "No data available for analysis"
            
        # Make sure required columns exist
        required_columns = ['text', 'sentiment', 'confidence']
        for col in required_columns:
            if col not in df.columns:
                raise ValueError(f"Required column '{col}' not found in CSV file")
        
        # Count sentiment categories
        sentiment_counts = df['sentiment'].value_counts()
        total_reviews = len(df)
        
        # Calculate percentages
        if 'POSITIVE' in sentiment_counts:
            positive_percent = (sentiment_counts['POSITIVE'] / total_reviews) * 100
        else:
            positive_percent = 0
            
        if 'NEGATIVE' in sentiment_counts:
            negative_percent = (sentiment_counts['NEGATIVE'] / total_reviews) * 100
        else:
            negative_percent = 0
            
        if 'NEUTRAL' in sentiment_counts:
            neutral_percent = (sentiment_counts['NEUTRAL'] / total_reviews) * 100
        else:
            neutral_percent = 0
        
        # Print summary statistics
        print(f"Total reviews analyzed: {total_reviews}")
        print(f"Positive reviews: {sentiment_counts.get('POSITIVE', 0)} ({positive_percent:.1f}%)")
        print(f"Negative reviews: {sentiment_counts.get('NEGATIVE', 0)} ({negative_percent:.1f}%)")
        print(f"Neutral reviews: {sentiment_counts.get('NEUTRAL', 0)} ({neutral_percent:.1f}%)")
        
        # Calculate average confidence
        avg_confidence = df['confidence'].mean()
        print(f"Average confidence score: {avg_confidence:.2f}")
        
        # Generate visualization
        plt.figure(figsize=(12, 8))
        
        # Pie chart of sentiment distribution
        plt.subplot(2, 2, 1)
        sentiment_data = [
            sentiment_counts.get('POSITIVE', 0),
            sentiment_counts.get('NEGATIVE', 0),
            sentiment_counts.get('NEUTRAL', 0)
        ]
        labels = ['Positive', 'Negative', 'Neutral']
        colors = ['#4CAF50', '#F44336', '#2196F3']
        
        # Only create pie chart if there's data
        if sum(sentiment_data) > 0:
            plt.pie(sentiment_data, labels=labels, colors=colors, autopct='%1.1f%%', startangle=90)
            plt.title('Sentiment Distribution')
        else:
            plt.text(0.5, 0.5, "No sentiment data available", ha='center', va='center')
        
        # Bar chart of sentiment counts
        plt.subplot(2, 2, 2)
        plt.bar(labels, sentiment_data, color=colors)
        plt.title('Sentiment Counts')
        plt.ylabel('Number of Reviews')
        
        # Histogram of confidence scores
        plt.subplot(2, 2, 3)
        plt.hist(df['confidence'], bins=10, color='#9C27B0')
        plt.title('Confidence Score Distribution')
        plt.xlabel('Confidence Score')
        plt.ylabel('Number of Reviews')
        
        # Save the figure
        output_file = os.path.splitext(csv_file)[0] + '_analysis.png'
        plt.tight_layout()
        plt.savefig(output_file)
        
        return "Summary generated successfully"
    except Exception as e:
        print(f"Error generating summary: {str(e)}")
        return f"Error: {str(e)}"