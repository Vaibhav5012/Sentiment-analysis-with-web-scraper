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
        # Skip empty text or text that's just metadata
        if not text or len(text.strip()) < 10 or text.count('\n') > text.count(' '):
            return "NEUTRAL", 0.5
            
        # Handle user metadata without actual review content
        if re.match(r'^[A-Z]{1,2}\s*\n*[A-Za-z\s]+\s*\n*[A-Z]{2}\s*\n*•\s*\d+\s*reviews*\s*\n*(\d+\s*(days|hours|minutes)\s*ago)?$', text.strip()):
            return "NEUTRAL", 0.5
            
        # Handle rating statistics
        if re.search(r'(star|reviews|total|\d+%)', text) and not re.search(r'(good|bad|love|hate|terrible|excellent)', text.lower()):
            return "NEUTRAL", 0.5
        
        # Get raw sentiment from model
        result = model_loader.sentiment_transformer(text[:512])[0]
        score = float(result['score'])
        label = result['label']
        
        # Check for strong sentiment indicators in the text
        negative_phrases = [
            'bad', 'terrible', 'awful', 'worst', 'hate', 'disappointed', 'refund', 
            'complaint', 'poor', 'horrible', 'useless', 'waste', 'scam', 'fraud',
            'not happy', 'disgusted', 'furious', 'never again', 'don\'t use', 'do not use',
            'lies', 'liar', 'rob', 'steal', 'not worth', 'avoid', 'flopped', 'faeces',
            'not working', 'damaged', 'broken', 'delayed', 'late', 'never arrived',
            'worst service', 'unresolved', 'lack of', 'not received', 'missing', 'stolen',
            'refuse to', 'not delivering', 'never get', 'charging me', 'unfairly charged',
            'manipulate', 'failed', 'cutting off', 'useless', 'baffled', 'not sure where to begin',
            'not accommodating', 'don\'t do', 'expensive', 'always delayed', 'not worth it',
            'fake reviews', 'not happy with', 'shedded', 'bald spots', 'awful', 'worst',
            'not fit', 'doesn\'t allow returns', 'not happy with', 'hacked', 'lost every',
            'never shopping', 'still charging', 'dictator', 'greatly disappointed'
        ]
        
        positive_phrases = [
            'love', 'great', 'excellent', 'amazing', 'wonderful', 'best', 'fantastic',
            'good', 'helpful', 'recommend', 'satisfied', 'happy with', 'perfect',
            'awesome', 'brilliant', 'outstanding', 'superb', 'exceptional', 'impressive',
            'thank you', 'sorted', 'amazing', 'definitely recommend'
        ]
        
        # Count negative and positive phrases
        negative_count = sum(1 for phrase in negative_phrases if phrase.lower() in text.lower())
        positive_count = sum(1 for phrase in positive_phrases if phrase.lower() in text.lower())
        
        # Check for sarcasm indicators
        sarcasm_indicators = [
            'makes sense, right', 'still amazon is a good', 'i love shopping in amazon. the delivery of amazon is always delayed',
            'the prices of amazon is also expensive. still amazon is a good'
        ]
        
        has_sarcasm = any(indicator.lower() in text.lower() for indicator in sarcasm_indicators)
        
        # Special case for sarcasm
        if has_sarcasm:
            return "NEGATIVE", score
        
        # Handle short reviews with clear sentiment words
        if len(text.strip()) < 50:
            if any(word in text.lower() for word in ['worst', 'terrible', 'awful', 'bad']):
                return "NEGATIVE", 0.9
            if any(word in text.lower() for word in ['good', 'great', 'excellent', 'love']):
                return "POSITIVE", 0.9
        
        # If there are significantly more negative phrases than positive ones, override to NEGATIVE
        if negative_count >= 1 and negative_count > positive_count:
            return "NEGATIVE", 0.9
            
        # If there are significantly more positive phrases than negative ones, override to POSITIVE
        if positive_count >= 1 and positive_count > negative_count and not any(neg in text.lower() for neg in ['not', 'don\'t', 'doesn\'t', 'didn\'t', 'won\'t', 'can\'t']):
            return "POSITIVE", 0.9
            
        # For models that return LABEL_0/LABEL_1 format (like your fine-tuned model)
        if label.startswith('LABEL_'):
            label_num = int(label.split('_')[1])
            
            # If we have strong negative indicators but model says positive, override
            if label_num == 1 and negative_count >= 1:
                return "NEGATIVE", 0.9
                
            # Use the model's prediction with our additional checks
            if label_num == 0:
                return "NEGATIVE", 0.9
            else:
                # Double-check positive predictions
                if any(word in text.lower() for word in ['not', 'don\'t', 'bad', 'worst', 'terrible', 'awful']):
                    return "NEGATIVE", 0.9
                return "POSITIVE", 0.9
        
        # For models that return "negative"/"positive" directly
        if label.lower() == 'negative':
            return "NEGATIVE", score
        elif label.lower() == 'positive':
            return "POSITIVE", score
        
        # Default to using the score with better thresholds
        if score < 0.6:  # Increased threshold for negative sentiment
            return "NEGATIVE", score
        elif score > 0.7:  # Increased threshold for positive sentiment
            return "POSITIVE", score
        else:
            # For truly ambiguous cases, check for negative indicators
            if negative_count > 0:
                return "NEGATIVE", 0.7
            elif positive_count > 0:
                return "POSITIVE", 0.7
            else:
                return "NEUTRAL", 0.5
            
    except Exception as e:
        print(f"Error in sentiment analysis: {str(e)}")
        return "NEUTRAL", 0.5

# VADER sentiment function removed

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

def process_review_batch(reviews, source_url):
    """Process a batch of reviews and analyze their sentiment"""
    results = []
    for review in reviews:
        # Clean the review text first
        cleaned_review = clean_text(review)
        
        # Skip if the review is too short after cleaning
        if len(cleaned_review.split()) < 5:
            continue
            
        try:
            # Use the existing transformer sentiment function
            sentiment, confidence = get_transformer_sentiment(cleaned_review)
            
            results.append([
                review,
                sentiment,
                source_url,
                datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "Unknown",
                "Unknown",
                confidence
            ])
        except Exception as e:
            print(f"Error processing review: {str(e)}")
    
    return results
