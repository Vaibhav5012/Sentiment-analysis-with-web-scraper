import pandas as pd
import matplotlib.pyplot as plt
from wordcloud import WordCloud, STOPWORDS
import textwrap
import os
import sys
import webbrowser
from datetime import datetime
from PyQt5.QtWidgets import (QMainWindow, QVBoxLayout, QHBoxLayout, 
                            QPushButton, QLabel, QFileDialog, QMessageBox, 
                            QInputDialog, QWidget, QProgressDialog, QLineEdit, QFrame, 
                            QTabWidget, QTextEdit, QScrollArea, QGridLayout, QGroupBox,
                            QSplitter, QProgressBar, QComboBox, QSpinBox, QCheckBox,
                            QToolTip, QApplication, QDialog)
from PyQt5.QtCore import Qt, QTimer, QPropertyAnimation, QEasingCurve, QRect, QThread, pyqtSignal
from PyQt5.QtGui import QFont, QPixmap, QPalette, QColor, QIcon, QPainter, QBrush, QDesktopServices
from PyQt5.QtCore import QUrl
from models import SummarizerThread
from scraper import ScraperThread
from utils import clean_csv_data

class DeploymentStatusThread(QThread):
    """Thread to check deployment status"""
    status_updated = pyqtSignal(dict)
    error_occurred = pyqtSignal(str)
    
    def __init__(self, deploy_id=None):
        super().__init__()
        self.deploy_id = deploy_id
        
    def run(self):
        try:
            # This would normally call the deployment status API
            # For now, we'll simulate the response
            status = {
                'status': 'ready',
                'deploy_url': 'https://example-site.netlify.app',
                'claim_url': 'https://app.netlify.com/sites/example-site/overview',
                'claimed': False
            }
            self.status_updated.emit(status)
        except Exception as e:
            self.error_occurred.emit(str(e))

