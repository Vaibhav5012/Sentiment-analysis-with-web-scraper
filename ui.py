import pandas as pd
import matplotlib.pyplot as plt
from wordcloud import WordCloud, STOPWORDS
import textwrap
import io
import os
import sys
from datetime import datetime
from PyQt5.QtWidgets import (QMainWindow, QVBoxLayout, QHBoxLayout, 
                            QPushButton, QLabel, QFileDialog, QMessageBox, 
                            QInputDialog, QWidget, QProgressDialog, QLineEdit, QFrame, 
                            QTabWidget, QTextEdit, QFileDialog, 
                            QVBoxLayout, QHBoxLayout, QPushButton, QLabel)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont, QPixmap
from models import SummarizerThread, QAThread
from scraper import ScraperThread
from utils import clean_csv_data, summarize_sentiment_results

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
        self.clean_button = QPushButton("Clean CSV")
        self.clean_button.clicked.connect(self.clean_loaded_csv)
        self.clean_button.setEnabled(False)
        
        action_layout.addWidget(self.scrape_button)
        action_layout.addWidget(self.load_button)
        action_layout.addWidget(self.clean_button)
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
        
        self.summary_button = QPushButton("Sentiment Summary")
        self.summary_button.clicked.connect(self.show_sentiment_summary)
        self.summary_button.setEnabled(False)
        
        analysis_row1.addWidget(self.sentiment_button)
        analysis_row1.addWidget(self.wordcloud_button)
        analysis_row1.addWidget(self.summary_button)
        main_layout.addLayout(analysis_row1)
        
        # Second row of analysis buttons
        analysis_row2 = QHBoxLayout()
        
        self.summarize_button = QPushButton("Summarize")
        self.summarize_button.clicked.connect(self.summarize_reviews)
        self.summarize_button.setEnabled(False)
        
        self.ask_button = QPushButton("Ask Questions")
        self.ask_button.clicked.connect(self.ask_questions)
        self.ask_button.setEnabled(False)
        
        analysis_row2.addWidget(self.summarize_button)
        analysis_row2.addWidget(self.ask_button)
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
        url = self.url_input.text().strip()
        if not url:
            QMessageBox.warning(self, "Input Error", "Please enter a valid URL")
            return
            
        # Disable buttons during scraping
        self.scrape_button.setEnabled(False)
        self.load_button.setEnabled(False)
        self.status_label.setText("Scraping website... Please wait.")
        
        # Create and start the scraper thread
        self.scraper_thread = ScraperThread(url)
        self.scraper_thread.progress_signal.connect(self.update_progress)
        self.scraper_thread.finished_signal.connect(self.process_scraped_data)
        self.scraper_thread.error_signal.connect(self.handle_scraper_error)
        self.scraper_thread.start()
        
    def update_progress(self, message):
        self.status_label.setText(message)
        
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
        self.ask_button.setEnabled(True)
        self.export_button.setEnabled(True)
        self.clean_button.setEnabled(True)
        
        # Update status
        review_count = len(self.df)
        positive_count = len(self.df[self.df["sentiment"] == "POSITIVE"])
        negative_count = len(self.df[self.df["sentiment"] == "NEGATIVE"])
        
        self.status_label.setText(f"Analysis ready: {review_count} reviews found ({positive_count} positive, {negative_count} negative). Removed {removed_count} non-review items.")
        
    def handle_scraper_error(self, error_message):
        self.scrape_button.setEnabled(True)
        self.load_button.setEnabled(True)
        self.status_label.setText("Ready")
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
        self.ask_button.setEnabled(has_data)
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
            self.ask_button.setEnabled(True)
            self.export_button.setEnabled(True)
            self.clean_button.setEnabled(True)
            
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
            
    def show_sentiment_summary(self):
        """Show a summary analysis of the sentiment data"""
        if self.df is None or len(self.df) == 0:
            QMessageBox.warning(self, "No Data", "No data available for analysis")
            return
        
        # Create a dialog to show the summary
        summary_dialog = QWidget()
        summary_dialog.setWindowTitle("Sentiment Analysis Summary")
        summary_dialog.setGeometry(150, 150, 800, 600)
        summary_layout = QVBoxLayout(summary_dialog)
        
        # Create a text area for the summary
        summary_text = QTextEdit()
        summary_text.setReadOnly(True)
        
        # Create an image label for the charts
        image_label = QLabel()
        image_label.setAlignment(Qt.AlignCenter)
        image_label.setMinimumHeight(400)
        
        # Add widgets to layout
        summary_layout.addWidget(summary_text)
        summary_layout.addWidget(image_label)
        
        # Show the dialog
        summary_dialog.show()
        
        # Redirect stdout to capture print output
        old_stdout = sys.stdout
        new_stdout = io.StringIO()
        sys.stdout = new_stdout
        
        try:
            # Save the current dataframe to a temporary CSV file
            temp_csv = "temp_summary.csv"
            self.df.to_csv(temp_csv, index=False)
            
            # Run the analysis
            from utils import summarize_sentiment_results
            summary = summarize_sentiment_results(temp_csv)
            
            # Get the captured output
            output = new_stdout.getvalue()
            summary_text.setText(output)
            
            # Display the generated image
            image_path = os.path.splitext(temp_csv)[0] + '_analysis.png'
            if os.path.exists(image_path):
                pixmap = QPixmap(image_path)
                image_label.setPixmap(pixmap.scaled(
                    image_label.width(), 
                    image_label.height(),
                    Qt.KeepAspectRatio,
                    Qt.SmoothTransformation
                ))
                
            # Clean up temporary files
            try:
                if os.path.exists(temp_csv):
                    os.remove(temp_csv)
                if os.path.exists(image_path):
                    # Keep the image file for now, can be removed later
                    pass
            except Exception as cleanup_error:
                print(f"Warning: Could not clean up temporary files: {cleanup_error}")
        except Exception as e:
            summary_text.setText(f"Error generating summary: {str(e)}")
        finally:
            # Restore stdout
            sys.stdout = old_stdout
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
        
        # Combine reviews into a single text
        combined_text = " ".join(reviews)
    
        # Show loading dialog
        self.progress_dialog = QProgressDialog("Generating summary...", "Cancel", 0, 100, self)
        self.progress_dialog.setWindowTitle("Summarizing Reviews")
        self.progress_dialog.setWindowModality(Qt.WindowModal)
        self.progress_dialog.setValue(10)
        self.progress_dialog.canceled.connect(self.cancel_summarization)
    
        # Calculate appropriate summary length
        max_length = min(150, len(combined_text.split()) // 2)
        min_length = min(30, max_length - 10)
    
        # Create and start the summarizer thread
        self.summarizer_thread = SummarizerThread(combined_text, max_length, min_length)
        self.summarizer_thread.progress_signal.connect(self.progress_dialog.setValue)
        self.summarizer_thread.finished_signal.connect(self.handle_summary_result)
        self.summarizer_thread.error_signal.connect(self.handle_summary_error)
        self.summarizer_thread.start()
    
        # Store the choice for later use
        self.current_summary_choice = choice

    def cancel_summarization(self):
        if hasattr(self, 'summarizer_thread') and self.summarizer_thread.isRunning():
            self.summarizer_thread.terminate()
            self.summarizer_thread.wait()
            
    def handle_summary_result(self, summary):
        # Format summary
        formatted_summary = textwrap.fill(summary, width=80)
    
        # Save summary to file
        filename = f"summary_{self.current_summary_choice.lower()}.txt"
        with open(filename, "w", encoding="utf-8") as f:
            f.write(formatted_summary)
    
        self.progress_dialog.setValue(100)
    
        # Show summary in message box
        QMessageBox.information(self, "Summary Generated", 
                          f"Summary for {self.current_summary_choice.lower()} reviews:\n\n{formatted_summary}\n\n"
                          f"Summary has been saved as '{filename}'")

    def handle_summary_error(self, error_message):
        self.progress_dialog.close()
        QMessageBox.critical(self, "Error", f"Failed to generate summary: {error_message}")

    def ask_questions(self):
        if self.df is None or len(self.df) == 0:
            QMessageBox.warning(self, "No Data", "No data available for questions")
            return
    
        # Ask user for their question
        question, ok = QInputDialog.getText(self, "Ask a Question", 
                                      "What would you like to know about these reviews?")
        if not ok or not question:
            return
    
        # Combine all reviews into a single context
        context = " ".join(self.df["text"].tolist())
    
        # Show loading dialog
        self.qa_progress_dialog = QProgressDialog("Finding answer...", "Cancel", 0, 100, self)
        self.qa_progress_dialog.setWindowTitle("Processing Question")
        self.qa_progress_dialog.setWindowModality(Qt.WindowModal)
        self.qa_progress_dialog.setValue(10)
        self.qa_progress_dialog.canceled.connect(self.cancel_qa)
    
        # Create and start the QA thread
        self.qa_thread = QAThread(question, context)
        self.qa_thread.progress_signal.connect(self.qa_progress_dialog.setValue)
        self.qa_thread.finished_signal.connect(self.handle_qa_result)
        self.qa_thread.error_signal.connect(self.handle_qa_error)
        self.qa_thread.start()
    
        # Store the question for later use
        self.current_question = question

    def cancel_qa(self):
        if hasattr(self, 'qa_thread') and self.qa_thread.isRunning():
            self.qa_thread.terminate()
            self.qa_thread.wait()

    def handle_qa_result(self, answer):
        # Format answer
        formatted_answer = textwrap.fill(answer['answer'], width=80)
        confidence = answer['score'] * 100
    
        self.qa_progress_dialog.setValue(100)
    
        # Show answer in message box
        QMessageBox.information(self, "Answer", 
                          f"Question: {self.current_question}\n\n"
                          f"Answer: {formatted_answer}\n\n"
                          f"Confidence: {confidence:.2f}%")

    def handle_qa_error(self, error_message):
        self.qa_progress_dialog.close()
        QMessageBox.critical(self, "Error", f"Failed to process question: {error_message}")

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