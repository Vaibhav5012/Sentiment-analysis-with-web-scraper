# app.py
import os
os.environ["TF_CPP_MIN_LOG_LEVEL"] = "2"  # or "3" to suppress all TF logs
import sys
import nltk
from PyQt5.QtWidgets import QApplication

# Download required NLTK data
try:
    nltk.download('vader_lexicon', quiet=True)
except Exception as e:
    print(f"Warning: Failed to download NLTK data: {e}")

# Import the main UI class
from ui import SentimentAnalysisApp

# Main entry point
if __name__ == "__main__":
    # Check for command line arguments
    if len(sys.argv) > 1 and sys.argv[1] == "--scrape-only":
        # Run scraper directly if requested
        from scraper import run_standalone_scraper
        print("Starting standalone scraper...")
        url = sys.argv[2] if len(sys.argv) > 2 else input("Enter URL to scrape: ")
        run_standalone_scraper(url)
    else:
        # Start the UI application
        app = QApplication(sys.argv)
        window = SentimentAnalysisApp()
        window.show()
        sys.exit(app.exec_())