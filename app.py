import os
os.environ["TF_CPP_MIN_LOG_LEVEL"] = "2"  
import sys
from PyQt5.QtWidgets import QApplication

# Import the main UI class
from ui import SentimentAnalysisApp

# Main entry point
if __name__ == "__main__":
        # Start the UI application
        app = QApplication(sys.argv)
        window = SentimentAnalysisApp()
        window.show()
        sys.exit(app.exec_())