class ClaimLinkDialog(QDialog):
    """Custom dialog for showing claim link information"""
    
    def __init__(self, claim_url, deploy_url, parent=None):
        super().__init__(parent)
        self.claim_url = claim_url
        self.deploy_url = deploy_url
        self.setup_ui()
        
    def setup_ui(self):
        self.setWindowTitle("🚀 Deployment Successful")
        self.setFixedSize(500, 300)
        self.setStyleSheet("""
            QDialog {
                background: white;
                border-radius: 10px;
            }
            QLabel {
                color: #2c3e50;
            }
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #2196F3, stop:1 #1976D2);
                color: white;
                border: none;
                border-radius: 6px;
                padding: 10px 20px;
                font-weight: 500;
                font-size: 11px;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #42A5F5, stop:1 #2196F3);
            }
            QPushButton:pressed {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #1976D2, stop:1 #1565C0);
            }
        """)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(30, 30, 30, 30)
        layout.setSpacing(20)
        
        # Success icon and title
        title_label = QLabel("🎉 Your site has been deployed successfully!")
        title_label.setFont(QFont("Segoe UI", 16, QFont.Bold))
        title_label.setStyleSheet("color: #4CAF50; margin-bottom: 10px;")
        title_label.setAlignment(Qt.AlignCenter)
        
        # Site URL section
        site_section = QGroupBox("🌐 Your Live Site")
        site_layout = QVBoxLayout(site_section)
        
        site_url_label = QLabel(f"<a href='{self.deploy_url}' style='color: #2196F3; text-decoration: none;'>{self.deploy_url}</a>")
        site_url_label.setOpenExternalLinks(True)
        site_url_label.setFont(QFont("Segoe UI", 11))
        site_url_label.setStyleSheet("padding: 10px; background: #f8f9fa; border-radius: 6px;")
        
        visit_button = QPushButton("🔗 Visit Your Site")
        visit_button.clicked.connect(lambda: self.open_url(self.deploy_url))
        
        site_layout.addWidget(site_url_label)
        site_layout.addWidget(visit_button)
        
        # Claim section
        claim_section = QGroupBox("🏠 Transfer to Your Account")
        claim_layout = QVBoxLayout(claim_section)
        
        claim_info = QLabel(
            "To manage this site from your own Netlify account, click the button below. "
            "This will transfer ownership to you and allow you to:\n\n"
            "• Manage deployments and settings\n"
            "• Connect your own domain\n"
            "• Access analytics and logs\n"
            "• Set up continuous deployment"
        )
        claim_info.setWordWrap(True)
        claim_info.setFont(QFont("Segoe UI", 10))
        claim_info.setStyleSheet("color: #666; line-height: 1.4;")
        
        claim_button = QPushButton("🎯 Claim Site in Netlify")
        claim_button.clicked.connect(lambda: self.open_url(self.claim_url))
        claim_button.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #4CAF50, stop:1 #45a049);
                color: white;
                border: none;
                border-radius: 6px;
                padding: 12px 20px;
                font-weight: 600;
                font-size: 11px;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #5CBF60, stop:1 #4CAF50);
            }
        """)
        
        claim_layout.addWidget(claim_info)
        claim_layout.addWidget(claim_button)
        
        # Close button
        close_button = QPushButton("✅ Done")
        close_button.clicked.connect(self.accept)
        close_button.setStyleSheet("""
            QPushButton {
                background: #6c757d;
                color: white;
                border: none;
                border-radius: 6px;
                padding: 10px 30px;
                font-weight: 500;
            }
            QPushButton:hover {
                background: #5a6268;
            }
        """)
        
        # Add all sections to layout
        layout.addWidget(title_label)
        layout.addWidget(site_section)
        layout.addWidget(claim_section)
        layout.addWidget(close_button, 0, Qt.AlignCenter)
        
    def open_url(self, url):
        """Open URL in default browser"""
        try:
            QDesktopServices.openUrl(QUrl(url))
        except Exception as e:
            QMessageBox.warning(self, "Error", f"Could not open URL: {str(e)}")

class ModernButton(QPushButton):
    def __init__(self, text, primary=False):
        super().__init__(text)
        self.primary = primary
        self.setMinimumHeight(45)
        self.setFont(QFont("Segoe UI", 10, QFont.Medium))
        self.setCursor(Qt.PointingHandCursor)
        self.update_style()
        
    def update_style(self):
        if self.primary:
            self.setStyleSheet("""
                QPushButton {
                    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                        stop:0 #4CAF50, stop:1 #45a049);
                    color: white;
                    border: none;
                    border-radius: 8px;
                    padding: 12px 24px;
                    font-weight: 600;
                    font-size: 11px;
                }
                QPushButton:hover {
                    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                        stop:0 #5CBF60, stop:1 #4CAF50);
                    transform: translateY(-1px);
                }
                QPushButton:pressed {
                    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                        stop:0 #45a049, stop:1 #3d8b40);
                }
                QPushButton:disabled {
                    background: #cccccc;
                    color: #888888;
                }
            """)
        else:
            self.setStyleSheet("""
                QPushButton {
                    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                        stop:0 #2196F3, stop:1 #1976D2);
                    color: white;
                    border: none;
                    border-radius: 8px;
                    padding: 12px 24px;
                    font-weight: 500;
                    font-size: 10px;
                }
                QPushButton:hover {
                    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                        stop:0 #42A5F5, stop:1 #2196F3);
                    transform: translateY(-1px);
                }
                QPushButton:pressed {
                    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                        stop:0 #1976D2, stop:1 #1565C0);
                }
                QPushButton:disabled {
                    background: #cccccc;
                    color: #888888;
                }
            """)

class StatsCard(QWidget):
    def __init__(self, title, value, color="#2196F3"):
        super().__init__()
        self.setFixedSize(180, 100)
        self.setStyleSheet(f"""
            QWidget {{
                background: white;
                border: 1px solid #e0e0e0;
                border-radius: 12px;
                border-left: 4px solid {color};
            }}
        """)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(15, 10, 15, 10)
        
        title_label = QLabel(title)
        title_label.setFont(QFont("Segoe UI", 9))
        title_label.setStyleSheet("color: #666666; font-weight: 500;")
        
        value_label = QLabel(str(value))
        value_label.setFont(QFont("Segoe UI", 18, QFont.Bold))
        value_label.setStyleSheet(f"color: {color}; margin-top: 5px;")
        
        layout.addWidget(title_label)
        layout.addWidget(value_label)
        layout.addStretch()

class SentimentAnalysisApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("🔍 Advanced Sentiment Analysis Tool")
        self.setGeometry(100, 100, 1200, 800)
        self.setMinimumSize(1000, 700)
        
        # Set application style
        self.setStyleSheet("""
            QMainWindow {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #f8f9fa, stop:1 #e9ecef);
            }
            QLabel {
                color: #2c3e50;
            }
            QLineEdit {
                padding: 12px 16px;
                border: 2px solid #e0e0e0;
                border-radius: 8px;
                font-size: 11px;
                background: white;
                selection-background-color: #2196F3;
            }
            QLineEdit:focus {
                border-color: #2196F3;
                outline: none;
            }
            QGroupBox {
                font-weight: 600;
                font-size: 12px;
                color: #2c3e50;
                border: 2px solid #e0e0e0;
                border-radius: 8px;
                margin-top: 10px;
                padding-top: 10px;
                background: white;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 8px 0 8px;
                background: white;
            }
            QComboBox {
                padding: 8px 12px;
                border: 2px solid #e0e0e0;
                border-radius: 6px;
                background: white;
                min-width: 120px;
            }
            QComboBox:focus {
                border-color: #2196F3;
            }
            QComboBox::drop-down {
                border: none;
                width: 20px;
            }
            QComboBox::down-arrow {
                image: none;
                border-left: 5px solid transparent;
                border-right: 5px solid transparent;
                border-top: 5px solid #666;
                margin-right: 5px;
            }
            QProgressBar {
                border: none;
                border-radius: 6px;
                background: #e0e0e0;
                height: 8px;
            }
            QProgressBar::chunk {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #4CAF50, stop:1 #8BC34A);
                border-radius: 6px;
            }
        """)
        
        # Initialize data storage
        self.data = []
        self.df = None
        self.scraper_thread = None
        self.summarizer_thread = None
        self.deployment_thread = None
        self.progress_dialog = None
        self.stats_cards = []
        
        self.setup_ui()
        
    def setup_ui(self):
        # Create main widget and layout
        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        main_layout = QVBoxLayout(main_widget)
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setSpacing(20)
        
        # Header section
        self.create_header(main_layout)
        
        # Create splitter for main content
        splitter = QSplitter(Qt.Horizontal)
        main_layout.addWidget(splitter)
        
        # Left panel - Input and controls
        left_panel = self.create_left_panel()
        splitter.addWidget(left_panel)
        
        # Right panel - Results and stats
        right_panel = self.create_right_panel()
        splitter.addWidget(right_panel)
        
        # Set splitter proportions
        splitter.setSizes([400, 600])
        
        # Status bar
        self.create_status_bar(main_layout)
        
    def create_header(self, layout):
        header_widget = QWidget()
        header_widget.setStyleSheet("""
            QWidget {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #667eea, stop:1 #764ba2);
                border-radius: 15px;
                padding: 20px;
            }
        """)
        header_widget.setFixedHeight(120)
        
        header_layout = QVBoxLayout(header_widget)
        header_layout.setContentsMargins(30, 20, 30, 20)
        
        title_label = QLabel("🔍 Advanced Sentiment Analysis Tool")
        title_label.setFont(QFont("Segoe UI", 24, QFont.Bold))
        title_label.setStyleSheet("color: white; margin-bottom: 5px;")
        
        subtitle_label = QLabel("Analyze customer sentiment from websites and CSV files with AI-powered insights")
        subtitle_label.setFont(QFont("Segoe UI", 12))
        subtitle_label.setStyleSheet("color: rgba(255, 255, 255, 0.9);")
        
        header_layout.addWidget(title_label)
        header_layout.addWidget(subtitle_label)
        header_layout.addStretch()
        
        layout.addWidget(header_widget)
        
    def create_left_panel(self):
        left_widget = QWidget()
        left_layout = QVBoxLayout(left_widget)
        left_layout.setContentsMargins(0, 0, 10, 0)
        
        # Data Input Section
        input_group = QGroupBox("📥 Data Input")
        input_layout = QVBoxLayout(input_group)
        input_layout.setSpacing(15)
        
        # URL input with better styling
        url_label = QLabel("🌐 Website URL:")
        url_label.setFont(QFont("Segoe UI", 10, QFont.Medium))
        
        self.url_input = QLineEdit()
        self.url_input.setPlaceholderText("https://www.example.com/reviews or product page")
        self.url_input.setToolTip("Enter the URL of a website with reviews or customer feedback")
        
        # Action buttons with icons
        button_layout = QHBoxLayout()
        
        self.scrape_button = ModernButton("🔍 Scrape Website", primary=True)
        self.scrape_button.clicked.connect(self.scrape_website)
        self.scrape_button.setToolTip("Extract and analyze reviews from the website")
        
        self.load_button = ModernButton("📁 Load CSV")
        self.load_button.clicked.connect(self.load_csv)
        self.load_button.setToolTip("Load previously saved review data from CSV file")
        
        button_layout.addWidget(self.scrape_button)
        button_layout.addWidget(self.load_button)
        
        input_layout.addWidget(url_label)
        input_layout.addWidget(self.url_input)
        input_layout.addLayout(button_layout)
        
        # Analysis Options Section
        options_group = QGroupBox("⚙️ Analysis Options")
        options_layout = QGridLayout(options_group)
        options_layout.setSpacing(10)
        
        # Sentiment filter
        sentiment_label = QLabel("Filter by Sentiment:")
        self.sentiment_filter = QComboBox()
        self.sentiment_filter.addItems(["All", "Positive", "Negative", "Neutral"])
        self.sentiment_filter.setToolTip("Filter results by sentiment type")
        
        # Word cloud options
        wordcloud_label = QLabel("Word Cloud Type:")
        self.wordcloud_type = QComboBox()
        self.wordcloud_type.addItems(["All Reviews", "Positive Only", "Negative Only"])
        
        # Summary length
        summary_label = QLabel("Summary Length:")
        self.summary_length = QComboBox()
        self.summary_length.addItems(["Short", "Medium", "Long"])
        self.summary_length.setCurrentText("Medium")
        
        options_layout.addWidget(sentiment_label, 0, 0)
        options_layout.addWidget(self.sentiment_filter, 0, 1)
        options_layout.addWidget(wordcloud_label, 1, 0)
        options_layout.addWidget(self.wordcloud_type, 1, 1)
        options_layout.addWidget(summary_label, 2, 0)
        options_layout.addWidget(self.summary_length, 2, 1)
        
        # Analysis Tools Section
        tools_group = QGroupBox("🔧 Analysis Tools")
        tools_layout = QVBoxLayout(tools_group)
        tools_layout.setSpacing(10)
        
        # Analysis buttons
        self.sentiment_button = ModernButton("📊 Sentiment Analysis")
        self.sentiment_button.clicked.connect(self.show_sentiment_analysis)
        self.sentiment_button.setEnabled(False)
        self.sentiment_button.setToolTip("Generate sentiment distribution charts and statistics")
        
        self.wordcloud_button = ModernButton("☁️ Generate Word Cloud")
        self.wordcloud_button.clicked.connect(self.generate_wordcloud)
        self.wordcloud_button.setEnabled(False)
        self.wordcloud_button.setToolTip("Create visual word cloud from review text")
        
        self.summarize_button = ModernButton("📝 Summarize Reviews")
        self.summarize_button.clicked.connect(self.summarize_reviews)
        self.summarize_button.setEnabled(False)
        self.summarize_button.setToolTip("Generate AI-powered summary of reviews")
        
        self.export_button = ModernButton("💾 Export Results")
        self.export_button.clicked.connect(self.export_results)
        self.export_button.setEnabled(False)
        self.export_button.setToolTip("Save analysis results to CSV file")
        
        # Add deployment button
        self.deploy_button = ModernButton("🚀 Deploy to Web")
        self.deploy_button.clicked.connect(self.deploy_to_web)
        self.deploy_button.setEnabled(False)
        self.deploy_button.setToolTip("Deploy your analysis results as a web dashboard")
        
        tools_layout.addWidget(self.sentiment_button)
        tools_layout.addWidget(self.wordcloud_button)
        tools_layout.addWidget(self.summarize_button)
        tools_layout.addWidget(self.export_button)
        tools_layout.addWidget(self.deploy_button)
        
        # Add all groups to left layout
        left_layout.addWidget(input_group)
        left_layout.addWidget(options_group)
        left_layout.addWidget(tools_group)
        left_layout.addStretch()
        
        return left_widget
        
    def create_right_panel(self):
        right_widget = QWidget()
        right_layout = QVBoxLayout(right_widget)
        right_layout.setContentsMargins(10, 0, 0, 0)
        
        # Statistics Section
        stats_group = QGroupBox("📈 Statistics Overview")
        stats_layout = QVBoxLayout(stats_group)
        
        # Stats cards container
        self.stats_container = QWidget()
        self.stats_layout = QHBoxLayout(self.stats_container)
        self.stats_layout.setSpacing(15)
        
        # Initialize empty stats
        self.update_stats_display(0, 0, 0)
        
        stats_layout.addWidget(self.stats_container)
        
        # Progress section
        progress_group = QGroupBox("⏳ Processing Status")
        progress_layout = QVBoxLayout(progress_group)
        
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        self.progress_bar.setTextVisible(True)
        
        self.status_label = QLabel("Ready to analyze data")
        self.status_label.setFont(QFont("Segoe UI", 10))
        self.status_label.setStyleSheet("""
            QLabel {
                padding: 12px;
                background: #f8f9fa;
                border: 1px solid #e9ecef;
                border-radius: 6px;
                color: #495057;
            }
        """)
        
        progress_layout.addWidget(self.progress_bar)
        progress_layout.addWidget(self.status_label)
        
        # Results preview section
        preview_group = QGroupBox("👁️ Data Preview")
        preview_layout = QVBoxLayout(preview_group)
        
        self.preview_text = QTextEdit()
        self.preview_text.setMaximumHeight(200)
        self.preview_text.setPlaceholderText("Review data will appear here after scraping or loading...")
        self.preview_text.setStyleSheet("""
            QTextEdit {
                border: 1px solid #e0e0e0;
                border-radius: 6px;
                padding: 10px;
                background: #fafafa;
                font-family: 'Consolas', 'Monaco', monospace;
                font-size: 9px;
            }
        """)
        
        preview_layout.addWidget(self.preview_text)
        
        # Add all groups to right layout
        right_layout.addWidget(stats_group)
        right_layout.addWidget(progress_group)
        right_layout.addWidget(preview_group)
        right_layout.addStretch()
        
        return right_widget
        
    def create_status_bar(self, layout):
        status_widget = QWidget()
        status_widget.setFixedHeight(40)
        status_widget.setStyleSheet("""
            QWidget {
                background: white;
                border-top: 1px solid #e0e0e0;
                border-radius: 0px;
            }
        """)
        
        status_layout = QHBoxLayout(status_widget)
        status_layout.setContentsMargins(20, 10, 20, 10)
        
        version_label = QLabel("v2.0 | Advanced Sentiment Analysis")
        version_label.setFont(QFont("Segoe UI", 9))
        version_label.setStyleSheet("color: #6c757d;")
        
        status_layout.addWidget(version_label)
        status_layout.addStretch()
        
        layout.addWidget(status_widget)
        
    def update_stats_display(self, total, positive, negative):
        # Clear existing stats cards
        for card in self.stats_cards:
            card.deleteLater()
        self.stats_cards.clear()
        
        # Create new stats cards
        total_card = StatsCard("Total Reviews", total, "#2196F3")
        positive_card = StatsCard("Positive", positive, "#4CAF50")
        negative_card = StatsCard("Negative", negative, "#F44336")
        
        self.stats_cards = [total_card, positive_card, negative_card]
        
        # Add cards to layout
        for card in self.stats_cards:
            self.stats_layout.addWidget(card)
        
        self.stats_layout.addStretch()
        
    def update_preview(self, data_sample):
        if not data_sample:
            self.preview_text.clear()
            return
            
        preview_text = "Sample Reviews:\n" + "="*50 + "\n\n"
        for i, review in enumerate(data_sample[:3]):  # Show first 3 reviews
            preview_text += f"Review {i+1}:\n"
            preview_text += f"Sentiment: {review[1]}\n"
            preview_text += f"Text: {review[0][:100]}...\n\n"
            
        self.preview_text.setPlainText(preview_text)

    def deploy_to_web(self):
        """Deploy the analysis results to a web dashboard"""
        if self.df is None or len(self.df) == 0:
            QMessageBox.warning(self, "No Data", "No data available to deploy")
            return
            
        # Show progress
        self.progress_bar.setVisible(True)
        self.progress_bar.setRange(0, 0)  # Indeterminate progress
        self.status_label.setText("🚀 Preparing deployment...")
        
        # Disable deploy button
        self.deploy_button.setEnabled(False)
        
        # Create deployment status thread
        self.deployment_thread = DeploymentStatusThread()
        self.deployment_thread.status_updated.connect(self.handle_deployment_status)
        self.deployment_thread.error_occurred.connect(self.handle_deployment_error)
        
        # Start deployment process
        self.deployment_thread.start()
        
    def handle_deployment_status(self, status):
        """Handle deployment status updates"""
        self.progress_bar.setVisible(False)
        self.deploy_button.setEnabled(True)
        
        if status.get('status') == 'ready':
            deploy_url = status.get('deploy_url', '')
            claim_url = status.get('claim_url', '')
            claimed = status.get('claimed', False)
            
            self.status_label.setText("✅ Deployment successful!")
            
            if claimed:
                # Site was already claimed, show simple success message
                QMessageBox.information(
                    self, 
                    "🚀 Deployment Complete", 
                    f"Your sentiment analysis dashboard has been deployed!\n\n"
                    f"🌐 Live URL: {deploy_url}\n\n"
                    "A new site with a new URL was deployed since the previous one was already claimed."
                )
                # Open the deployed site
                QDesktopServices.openUrl(QUrl(deploy_url))
            else:
                # Show claim dialog
                if claim_url and deploy_url:
                    dialog = ClaimLinkDialog(claim_url, deploy_url, self)
                    dialog.exec_()
                else:
                    # Fallback if URLs are missing
                    QMessageBox.information(
                        self, 
                        "🚀 Deployment Complete", 
                        "Your sentiment analysis dashboard has been deployed successfully!"
                    )
        else:
            self.status_label.setText("❌ Deployment failed")
            QMessageBox.warning(self, "Deployment Error", "Deployment failed. Please try again.")
            
    def handle_deployment_error(self, error_message):
        """Handle deployment errors"""
        self.progress_bar.setVisible(False)
        self.deploy_button.setEnabled(True)
        self.status_label.setText("❌ Deployment failed")
        
        QMessageBox.critical(
            self, 
            "Deployment Error", 
            f"Failed to deploy your dashboard:\n\n{error_message}\n\n"
            "Please check your internet connection and try again."
        )

    def scrape_website(self):
        """Start scraping the website for reviews"""
        url = self.url_input.text().strip()
        
        if not url:
            QMessageBox.warning(self, "Input Error", 
                               "Please enter a valid URL\n\nExample: https://www.amazon.com/product-reviews/...")
            return
            
        # Show progress
        self.progress_bar.setVisible(True)
        self.progress_bar.setRange(0, 0)  # Indeterminate progress
        self.status_label.setText("🔍 Initializing web scraper...")
        
        # Disable buttons
        self.scrape_button.setEnabled(False)
        self.load_button.setEnabled(False)
        
        # Create and configure the scraper thread
        self.scraper_thread = ScraperThread(url)
        
        # Connect signals properly
        self.scraper_thread.progress_signal.connect(self.update_progress)
        self.scraper_thread.finished_signal.connect(self.process_scraped_data)
        self.scraper_thread.error_signal.connect(self.handle_scraper_error)
        
        # Start the scraper thread
        self.scraper_thread.start()
        
    def update_progress(self, message):
        self.status_label.setText(f"🔄 {message}")
        
    def cancel_scraping(self):
        """Cancel the scraping operation if it's running"""
        if hasattr(self, 'scraper_thread') and self.scraper_thread.isRunning():
            self.scraper_thread.terminate()
            self.scraper_thread.wait()
            self.status_label.setText("❌ Scraping canceled")
            self.progress_bar.setVisible(False)
            self.scrape_button.setEnabled(True)
            self.load_button.setEnabled(True)
    
    def process_scraped_data(self, data):
        self.data = data
        self.df = pd.DataFrame(data, columns=["text", "sentiment", "source", "date", "user_id", "location", "confidence"])
        
        # Update progress
        self.status_label.setText("🧹 Cleaning scraped data...")
        
        # Automatically clean the data to remove non-review content
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
        self.deploy_button.setEnabled(True)  # Enable deploy button
        
        # Update statistics
        review_count = len(self.df)
        positive_count = len(self.df[self.df["sentiment"] == "POSITIVE"])
        negative_count = len(self.df[self.df["sentiment"] == "NEGATIVE"])
        
        self.update_stats_display(review_count, positive_count, negative_count)
        self.update_preview(self.data)
        
        # Hide progress bar and update status
        self.progress_bar.setVisible(False)
        self.status_label.setText(f"✅ Analysis ready: {review_count} reviews found ({positive_count} positive, {negative_count} negative). Removed {removed_count} non-review items.")
        
        # Show success message
        QMessageBox.information(self, "Scraping Complete", 
                               f"Successfully scraped and analyzed {review_count} reviews!\n\n"
                               f"• Positive reviews: {positive_count}\n"
                               f"• Negative reviews: {negative_count}\n"
                               f"• Removed non-review items: {removed_count}\n\n"
                               "You can now use the analysis tools.")
        
    def handle_scraper_error(self, error_message):
        self.scrape_button.setEnabled(True)
        self.load_button.setEnabled(True)
        self.progress_bar.setVisible(False)
        self.status_label.setText("❌ Scraping failed")
        
        QMessageBox.critical(self, "Scraping Error", 
                           f"Failed to scrape the website:\n\n{error_message}\n\n"
                           "Possible solutions:\n"
                           "• Check if the URL is correct and accessible\n"
                           "• Ensure the website contains reviews\n"
                           "• Try a different review page\n"
                           "• Check your internet connection")
        
    def load_csv(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self, 
            "Open CSV File", 
            "", 
            "CSV Files (*.csv);;All Files (*)"
        )
        if not file_path:
            return
            
        try:
            self.status_label.setText("📁 Loading CSV file...")
            self.progress_bar.setVisible(True)
            self.progress_bar.setRange(0, 0)
            
            self.df = pd.read_csv(file_path)
            required_columns = ["text", "sentiment"]
            
            # Check if required columns exist
            if not all(col in self.df.columns for col in required_columns):
                self.progress_bar.setVisible(False)
                QMessageBox.warning(self, "Format Error", 
                                   "CSV file must contain 'text' and 'sentiment' columns\n\n"
                                   "Expected format:\n"
                                   "text,sentiment\n"
                                   "\"Great product!\",POSITIVE\n"
                                   "\"Not satisfied\",NEGATIVE")
                return
                
            # Add missing columns if needed
            if "source" not in self.df.columns:
                self.df["source"] = "CSV Import"
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
            self.deploy_button.setEnabled(True)  # Enable deploy button
            
            # Update statistics
            review_count = len(self.df)
            positive_count = len(self.df[self.df["sentiment"] == "POSITIVE"])
            negative_count = len(self.df[self.df["sentiment"] == "NEGATIVE"])
            
            self.update_stats_display(review_count, positive_count, negative_count)
            self.update_preview(self.data)
            
            # Hide progress and update status
            self.progress_bar.setVisible(False)
            self.status_label.setText(f"✅ CSV loaded: {review_count} reviews ({positive_count} positive, {negative_count} negative)")
            
            QMessageBox.information(self, "CSV Loaded", 
                                   f"Successfully loaded {review_count} reviews from CSV file!")
            
        except Exception as e:
            self.progress_bar.setVisible(False)
            self.status_label.setText("❌ Failed to load CSV")
            QMessageBox.critical(self, "Error", f"Failed to load CSV file:\n\n{str(e)}")
            
    def show_sentiment_analysis(self):
        if self.df is None or len(self.df) == 0:
            QMessageBox.warning(self, "No Data", "No data available for analysis")
            return
            
        self.status_label.setText("📊 Generating sentiment analysis chart...")
        
        # Count sentiments
        sentiment_counts = self.df["sentiment"].value_counts()
        
        # Create figure with better styling
        plt.style.use('seaborn-v0_8')
        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(15, 6))
        
        # Bar chart
        colors = ['#4CAF50' if x == 'POSITIVE' else '#F44336' if x == 'NEGATIVE' else '#FF9800' 
                 for x in sentiment_counts.index]
        bars = ax1.bar(sentiment_counts.index, sentiment_counts.values, color=colors, alpha=0.8)
        
        # Add count labels on top of bars
        for bar in bars:
            height = bar.get_height()
            ax1.text(bar.get_x() + bar.get_width()/2., height + 0.1,
                    f'{int(height)}', ha='center', va='bottom', fontweight='bold')
        
        ax1.set_title("Sentiment Distribution", fontsize=14, fontweight='bold')
        ax1.set_xlabel("Sentiment", fontweight='bold')
        ax1.set_ylabel("Count", fontweight='bold')
        ax1.grid(True, alpha=0.3)
        
        # Pie chart
        ax2.pie(sentiment_counts.values, labels=sentiment_counts.index, colors=colors,
                autopct='%1.1f%%', startangle=90, textprops={'fontweight': 'bold'})
        ax2.set_title("Sentiment Percentage", fontsize=14, fontweight='bold')
        
        plt.tight_layout()
        
        # Save and show the figure
        filename = "sentiment_analysis.png"
        plt.savefig(filename, dpi=300, bbox_inches='tight')
        plt.close()
        
        self.status_label.setText("✅ Sentiment analysis complete")
        
        QMessageBox.information(self, "Analysis Complete", 
                               f"Sentiment analysis chart has been saved as '{filename}'\n\n"
                               f"Summary:\n"
                               f"• Total reviews: {len(self.df)}\n" +
                               "\n".join([f"• {sentiment}: {count} ({count/len(self.df)*100:.1f}%)" 
                                        for sentiment, count in sentiment_counts.items()]))
        
    def export_results(self):
        if self.df is None or len(self.df) == 0:
            QMessageBox.warning(self, "No Data", "No data available to export")
            return
            
        file_path, _ = QFileDialog.getSaveFileName(
            self, 
            "Save Results", 
            f"sentiment_analysis_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv", 
            "CSV Files (*.csv);;All Files (*)"
        )
        if not file_path:
            return
            
        try:
            self.status_label.setText("💾 Exporting results...")
            self.df.to_csv(file_path, index=False)
            self.status_label.setText("✅ Export complete")
            QMessageBox.information(self, "Export Complete", 
                                   f"Results successfully exported to:\n{file_path}")
        except Exception as e:
            self.status_label.setText("❌ Export failed")
            QMessageBox.critical(self, "Error", f"Failed to export results:\n\n{str(e)}")
            
    def generate_wordcloud(self):
        if self.df is None or len(self.df) == 0:
            QMessageBox.warning(self, "No Data", "No data available for analysis")
            return
            
        # Use the selected option from combo box
        choice_map = {"All Reviews": "ALL", "Positive Only": "POSITIVE", "Negative Only": "NEGATIVE"}
        choice = choice_map[self.wordcloud_type.currentText()]
            
        self.status_label.setText(f"☁️ Generating {choice.lower()} word cloud...")
        
        # Filter data based on choice
        if choice == "ALL":
            text = " ".join(self.df["text"])
        else:
            filtered_df = self.df[self.df["sentiment"] == choice]
            if len(filtered_df) == 0:
                QMessageBox.warning(self, "No Data", f"No {choice.lower()} reviews found")
                return
            text = " ".join(filtered_df["text"])
            
        # Generate word cloud with better styling
        stopwords = set(STOPWORDS)
        common_words = {"one", "will", "get", "also", "us", "may", "even", "much", "many", "would", "could", "though"}
        stopwords.update(common_words)
        
        # Choose color scheme based on sentiment
        if choice == "POSITIVE":
            colormap = "Greens"
        elif choice == "NEGATIVE":
            colormap = "Reds"
        else:
            colormap = "viridis"
        
        wordcloud = WordCloud(
            width=1200, height=600, 
            background_color="white",
            stopwords=stopwords, 
            max_words=150,
            colormap=colormap,
            relative_scaling=0.5,
            min_font_size=10
        ).generate(text)
                             
        # Create figure
        plt.figure(figsize=(15, 8))
        plt.imshow(wordcloud, interpolation="bilinear")
        plt.axis("off")
        plt.title(f"Word Cloud - {choice.title()} Reviews", fontsize=16, fontweight='bold', pad=20)
        plt.tight_layout()
        
        # Save and show the figure
        filename = f"wordcloud_{choice.lower()}.png"
        plt.savefig(filename, dpi=300, bbox_inches='tight')
        plt.close()
        
        self.status_label.setText("✅ Word cloud generated")
        
        QMessageBox.information(self, "Word Cloud Generated", 
                               f"Word cloud has been saved as '{filename}'\n\n"
                               f"The visualization shows the most frequently used words in {choice.lower()} reviews.")
        
    def summarize_reviews(self):
        if self.df is None or len(self.df) == 0:
            QMessageBox.warning(self, "No Data", "No data available for summarization")
            return
        
        # Use the selected option from combo box
        choice_map = {"All Reviews": "ALL", "Positive Only": "POSITIVE", "Negative Only": "NEGATIVE"}
        choice = choice_map[self.wordcloud_type.currentText()]
        
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
    
        # Show progress
        self.progress_bar.setVisible(True)
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(10)
        self.status_label.setText("📝 Generating AI summary...")
    
        # Calculate appropriate summary length based on selection
        length_map = {"Short": (50, 20), "Medium": (150, 30), "Long": (250, 50)}
        max_length, min_length = length_map[self.summary_length.currentText()]
        
        word_count = len(combined_text.split())
        max_length = min(max_length, max(50, word_count // 4))
        min_length = min(min_length, max_length - 20)
    
        # Create and start the summarizer thread
        self.summarizer_thread = SummarizerThread(combined_text, max_length, min_length)
        self.summarizer_thread.progress_signal.connect(self.progress_bar.setValue)
        self.summarizer_thread.finished_signal.connect(self.handle_summary_result)
        self.summarizer_thread.error_signal.connect(self.handle_summary_error)
        self.summarizer_thread.start()
    
        # Store the choice for later use
        self.current_summary_choice = choice

    def handle_summary_result(self, summary):
        # Hide progress
        self.progress_bar.setVisible(False)
        self.status_label.setText("✅ Summary generation completed")
            
        # Format summary
        formatted_summary = textwrap.fill(summary, width=80)
    
        # Save summary to file
        filename = f"summary_{self.current_summary_choice.lower()}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
        try:
            with open(filename, "w", encoding="utf-8") as f:
                f.write(f"Sentiment Analysis Summary - {self.current_summary_choice.title()} Reviews\n")
                f.write("="*60 + "\n\n")
                f.write(formatted_summary)
                f.write(f"\n\nGenerated on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        except Exception as e:
            print(f"Warning: Could not save summary to file: {str(e)}")
    
        # Show summary in a custom dialog
        self.show_summary_dialog(formatted_summary, filename)

    def show_summary_dialog(self, summary, filename):
        dialog = QMessageBox(self)
        dialog.setWindowTitle("📝 AI-Generated Summary")
        dialog.setIcon(QMessageBox.Information)
        
        dialog.setText(f"Summary for {self.current_summary_choice.lower()} reviews:")
        dialog.setDetailedText(summary)
        dialog.setInformativeText(f"Summary has been saved as '{filename}'")
        
        dialog.setStyleSheet("""
            QMessageBox {
                background: white;
            }
            QMessageBox QLabel {
                font-size: 11px;
            }
        """)
        
        dialog.exec_()

    def handle_summary_error(self, error_message):
        # Hide progress
        self.progress_bar.setVisible(False)
        self.status_label.setText("❌ Summary generation failed")
            
        QMessageBox.critical(self, "Summarization Error", 
                           f"Failed to generate summary:\n\n{error_message}\n\n"
                           "This might be due to:\n"
                           "• Internet connection issues\n"
                           "• AI model loading problems\n"
                           "• Insufficient text content\n\n"
                           "Please try again or check your internet connection.")