import time
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from PyQt5.QtCore import QThread, pyqtSignal
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from webdriver_manager.chrome import ChromeDriverManager
from utils import process_review_batch, is_non_review_content, thread_local

class ScraperThread(QThread):
    progress_signal = pyqtSignal(str)
    finished_signal = pyqtSignal(list)
    error_signal = pyqtSignal(str)
    
    def __init__(self, url):
        super().__init__()
        self.url = url
        self.driver = None 
        
    def run(self):
        try:
            # Setup Chrome options
            chrome_options = Options()
            chrome_options.add_argument("--headless=new")  # Run in headless mode
            chrome_options.add_argument("--no-sandbox")
            chrome_options.add_argument("--disable-dev-shm-usage")
            chrome_options.add_argument("--disable-extensions")
            chrome_options.add_argument("--disable-logging")
            chrome_options.add_argument("--disable-notifications")
            chrome_options.page_load_strategy = 'eager'  # Load faster by not waiting for all resources
            
            # More aggressive GPU disabling to prevent GLES errors
            chrome_options.add_argument("--disable-gpu")
            chrome_options.add_argument("--disable-software-rasterizer")
            chrome_options.add_argument("--disable-webgl")
            chrome_options.add_argument("--disable-accelerated-2d-canvas")
            chrome_options.add_argument("--disable-accelerated-video-decode")
            chrome_options.add_argument("--disable-gpu-compositing")
            chrome_options.add_argument("--disable-gl-extensions")  # Disable GL extensions
            chrome_options.add_argument("--disable-d3d11")  # Disable Direct3D 11
            chrome_options.add_argument("--disable-webrtc-hw-encoding")  # Disable WebRTC hardware encoding
            
            # Add user agent to appear more like a real browser
            chrome_options.add_argument("--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36")
            
            # Initialize the driver
            self.progress_signal.emit("Initializing web driver...")
            
            # Use standard ChromeDriverManager without cache_valid_range parameter
            self.driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=chrome_options)
            
            # Set window size explicitly to ensure consistent rendering
            self.driver.set_window_size(1366, 768)

            # Navigate to the URL
            self.driver.get(self.url)
            self.progress_signal.emit("Extracting review content...")
            # Wait for page to load - increase initial wait time
            time.sleep(5)
            
            # Try to accept cookies if present (common blocker for scraping)
            try:
                cookie_buttons = self.driver.find_elements(By.XPATH, 
                    "//*[contains(text(), 'Accept') or contains(text(), 'I agree') or contains(text(), 'Allow') or contains(text(), 'Got it') or contains(text(), 'OK')]")
                for button in cookie_buttons:
                    if button.is_displayed():
                        self.driver.execute_script("arguments[0].click();", button)
                        time.sleep(2)
            except Exception as e:
                print(f"Cookie button error: {e}")  # Log but continue
                
            # Enhanced auto-scroll implementation
            scroll_pause_time = 2.5  # Increased pause time
            max_scrolls = 15  # Reduced for reliability
            
            # Show progress
            self.progress_signal.emit("Starting to scroll and collect reviews...")
            
            # Scroll to load all content
            last_height = self.driver.execute_script("return document.body.scrollHeight")
            scroll_count = 0
            
            while scroll_count < max_scrolls:
                # Scroll down
                self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                
                # Wait for new content
                time.sleep(scroll_pause_time)
                
                # Calculate new scroll height and compare with last scroll height
                new_height = self.driver.execute_script("return document.body.scrollHeight")
                if new_height == last_height:
                    # Try to click "load more" or "show more" buttons if scrolling doesn't reveal new content
                    try:
                        more_buttons = self.driver.find_elements(By.XPATH, 
                            "//*[contains(text(), 'Show More') or contains(text(), 'Load More') or contains(text(), 'More Reviews') or contains(text(), 'View More')]")
                        clicked = False
                        for button in more_buttons:
                            if button.is_displayed():
                                self.driver.execute_script("arguments[0].click();", button)
                                time.sleep(3)
                                clicked = True
                                break
                                
                        # If we didn't click any buttons, try again with different selectors
                        if not clicked:
                            more_buttons = self.driver.find_elements(By.CSS_SELECTOR, 
                                "button[class*='more'], button[class*='load'], a[class*='more'], a[class*='load']")
                            for button in more_buttons:
                                if button.is_displayed():
                                    self.driver.execute_script("arguments[0].click();", button)
                                    time.sleep(3)
                                    break
                    except Exception as e:
                        print(f"Load more button error: {e}")  # Log but continue
                        
                    # If we've tried clicking buttons and height still doesn't change, we're at the end
                    new_height = self.driver.execute_script("return document.body.scrollHeight")
                    if new_height == last_height:
                        # Try one more scroll just to be sure
                        self.driver.execute_script("window.scrollTo(0, 0);")  # Scroll to top
                        time.sleep(1)
                        self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")  # Scroll to bottom
                        time.sleep(2)
                        new_height = self.driver.execute_script("return document.body.scrollHeight")
                        if new_height == last_height:
                            break
                
                last_height = new_height
                scroll_count += 1
                self.progress_signal.emit(f"Scrolling page... ({scroll_count}/{max_scrolls})")
        
            # Expand review text if possible - try multiple patterns for "Read More" buttons
            try:
                self.progress_signal.emit("Expanding review texts...")
                expand_patterns = [
                    "//*[contains(text(), 'Read More')]",
                    "//*[contains(text(), '... More')]",
                    "//*[contains(text(), 'Show Full Review')]",
                    "//*[contains(text(), 'See More')]",
                    "//*[contains(@class, 'expand')]",
                    "//*[contains(@class, 'more')]",
                    "//button[contains(@aria-label, 'expand')]"
                ]
                
                for pattern in expand_patterns:
                    expand_buttons = self.driver.find_elements(By.XPATH, pattern)
                    for button in expand_buttons:
                        if button.is_displayed():
                            try:
                                self.driver.execute_script("arguments[0].click();", button)
                                time.sleep(0.5)
                            except:
                                pass  # Continue if one button fails
            except Exception as e:
                print(f"Expand review error: {e}")  # Log but continue
        
            # Extract review content with improved selectors
            self.progress_signal.emit("Extracting review content...")
            
            # First try to identify the main review container
            reviews = set()  # Use set to avoid duplicates
            
            # Try to find review containers first - this is more reliable than individual elements
            container_selectors = [
                "div.review", "div.comment", "div.feedback", "div.testimonial",
                "div[class*='review']", "div[class*='comment']", "div[class*='feedback']",
                "div[itemprop='review']", "div[data-hook='review']",
                "li[class*='review']", "article[class*='review']",
                ".review-card", ".review-container", ".review-wrapper",
                "[data-testid*='review']", "[data-test*='review']"
            ]
            
            for selector in container_selectors:
                containers = self.driver.find_elements(By.CSS_SELECTOR, selector)
                if containers:
                    self.progress_signal.emit(f"Found {len(containers)} review containers with selector: {selector}")
                    for container in containers:
                        # Extract text from the container
                        text = container.text.strip()
                        if len(text) > 30:  # Only consider substantial text
                            reviews.add(text)
            
            # If we didn't find enough reviews with containers, try direct text extraction
            if len(reviews) < 5:
                self.progress_signal.emit("Trying direct text extraction...")
                
                # Comprehensive list of selectors for review content
                review_selectors = [
                    'div[class*="review-text"], div[class*="reviewText"], p[class*="review-text"]',
                    'div[data-hook="review-body"], span[class*="review-text"]',
                    'div[class*="review-content"], div[class*="reviewContent"]',
                    'p[class*="comment-content"], div[class*="commentContent"]',
                    'div[class*="userReview"], div[class*="user-review"]',
                    '.review-content p, .review-body p, .comment-body p',
                    'article p, .review p, .comment p'
                ]
                
                for selector in review_selectors:
                    elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                    if elements:
                        self.progress_signal.emit(f"Found {len(elements)} elements with selector: {selector}")
                        for element in elements:
                            text = element.text.strip()
                            if len(text) > 30:  # Only consider substantial text
                                cleaned_text = ' '.join(text.split())
                                if not is_non_review_content(cleaned_text):
                                    reviews.add(cleaned_text)
            
            # If still not enough reviews, try a more aggressive approach with XPath
            if len(reviews) < 5:
                self.progress_signal.emit("Trying XPath extraction...")
                
                # Try to find paragraphs with substantial text
                paragraphs = self.driver.find_elements(By.XPATH, "//p[string-length() > 50]")
                for p in paragraphs:
                    text = p.text.strip()
                    if len(text) > 30:
                        cleaned_text = ' '.join(text.split())
                        if not is_non_review_content(cleaned_text):
                            reviews.add(cleaned_text)
                
                # Try to find divs with substantial text that might be reviews
                divs = self.driver.find_elements(By.XPATH, "//div[string-length() > 100 and not(.//div)]")
                for div in divs:
                    text = div.text.strip()
                    if 50 < len(text) < 2000:  # Reasonable review length
                        cleaned_text = ' '.join(text.split())
                        if not is_non_review_content(cleaned_text):
                            reviews.add(cleaned_text)
            
            # Last resort: take a screenshot for debugging
            if len(reviews) < 5:
                self.progress_signal.emit("Taking screenshot for debugging...")
                try:
                    self.driver.save_screenshot("scraping_debug.png")
                    print("Screenshot saved as scraping_debug.png")
                except Exception as e:
                    print(f"Screenshot error: {e}")
                    
                # Try to get the entire page HTML
                page_source = self.driver.page_source
                with open("page_source.html", "w", encoding="utf-8") as f:
                    f.write(page_source)
                print("Page source saved as page_source.html")
                
                # Try one more extraction from the entire body
                body_text = self.driver.find_element(By.TAG_NAME, "body").text
                paragraphs = body_text.split('\n')
                for p in paragraphs:
                    if 50 < len(p) < 1000:  # Reasonable paragraph length
                        cleaned_text = ' '.join(p.split())
                        if not is_non_review_content(cleaned_text):
                            reviews.add(cleaned_text)
                    
            # Process reviews in parallel
            self.progress_signal.emit(f"Analyzing {len(reviews)} reviews...")
            data = []
            
            # Check if we have any reviews to process
            if not reviews:
                self.error_signal.emit("No valid review data found on the page. Try a different URL or adjust the scraping settings.")
                if self.driver:
                    self.driver.quit()
                    self.driver = None
                return
                
            batch_size = 7  # Adjust based on your needs
            review_batches = [list(reviews)[i:i + batch_size] for i in range(0, len(reviews), batch_size)]
            
            # Initialize thread-local storage before processing
            thread_local.seen_texts = set()
            
            # Ensure max_workers is at least 1
            max_workers = max(1, min(len(review_batches), 4))
            
            with ThreadPoolExecutor(max_workers=max_workers) as executor:
                future_to_batch = {executor.submit(process_review_batch, batch): batch 
                                for batch in review_batches}
                
                completed = 0
                for future in as_completed(future_to_batch):
                    try:
                        batch_results = future.result()
                        data.extend(batch_results)
                        completed += 1
                        self.progress_signal.emit(f"Processed {completed}/{len(review_batches)} batches...")
                    except Exception as e:
                        print(f"Batch processing failed: {e}")

            # Clean up
            self.driver.quit()
            self.driver = None
            
            if data:
                self.finished_signal.emit(data)
            else:
                self.error_signal.emit("No valid review data found on the page!")
                
        except Exception as e:
            self.error_signal.emit(f"Failed to scrape URL: {str(e)}")
            if self.driver:
                self.driver.quit()
                self.driver = None


# Add this function to your scraper.py file

def run_standalone_scraper(url):
    """Run the scraper directly from command line with enhanced settings"""
    import pandas as pd
    from datetime import datetime
    
    print(f"Scraping reviews from: {url}")
    
    # Create a scraper with more aggressive settings
    scraper = ScraperThread(url)
    
    # Override default settings for more thorough scraping
    scraper.max_pages = 10  # Increase from default
    scraper.scroll_pause_time = 2.0  # Slow down scrolling
    scraper.max_retries = 5  # More retries
    
    # Run the scraper synchronously
    try:
        print("Starting scraper with enhanced settings...")
        data = scraper.run_scraper()
        
        # Save results to CSV
        if data and len(data) > 0:
            df = pd.DataFrame(data, columns=["text", "sentiment", "source", "date", "user_id", "location", "confidence"])
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_file = f"scraped_reviews_{timestamp}.csv"
            df.to_csv(output_file, index=False)
            print(f"Successfully scraped {len(data)} reviews. Saved to {output_file}")
        else:
            print("No reviews were scraped. Try adjusting the URL or scraper settings.")
    except Exception as e:
        print(f"Error during scraping: {str(e)}")
    
    return "Scraping completed"