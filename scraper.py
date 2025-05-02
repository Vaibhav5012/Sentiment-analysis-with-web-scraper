import time
import threading
import random
from datetime import datetime  # Add this import
from concurrent.futures import ThreadPoolExecutor, as_completed
from PyQt5.QtCore import QThread, pyqtSignal
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
from utils import process_review_batch, is_non_review_content, thread_local

class ScraperThread(QThread):
    # Define signals at the class level
    progress_signal = pyqtSignal(str)
    finished_signal = pyqtSignal(list)
    error_signal = pyqtSignal(str)
    
    def __init__(self, url):
        super().__init__()
        self.url = url
        self.driver = None
        self.scroll_pause_time = 2.0  # Time to pause between scrolls
        self.max_scrolls = 15  # Maximum number of scrolls to perform
        
    
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
            
            # Add user agent to appear more like a real browser - use a more modern user agent
            chrome_options.add_argument("--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/96.0.4664.110 Safari/537.36")
            
            # Initialize the driver
            self.progress_signal.emit("Initializing web driver...")
            
            # Use standard ChromeDriverManager without cache_valid_range parameter
            self.driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=chrome_options)
            
            # Set window size explicitly to ensure consistent rendering - use a larger size
            self.driver.set_window_size(1920, 1080)

            # Navigate to the URL
            self.driver.get(self.url)
            self.progress_signal.emit("Waiting for page to load...")
            # Wait for page to load - increase initial wait time
            time.sleep(5)
            
            # Try to accept cookies if present (common blocker for scraping) - enhanced with more patterns
            try:
                # More comprehensive list of cookie acceptance patterns
                cookie_selectors = [
                    "//*[contains(text(), 'Accept') or contains(text(), 'I agree') or contains(text(), 'Allow') or contains(text(), 'Got it') or contains(text(), 'OK')]",
                    "//button[contains(@id, 'cookie') or contains(@class, 'cookie')]",
                    "//a[contains(@id, 'cookie') or contains(@class, 'cookie')]",
                    "//div[contains(@id, 'consent') or contains(@class, 'consent')]//button",
                    "//div[contains(@id, 'gdpr') or contains(@class, 'gdpr')]//button",
                    "//div[contains(@id, 'privacy') or contains(@class, 'privacy')]//button",
                    "//button[contains(@id, 'accept') or contains(@class, 'accept')]",
                    "//button[contains(@id, 'agree') or contains(@class, 'agree')]"
                ]
                
                for selector in cookie_selectors:
                    try:
                        cookie_buttons = self.driver.find_elements(By.XPATH, selector)
                        for button in cookie_buttons:
                            if button.is_displayed():
                                self.driver.execute_script("arguments[0].click();", button)
                                time.sleep(2)
                                self.progress_signal.emit("Accepted cookies/consent dialog")
                                break
                    except:
                        continue
            except Exception as e:
                print(f"Cookie button error: {e}")  # Log but continue
                
            # Enhanced auto-scroll implementation with random pauses
            self.progress_signal.emit("Starting to scroll and collect reviews...")
            
            # Scroll to load all content
            # Remove the nested function definition and use the class method instead
            self.progress_signal.emit("Scrolling to load content...")
            
            last_height = self.driver.execute_script("return document.body.scrollHeight")
            scroll_count = 0
            max_scrolls = 15  # Limit scrolling to prevent infinite loops
            
            while scroll_count < max_scrolls:
                # Scroll down to the bottom
                self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                
                # Wait for new content to load
                time.sleep(self.scroll_pause_time)
                
                # Calculate new scroll height and compare with last scroll height
                new_height = self.driver.execute_script("return document.body.scrollHeight")
                
                # If heights are the same, content might be fully loaded
                if new_height == last_height:
                    # Try one more scroll with longer wait time
                    self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                    time.sleep(self.scroll_pause_time * 2)
                    
                    # Check again
                    final_height = self.driver.execute_script("return document.body.scrollHeight")
                    if final_height == new_height:
                        # No more new content
                        break
                
                last_height = new_height
                scroll_count += 1
                self.progress_signal.emit(f"Scrolling page ({scroll_count}/{max_scrolls})...")
                
            self.progress_signal.emit(f"Completed {scroll_count} scrolls")
            
            # Expand review text if possible - try multiple patterns for "Read More" buttons
            try:
                self.progress_signal.emit("Expanding review texts...")
                expand_patterns = [
                    "//*[contains(text(), 'Read More')]",
                    "//*[contains(text(), '... More')]",
                    "//*[contains(text(), 'Show Full Review')]",
                    "//*[contains(text(), 'See More')]",
                    "//*[contains(text(), 'Continue Reading')]",
                    "//*[contains(text(), 'Expand Review')]",
                    "//*[contains(@class, 'expand')]",
                    "//*[contains(@class, 'more')]",
                    "//button[contains(@aria-label, 'expand')]",
                    "//a[contains(@class, 'read-more')]",
                    "//span[contains(@class, 'read-more')]"
                ]
                
                for pattern in expand_patterns:
                    expand_buttons = self.driver.find_elements(By.XPATH, pattern)
                    for button in expand_buttons:
                        if button.is_displayed():
                            try:
                                # Scroll to the button first
                                self.driver.execute_script("arguments[0].scrollIntoView({behavior: 'smooth', block: 'center'});", button)
                                time.sleep(0.5)
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
                "[data-testid*='review']", "[data-test*='review']",
                "div.review-content", "div.review-text", "div.review-body",
                "div[class*='reviewText']", "div[class*='reviewContent']",
                "div[class*='reviewBody']", "div[class*='review-text']",
                "div[class*='review-content']", "div[class*='review-body']"
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
            if len(reviews) < 10:
                self.progress_signal.emit("Trying direct text extraction...")
                
                # Comprehensive list of selectors for review content
                review_selectors = [
                    'div[class*="review-text"], div[class*="reviewText"], p[class*="review-text"]',
                    'div[data-hook="review-body"], span[class*="review-text"]',
                    'div[class*="review-content"], div[class*="reviewContent"]',
                    'p[class*="comment-content"], div[class*="commentContent"]',
                    'div[class*="userReview"], div[class*="user-review"]',
                    '.review-content p, .review-body p, .comment-body p',
                    'article p, .review p, .comment p',
                    'div[class*="comment"] p, div[class*="review"] p',
                    'div[class*="feedback"] p, div[class*="testimonial"] p',
                    'div[itemprop="reviewBody"], span[itemprop="reviewBody"]',
                    'div[class*="text-content"], div[class*="textContent"]',
                    'div[class*="description"], div[class*="content"]'
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
            
            # Move this outside the if block so it always runs
            # Add this code to process the reviews after extraction
            if len(reviews) > 0:
                self.progress_signal.emit(f"Found {len(reviews)} reviews, processing...")
                # Try alternative extraction if we found very few reviews
                if len(reviews) < 5:
                    self.progress_signal.emit("Found few reviews, trying alternative methods...")
                    alternative_reviews = self.extract_reviews_alternative()
                    reviews.update(alternative_reviews)
                    self.progress_signal.emit(f"Total reviews after alternative methods: {len(reviews)}")
                
                # Process the reviews
                self.process_reviews(reviews)
            else:
                self.progress_signal.emit("No reviews found, trying alternative extraction...")
                alternative_reviews = self.extract_reviews_alternative()
                if len(alternative_reviews) > 0:
                    self.progress_signal.emit(f"Found {len(alternative_reviews)} reviews with alternative methods")
                    self.process_reviews(alternative_reviews)
                else:
                    self.error_signal.emit("No reviews found on this page. Try a different URL.")
                    if self.driver:
                        self.driver.quit()
                        self.driver = None
                            
        except Exception as e:
            self.error_signal.emit(f"Failed to scrape URL: {str(e)}")
            if self.driver:
                self.driver.quit()
                self.driver = None
        
    def go_to_next_page(self):
            """Try to navigate to the next page of reviews"""
            try:
                # Common patterns for next page buttons
                next_page_selectors = [
                    "//a[contains(text(), 'Next')]",
                    "//button[contains(text(), 'Next')]",
                    "//a[contains(@class, 'next')]",
                    "//button[contains(@class, 'next')]",
                    "//a[contains(@aria-label, 'Next')]",
                    "//button[contains(@aria-label, 'Next')]",
                    "//a[contains(@rel, 'next')]",
                    "//li[contains(@class, 'next')]/a",
                    "//div[contains(@class, 'pagination')]//a[contains(@class, 'next')]",
                    "//div[contains(@class, 'pagination')]//button[contains(@class, 'next')]",
                    "//a[.//i[contains(@class, 'arrow') or contains(@class, 'next')]]",
                    "//button[.//i[contains(@class, 'arrow') or contains(@class, 'next')]]",
                    "//a[contains(@class, 'pagination-next')]",
                    "//button[contains(@class, 'pagination-next')]"
                ]
                
                for selector in next_page_selectors:
                    next_buttons = self.driver.find_elements(By.XPATH, selector)
                    for button in next_buttons:
                        if button.is_displayed() and button.is_enabled():
                            try:
                                # Scroll to the button first
                                self.driver.execute_script("arguments[0].scrollIntoView({behavior: 'smooth', block: 'center'});", button)
                                time.sleep(1)
                                self.driver.execute_script("arguments[0].click();", button)
                                time.sleep(3)  # Wait for the next page to load
                                return True
                            except:
                                continue
                
                return False
            except Exception as e:
                self.progress_signal.emit(f"Error navigating to next page: {str(e)}")
                return False
        
    def extract_reviews_alternative(self):
            """Alternative method to extract reviews when standard methods fail"""
            self.progress_signal.emit("Trying alternative review extraction methods...")
            reviews = set()
            
            try:
                # Try more aggressive XPath queries
                xpath_queries = [
                    "//div[string-length() > 100]",
                    "//p[string-length() > 80]",
                    "//span[string-length() > 100]",
                    "//article//p",
                    "//section//p",
                    "//main//p[string-length() > 50]",
                    "//*[contains(@class, 'review') or contains(@class, 'comment') or contains(@class, 'feedback')]//p",
                    "//*[contains(@class, 'review') or contains(@class, 'comment') or contains(@class, 'feedback')]//div[not(.//div)]",
                    "//*[contains(@id, 'review') or contains(@id, 'comment') or contains(@id, 'feedback')]//p",
                    "//div[contains(text(), '.') and string-length() > 100 and not(.//div)]"
                ]
                
                for query in xpath_queries:
                    elements = self.driver.find_elements(By.XPATH, query)
                    self.progress_signal.emit(f"Found {len(elements)} potential review elements with query: {query}")
                    
                    for element in elements:
                        text = element.text.strip()
                        if len(text) > 50 and len(text) < 3000:  # Reasonable review length
                            # Check if it looks like a review (contains periods, not just navigation text)
                            if "." in text and len(text.split()) > 10:
                                cleaned_text = ' '.join(text.split())
                                if not is_non_review_content(cleaned_text):
                                    reviews.add(cleaned_text)
                
                # If still no reviews, try to find any substantial text on the page
                if len(reviews) < 5:
                    self.progress_signal.emit("Still not enough reviews, trying to capture any substantial text...")
                    
                    # Get all text from the page body
                    body_text = self.driver.find_element(By.TAG_NAME, "body").text
                    
                    # Split by common separators and look for review-like chunks
                    potential_reviews = []
                    for separator in ["\n\n", "\n", ". ", "! ", "? "]:
                        chunks = body_text.split(separator)
                        for chunk in chunks:
                            if len(chunk) > 100 and len(chunk) < 2000:
                                potential_reviews.append(chunk)
                    
                    # Process potential reviews
                    for text in potential_reviews:
                        cleaned_text = ' '.join(text.split())
                        if len(cleaned_text) > 50 and "." in cleaned_text and not is_non_review_content(cleaned_text):
                            reviews.add(cleaned_text)
                            
                self.progress_signal.emit(f"Found {len(reviews)} potential reviews from page text")
                
            except Exception as e:
                self.progress_signal.emit(f"Error in alternative extraction: {str(e)}")
            
            return reviews
        
    def process_reviews(self, reviews):
        """Process the collected reviews"""
        self.progress_signal.emit(f"Analyzing {len(reviews)} reviews...")
        data = []
        
        # Check if we have any reviews to process
        if not reviews:
            self.error_signal.emit("No valid review data found on the page. Try a different URL or adjust the scraping settings.")
            if self.driver:
                self.driver.quit()
                self.driver = None
            return
                
        batch_size = 10
        review_list = list(reviews)
        
        # Add debug output
        self.progress_signal.emit(f"Processing {len(review_list)} reviews in batches of {batch_size}")
        
        # Process reviews in batches to avoid memory issues
        with ThreadPoolExecutor(max_workers=4) as executor:
            futures = []
            for i in range(0, len(review_list), batch_size):
                batch = review_list[i:i+batch_size]
                futures.append(executor.submit(process_review_batch, batch, self.url))
                
            # Collect results as they complete
            for i, future in enumerate(as_completed(futures)):
                try:
                    batch_results = future.result()
                    if batch_results:
                        data.extend(batch_results)
                        self.progress_signal.emit(f"Processed batch {i+1}/{len(futures)} - Found {len(batch_results)} valid reviews")
                    else:
                        self.progress_signal.emit(f"Batch {i+1}/{len(futures)} contained no valid reviews")
                except Exception as e:
                    self.progress_signal.emit(f"Error processing batch {i+1}: {str(e)}")
        
        # Add more detailed logging
        self.progress_signal.emit(f"Processing complete. Found {len(data)} valid reviews out of {len(reviews)} extracted texts")
        
        if data:
            self.finished_signal.emit(data)
            self.progress_signal.emit(f"Successfully processed {len(data)} reviews")
        else:
            self.error_signal.emit("No valid review data found on the page!")
        
        # Clean up
        if self.driver:
            self.driver.quit()
            self.driver = None
        
        
