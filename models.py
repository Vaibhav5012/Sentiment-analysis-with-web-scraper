import threading
import os
from PyQt5.QtCore import QThread, pyqtSignal
from transformers import pipeline
from transformers import AutoModelForSequenceClassification, AutoTokenizer
import torch

class ModelLoader:
    _instance = None
    _lock = threading.Lock()
    
    def __new__(cls):
        with cls._lock:
            if cls._instance is None:
                cls._instance = super(ModelLoader, cls).__new__(cls)
                cls._instance._initialized = False
                cls._instance._summarizer = None
                cls._instance._qa_pipeline = None
                cls._instance._sentiment_transformer = None
            return cls._instance
    
    def _initialize_transformer_sentiment(self):
        if self._sentiment_transformer is None:
            try:
                # Use the fine-tuned model directly
                fine_tuned_model_path = os.path.join(os.path.dirname(__file__), "fine_tuned_model")
                
                # Try to use a specific checkpoint that might work better
                specific_checkpoint = "checkpoint-1000"  # You can change this to a checkpoint that works better
                model_checkpoint_path = os.path.join(fine_tuned_model_path, specific_checkpoint)
                
                if os.path.exists(model_checkpoint_path):
                    print(f"Using specific checkpoint: {specific_checkpoint}")
                    model = AutoModelForSequenceClassification.from_pretrained(model_checkpoint_path)
                    tokenizer = AutoTokenizer.from_pretrained(fine_tuned_model_path)
                else:
                    # Fallback to main model
                    print("Specific checkpoint not found, using main model")
                    model = AutoModelForSequenceClassification.from_pretrained(fine_tuned_model_path)
                    tokenizer = AutoTokenizer.from_pretrained(fine_tuned_model_path)
                
                # Create a custom pipeline with the fine-tuned model
                self._sentiment_transformer = pipeline(
                    "sentiment-analysis", 
                    model=model, 
                    tokenizer=tokenizer,
                    max_length=128,
                    truncation=True
                )
                
                print("Fine-tuned sentiment analysis model loaded successfully")
            except Exception as e:
                print(f"Error loading fine-tuned sentiment model: {str(e)}")
                # Fallback to a pre-trained model if the fine-tuned one fails
                try:
                    print("Falling back to pre-trained sentiment model")
                    self._sentiment_transformer = pipeline(
                        "sentiment-analysis", 
                        model="distilbert-base-uncased-finetuned-sst-2-english",
                        max_length=512,
                        truncation=True
                    )
                    print("Pre-trained sentiment model loaded successfully")
                except Exception as e:
                    print(f"Error loading pre-trained model: {str(e)}")
                    self._sentiment_transformer = None
                
        return self._sentiment_transformer
    
    def _initialize_summarizer(self):
        if self._summarizer is None:
            try:
                print("Loading summarization model...")
                # Use a smaller, more reliable model for summarization
                self._summarizer = pipeline(
                    "summarization", 
                    model="sshleifer/distilbart-cnn-12-6",
                    max_length=150,
                    min_length=30,
                    truncation=True
                )
                print("Summarization model loaded successfully")
            except Exception as e:
                print(f"Error loading summarization model: {str(e)}")
                try:
                    # Fallback to an even smaller model
                    print("Trying fallback summarization model...")
                    self._summarizer = pipeline(
                        "summarization",
                        model="facebook/bart-large-cnn",
                        max_length=150,
                        min_length=30,
                        truncation=True
                    )
                    print("Fallback summarization model loaded successfully")
                except Exception as e2:
                    print(f"Error loading fallback model: {str(e2)}")
                    self._summarizer = None
        return self._summarizer
    
    def _initialize_qa(self):
        if self._qa_pipeline is None:
            try:
                print("Loading Q&A model...")
                self._qa_pipeline = pipeline(
                    "question-answering", 
                    model="distilbert-base-cased-distilled-squad"
                )
                print("Q&A model loaded successfully")
            except Exception as e:
                print(f"Error loading Q&A model: {str(e)}")
                self._qa_pipeline = None
        return self._qa_pipeline
    
    @property
    def sentiment_transformer(self):
        return self._initialize_transformer_sentiment()
    
    @property
    def summarizer(self):
        return self._initialize_summarizer()
    
    @property
    def qa_pipeline(self):
        return self._initialize_qa()

# Create a global model loader instance
model_loader = ModelLoader()

class SummarizerThread(QThread):
    finished_signal = pyqtSignal(str)
    progress_signal = pyqtSignal(int)
    error_signal = pyqtSignal(str)
    
    def __init__(self, text, max_length=150, min_length=30):
        super().__init__()
        self.text = text
        self.max_length = max_length
        self.min_length = min_length
        
    def run(self):
        try:
            # Load model (this happens in the thread)
            self.progress_signal.emit(30)
            summarizer = model_loader.summarizer
            
            if summarizer is None:
                self.error_signal.emit("Summarization model could not be loaded. Please check your internet connection and try again.")
                return
            
            # Prepare text for summarization
            self.progress_signal.emit(50)
            
            # Limit text length to avoid memory issues
            max_input_length = 1024  # Adjust based on model capacity
            if len(self.text) > max_input_length:
                # Take the first part of the text
                self.text = self.text[:max_input_length]
                # Try to end at a sentence boundary
                last_period = self.text.rfind('.')
                if last_period > max_input_length // 2:
                    self.text = self.text[:last_period + 1]
            
            # Ensure minimum text length
            if len(self.text.strip()) < 50:
                self.error_signal.emit("Text is too short to summarize effectively.")
                return
            
            # Generate summary with error handling
            try:
                summary_result = summarizer(
                    self.text, 
                    max_length=min(self.max_length, len(self.text.split()) // 2),
                    min_length=min(self.min_length, 20),
                    do_sample=False,
                    truncation=True
                )
                
                if summary_result and len(summary_result) > 0:
                    summary = summary_result[0]['summary_text']
                else:
                    self.error_signal.emit("No summary could be generated from the provided text.")
                    return
                    
            except Exception as model_error:
                self.error_signal.emit(f"Error during summarization: {str(model_error)}")
                return
            
            self.progress_signal.emit(90)
            self.finished_signal.emit(summary)
            
        except Exception as e:
            self.error_signal.emit(f"Unexpected error during summarization: {str(e)}")

class QAThread(QThread):
    finished_signal = pyqtSignal(dict)
    progress_signal = pyqtSignal(int)
    error_signal = pyqtSignal(str)
    
    def __init__(self, question, context):
        super().__init__()
        self.question = question
        self.context = context
        
    def run(self):
        try:
            # Load model (this happens in the thread)
            self.progress_signal.emit(30)
            qa_pipeline = model_loader.qa_pipeline
            
            if qa_pipeline is None:
                self.error_signal.emit("Q&A model could not be loaded. Please check your internet connection and try again.")
                return
            
            # Get answer
            self.progress_signal.emit(50)
            answer = qa_pipeline(question=self.question, context=self.context)
            
            self.progress_signal.emit(90)
            self.finished_signal.emit(answer)
        except Exception as e:
            self.error_signal.emit(f"Error during Q&A processing: {str(e)}")