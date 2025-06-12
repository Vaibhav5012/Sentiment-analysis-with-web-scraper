import pandas as pd
import matplotlib.pyplot as plt
from wordcloud import WordCloud, STOPWORDS
import textwrap
import os
import sys
from datetime import datetime
from PyQt5.QtWidgets import (QMainWindow, QVBoxLayout, QHBoxLayout, 
                            QPushButton, QLabel, QFileDialog, QMessageBox, 
                            QInputDialog, QWidget, QProgressDialog, QLineEdit, QFrame, 
                            QTabWidget, QTextEdit)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont, QPixmap
from models import SummarizerThread
from scraper import ScraperThread
from utils import clean_csv_data

class SentimentAnalysisApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Website Sentiment Analysis")
        self.setGeometry(100, 100, 900, 600)
        self.setStyleSheet("""
            QMainWindow {
                background-color: #f8f8f8;
            }
            QLabel {
                color: #333333;
            }
            QPushButton {
                background-color: #4a86e8;
                color: white;
                border: none;
                border-radius: 3px;
                padding: 6px 12px;
            }
            QPushButton:hover {
                background-color: #3a76d8;
            }
            QPushButton:disabled {
                background-color: #cccccc;
                color: #888888;
            }
            QLineEdit {
                padding: 6px;
                border: 1px solid #cccccc;
                border-radius: 3px;
            }
        """)
        
        # Initialize data storage
        self.data = []
        self.df = None
        self.scraper_thread = None
        self.summarizer_thread = None
        self.progress_dialog = None
        
        # Create main widget and layout
        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        main_layout = QVBoxLayout(main_widget)
        main_layout.setContentsMargins(15, 15, 15, 15)
        main_layout.setSpacing(10)
        
        # Create header with title
        header_label = QLabel("Website Sentiment Analysis")
        header_label.setFont(QFont("Arial", 16, QFont.Bold))
        header_label.setAlignment(Qt.AlignCenter)
        main_layout.addWidget(header_label)
        
        # URL input section
        url_layout = QHBoxLayout()
        url_label = QLabel("URL:")
        self.url_input = QLineEdit()
        self.url_input.setPlaceholderText("https://www.example.com/reviews")
        url_layout.addWidget(url_label)
        url_layout.addWidget(self.url_input)
        main_layout.addLayout(url_layout)
        
        # Action buttons
        action_layout = QHBoxLayout()
        
        self.scrape_button = QPushButton("Scrape Website")
        self.scrape_button.clicked.connect(self.scrape_website)
        
        self.load_button = QPushButton("Load CSV")
        self.load_button.clicked.connect(self.load_csv)
        
        action_layout.addWidget(self.scrape_button)
        action_layout.addWidget(self.load_button)
        main_layout.addLayout(action_layout)
        
        # Add a separator line
        line = QFrame()
        line.setFrameShape(QFrame.HLine)
        line.setFrameShadow(QFrame.Sunken)
        main_layout.addWidget(line)
        
        # Analysis buttons
        analysis_label = QLabel("Analysis Tools")
        analysis_label.setFont(QFont("Arial", 14))
        analysis_label.setAlignment(Qt.AlignCenter)
        main_layout.addWidget(analysis_label)
        
        # First row of analysis buttons
        analysis_row1 = QHBoxLayout()
        
        self.sentiment_button = QPushButton("Sentiment Analysis")
        self.sentiment_button.clicked.connect(self.show_sentiment_analysis)
        self.sentiment_button.setEnabled(False)
        
        self.wordcloud_button = QPushButton("Word Cloud")
        self.wordcloud_button.clicked.connect(self.generate_wordcloud)
        self.wordcloud_button.setEnabled(False)
        
        analysis_row1.addWidget(self.sentiment_button)
        analysis_row1.addWidget(self.wordcloud_button)
        main_layout.addLayout(analysis_row1)
        
        # Second row of analysis buttons
        analysis_row2 = QHBoxLayout()
        
        self.summarize_button = QPushButton("Summarize")
        self.summarize_button.clicked.connect(self.summarize_reviews)
        self.summarize_button.setEnabled(False)
        
        analysis_row2.addWidget(self.summarize_button)
        main_layout.addLayout(analysis_row2)
        
        # Export button
        self.export_button = QPushButton("Export Results")
        self.export_button.clicked.connect(self.export_results)
        self.export_button.setEnabled(False)
        main_layout.addWidget(self.export_button)
        
        # Status label
        self.status_label = QLabel("Ready")
        self.status_label.setAlignment(Qt.AlignCenter)
        self.status_label.setStyleSheet("""
            padding: 5px;
            background-color: #f0f0f0;
            border: 1px solid #dddddd;
            border-radius: 3px;
        """)
        main_layout.addWidget(self.status_label)
        
        # Add a stretch at the end to push everything up
        main_layout.addStretch()

    def scrape_website(self):
        """Start scraping the website for reviews"""
        url = self.url_input.text().strip()
        
        if not url:
            QMessageBox.warning(self, "Input Error", "Please enter a valid URL")
            return
            
        # Create and configure the scraper thread
        self.scraper_thread = ScraperThread(url)
        
        # Connect signals properly
        self.scraper_thread.progress_signal.connect(self.update_progress)
        self.scraper_thread.finished_signal.connect(self.process_scraped_data)
        self.scraper_thread.error_signal.connect(self.handle_scraper_error)
        
        # Show progress dialog
        self.progress_dialog = QProgressDialog("Scraping website...", "Cancel", 0, 0, self)
        self.progress_dialog.setWindowTitle("Scraping")
        self.progress_dialog.setWindowModality(Qt.WindowModal)
        self.progress_dialog.setMinimumDuration(0)
        self.progress_dialog.canceled.connect(self.cancel_scraping)
        self.progress_dialog.show()
        
        # Start the scraper thread
        self.scraper_thread.start()
        
    def update_progress(self, message):
        self.status_label.setText(message)
        
    def cancel_scraping(self):
        """Cancel the scraping operation if it's running"""
        if hasattr(self, 'scraper_thread') and self.scraper_thread.isRunning():
            self.scraper_thread.terminate()
            self.scraper_thread.wait()
            self.status_label.setText("Scraping canceled")
            self.scrape_button.setEnabled(True)
            self.load_button.setEnabled(True)
    
    def process_scraped_data(self, data):
        self.data = data
        self.df = pd.DataFrame(data, columns=["text", "sentiment", "source", "date", "user_id", "location", "confidence"])
        
        # Automatically clean the data to remove non-review content
        self.status_label.setText("Cleaning scraped data...")
        cleaned_df, removed_count = clean_csv_data(self.df)
        
        # Update the dataframe and data with cleaned content
        self.df = cleaned_df
        self.data = self.df.values.tolist()
        
        # Re-enable buttons
        self.scrape_button.setEnabled(True)
        self.load_button.setEnabled(True)
        self.sentiment_button.setEnabled(True)
        self.wordcloud_button.setEnabled(True)
        self.summarize_button.setEnabled(True)
        self.export_button.setEnabled(True)
        
        # Update status
        review_count = len(self.df)
        positive_count = len(self.df[self.df["sentiment"] == "POSITIVE"])
        negative_count = len(self.df[self.df["sentiment"] == "NEGATIVE"])
        
        self.status_label.setText(f"Analysis ready: {review_count} reviews found ({positive_count} positive, {negative_count} negative). Removed {removed_count} non-review items.")
        
        # Close progress dialog
        if self.progress_dialog:
            self.progress_dialog.close()
        
    def handle_scraper_error(self, error_message):
        self.scrape_button.setEnabled(True)
        self.load_button.setEnabled(True)
        self.status_label.setText("Ready")
        
        # Close progress dialog
        if self.progress_dialog:
            self.progress_dialog.close()
            
        QMessageBox.critical(self, "Scraping Error", error_message)
        
    def clean_loaded_csv(self):
        """Clean the currently loaded CSV file to remove non-review content"""
        if self.df is None:
            QMessageBox.warning(self, "No Data", "Please load a CSV file first")
            return
        
        # Ask for confirmation
        reply = QMessageBox.question(self, "Clean CSV", 
                                "This will remove entries that appear to be website elements rather than actual reviews. Continue?",
                                QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
    
        if reply == QMessageBox.No:
            return
    
        self.status_label.setText("Cleaning CSV data...")
        cleaned_df, removed_count = clean_csv_data(self.df)
    
        self.df = cleaned_df
        self.data = self.df.values.tolist()
    
        review_count = len(self.df)
        positive_count = len(self.df[self.df["sentiment"] == "POSITIVE"])
        negative_count = len(self.df[self.df["sentiment"] == "NEGATIVE"])
    
        self.status_label.setText(f"CSV cleaned: {review_count} reviews ({positive_count} positive, {negative_count} negative). Removed {removed_count} non-review items.")
    
        # Enable analysis buttons if we have data
        has_data = len(self.df) > 0
        self.sentiment_button.setEnabled(has_data)
        self.wordcloud_button.setEnabled(has_data)
        self.summarize_button.setEnabled(has_data)
        self.export_button.setEnabled(has_data)
        
        QMessageBox.information(self, "CSV Cleaned", f"Successfully cleaned CSV file. Removed {removed_count} non-review entries.")
    
    def load_csv(self):
        file_path, _ = QFileDialog.getOpenFileName(self, "Open CSV File", "", "CSV Files (*.csv)")
        if not file_path:
            return
            
        try:
            self.df = pd.read_csv(file_path)
            required_columns = ["text", "sentiment"]
            
            # Check if required columns exist
            if not all(col in self.df.columns for col in required_columns):
                QMessageBox.warning(self, "Format Error", 
                                   "CSV file must contain 'text' and 'sentiment' columns")
                return
                
            # Add missing columns if needed
            if "source" not in self.df.columns:
                self.df["source"] = "Unknown"
            if "date" not in self.df.columns:
                self.df["date"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            if "user_id" not in self.df.columns:
                self.df["user_id"] = "Unknown"
            if "location" not in self.df.columns:
                self.df["location"] = "Unknown"
            if "confidence" not in self.df.columns:
                self.df["confidence"] = 0.5
                
            # Convert DataFrame back to list for consistency
            self.data = self.df.values.tolist()
            
            # Enable analysis buttons
            self.sentiment_button.setEnabled(True)
            self.wordcloud_button.setEnabled(True)
            self.summarize_button.setEnabled(True)
            self.export_button.setEnabled(True)
            
            # Update status
            review_count = len(self.df)
            positive_count = len(self.df[self.df["sentiment"] == "POSITIVE"])
            negative_count = len(self.df[self.df["sentiment"] == "NEGATIVE"])
            
            self.status_label.setText(f"Analysis ready: {review_count} reviews loaded ({positive_count} positive, {negative_count} negative)")
            
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to load CSV file: {str(e)}")
            
    def show_sentiment_analysis(self):
        if self.df is None or len(self.df) == 0:
            QMessageBox.warning(self, "No Data", "No data available for analysis")
            return
            
        # Count sentiments
        sentiment_counts = self.df["sentiment"].value_counts()
        
        # Create figure
        plt.figure(figsize=(10, 6))
        bars = plt.bar(sentiment_counts.index, sentiment_counts.values, color=["green", "red"])
        
        # Add count labels on top of bars
        for bar in bars:
            height = bar.get_height()
            plt.text(bar.get_x() + bar.get_width()/2., height + 0.1,
                    f'{height}', ha='center', va='bottom')
        
        plt.title("Sentiment Analysis Results")
        plt.xlabel("Sentiment")
        plt.ylabel("Count")
        plt.tight_layout()
        
        # Save and show the figure
        plt.savefig("sentiment_analysis.png")
        plt.close()
        
        QMessageBox.information(self, "Analysis Complete", 
                               "Sentiment analysis chart has been saved as 'sentiment_analysis.png'")
        
    def export_results(self):
        if self.df is None or len(self.df) == 0:
            QMessageBox.warning(self, "No Data", "No data available to export")
            return
            
        file_path, _ = QFileDialog.getSaveFileName(self, "Save Results", "", "CSV Files (*.csv)")
        if not file_path:
            return
            
        try:
            self.df.to_csv(file_path, index=False)
            QMessageBox.information(self, "Export Complete", f"Results exported to {file_path}")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to export results: {str(e)}")
            
    def generate_wordcloud(self):
        if self.df is None or len(self.df) == 0:
            QMessageBox.warning(self, "No Data", "No data available for analysis")
            return
            
        # Ask user which sentiment to analyze
        options = ["POSITIVE", "NEGATIVE", "ALL"]
        choice, ok = QInputDialog.getItem(self, "Select Sentiment", 
                                         "Generate word cloud for which sentiment?",
                                         options, 0, False)
        if not ok:
            return
            
        # Filter data based on choice
        if choice == "ALL":
            text = " ".join(self.df["text"])
        else:
            filtered_df = self.df[self.df["sentiment"] == choice]
            if len(filtered_df) == 0:
                QMessageBox.warning(self, "No Data", f"No {choice.lower()} reviews found")
                return
            text = " ".join(filtered_df["text"])
            
        # Generate word cloud
        stopwords = set(STOPWORDS)
        common_words = {"one", "will", "get", "also", "us", "may", "even", "much", "many", "would", "could", "though"}
        stopwords.update(common_words)
        
        wordcloud = WordCloud(width=800, height=400, background_color="white",
                             stopwords=stopwords, max_words=100).generate(text)
                             
        # Create figure
        plt.figure(figsize=(10, 6))
        plt.imshow(wordcloud, interpolation="bilinear")
        plt.axis("off")
        plt.tight_layout()
        
        # Save and show the figure
        filename = f"wordcloud_{choice.lower()}.png"
        plt.savefig(filename)
        plt.close()
        
        QMessageBox.information(self, "Word Cloud Generated", 
                               f"Word cloud has been saved as '{filename}'")
        
    def summarize_reviews(self):
        if self.df is None or len(self.df) == 0:
            QMessageBox.warning(self, "No Data", "No data available for summarization")
            return
        
        # Ask user which sentiment to summarize
        options = ["POSITIVE", "NEGATIVE", "ALL"]
        choice, ok = QInputDialog.getItem(self, "Select Sentiment", 
                                     "Generate summary for which sentiment?",
                                     options, 0, False)
        if not ok:
            return
        
        # Filter data based on choice
        if choice == "ALL":
            reviews = self.df["text"].tolist()
        else:
            filtered_df = self.df[self.df["sentiment"] == choice]
            if len(filtered_df) == 0:
                QMessageBox.warning(self, "No Data", f"No {choice.lower()} reviews found")
                return
            reviews = filtered_df["text"].tolist()
        
        # Combine reviews into a single text (limit to prevent memory issues)
        combined_text = " ".join(reviews[:50])  # Limit to first 50 reviews
        
        # Check if we have enough text to summarize
        if len(combined_text.strip()) < 100:
            QMessageBox.warning(self, "Insufficient Data", 
                               "Not enough text content to generate a meaningful summary.")
            return
    
        # Show loading dialog
        self.progress_dialog = QProgressDialog("Generating summary...", "Cancel", 0, 100, self)
        self.progress_dialog.setWindowTitle("Summarizing Reviews")
        self.progress_dialog.setWindowModality(Qt.WindowModal)
        self.progress_dialog.setValue(10)
        self.progress_dialog.canceled.connect(self.cancel_summarization)
        self.progress_dialog.show()
    
        # Calculate appropriate summary length
        word_count = len(combined_text.split())
        max_length = min(150, max(50, word_count // 4))
        min_length = min(30, max_length - 20)
    
        # Create and start the summarizer thread
        self.summarizer_thread = SummarizerThread(combined_text, max_length, min_length)
        self.summarizer_thread.progress_signal.connect(self.progress_dialog.setValue)
        self.summarizer_thread.finished_signal.connect(self.handle_summary_result)
        self.summarizer_thread.error_signal.connect(self.handle_summary_error)
        self.summarizer_thread.start()
    
        # Store the choice for later use
        self.current_summary_choice = choice

    def cancel_summarization(self):
        if hasattr(self, 'summarizer_thread') and self.summarizer_thread and self.summarizer_thread.isRunning():
            self.summarizer_thread.terminate()
            self.summarizer_thread.wait()
            self.status_label.setText("Summarization canceled")
            
    def handle_summary_result(self, summary):
        # Close progress dialog
        if self.progress_dialog:
            self.progress_dialog.close()
            
        # Format summary
        formatted_summary = textwrap.fill(summary, width=80)
    
        # Save summary to file
        filename = f"summary_{self.current_summary_choice.lower()}.txt"
        try:
            with open(filename, "w", encoding="utf-8") as f:
                f.write(formatted_summary)
        except Exception as e:
            print(f"Warning: Could not save summary to file: {str(e)}")
    
        # Show summary in message box
        QMessageBox.information(self, "Summary Generated", 
                          f"Summary for {self.current_summary_choice.lower()} reviews:\n\n{formatted_summary}\n\n"
                          f"Summary has been saved as '{filename}'")
        
        self.status_label.setText("Summary generation completed")

    def handle_summary_error(self, error_message):
        # Close progress dialog
        if self.progress_dialog:
            self.progress_dialog.close()
            
        self.status_label.setText("Summary generation failed")
        QMessageBox.critical(self, "Summarization Error", 
                           f"Failed to generate summary: {error_message}\n\n"
                           "This might be due to:\n"
                           "• Internet connection issues\n"
                           "• Model loading problems\n"
                           "• Insufficient text content\n\n"
                           "Please try again or check your internet connection.")