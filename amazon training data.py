import os
import pandas as pd
import kagglehub
from sklearn.model_selection import train_test_split
from transformers import AutoTokenizer, AutoModelForSequenceClassification, TrainingArguments, Trainer
import torch
from torch.utils.data import Dataset
import numpy as np

class ReviewsDataset(Dataset):
    def __init__(self, encodings, labels):
        self.encodings = encodings
        self.labels = labels

    def __getitem__(self, idx):
        item = {key: torch.tensor(val[idx]) for key, val in self.encodings.items()}
        item['labels'] = torch.tensor(self.labels[idx])
        return item

    def __len__(self):
        return len(self.labels)

def download_amazon_reviews_dataset():
    """Download the Amazon reviews dataset from Kaggle"""
    try:
        print("Downloading Amazon reviews dataset from Kaggle...")
        path = kagglehub.dataset_download("datafiniti/consumer-reviews-of-amazon-products")
        print(f"Dataset downloaded to: {path}")
        return path
    except Exception as e:
        print(f"Error downloading dataset: {e}")
        return None

def prepare_dataset(dataset_path):
    """Prepare the dataset for fine-tuning"""
    # Find CSV files in the dataset directory
    csv_files = [f for f in os.listdir(dataset_path) if f.endswith('.csv')]
    
    if not csv_files:
        print("No CSV files found in the dataset")
        return None
    
    # Load the first CSV file with proper settings to avoid dtype warnings
    print(f"Loading dataset from {os.path.join(dataset_path, csv_files[0])}")
    df = pd.read_csv(os.path.join(dataset_path, csv_files[0]), low_memory=False)
    
    # Check if the required columns exist
    if 'reviews.text' not in df.columns or 'reviews.rating' not in df.columns:
        print("Required columns not found in the dataset")
        return None
    
    # Extract reviews and ratings
    reviews = df['reviews.text'].dropna().tolist()
    ratings = df['reviews.rating'].dropna().tolist()
    
    # Convert ratings to sentiment labels (1-3 as negative, 4-5 as positive)
    labels = [0 if float(rating) < 4 else 1 for rating in ratings if pd.notna(rating)]
    reviews = [review for review, rating in zip(reviews, ratings) if pd.notna(rating)]
    
    # Ensure reviews and labels have the same length
    min_len = min(len(reviews), len(labels))
    reviews = reviews[:min_len]
    labels = labels[:min_len]
    
    print(f"Prepared dataset with {len(reviews)} reviews")
    
    # Split the dataset
    train_texts, val_texts, train_labels, val_labels = train_test_split(
        reviews, labels, test_size=0.2, random_state=42
    )
    
    return {
        'train_texts': train_texts,
        'val_texts': val_texts,
        'train_labels': train_labels,
        'val_labels': val_labels
    }

def fine_tune_model(dataset, model_name="distilbert-base-uncased", output_dir="fine_tuned_model"):
    """Fine-tune a pre-trained model on the Amazon reviews dataset"""
    # Check for CUDA availability
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print(f"Using device: {device}")
    
    # Load tokenizer and model
    tokenizer = AutoTokenizer.from_pretrained(model_name)
    model = AutoModelForSequenceClassification.from_pretrained(model_name, num_labels=2)
    model.to(device)
    
    # Tokenize the texts
    print("Tokenizing texts...")
    train_encodings = tokenizer(dataset['train_texts'], truncation=True, padding=True, max_length=512)
    val_encodings = tokenizer(dataset['val_texts'], truncation=True, padding=True, max_length=512)
    
    # Create datasets
    train_dataset = ReviewsDataset(train_encodings, dataset['train_labels'])
    val_dataset = ReviewsDataset(val_encodings, dataset['val_labels'])
    
    # Define training arguments
    training_args = TrainingArguments(
        output_dir=output_dir,
        num_train_epochs=3,
        per_device_train_batch_size=8,
        per_device_eval_batch_size=8,
        warmup_steps=500,
        weight_decay=0.01,
        logging_dir='./logs',
        logging_steps=10,
        eval_strategy="epoch",  # Updated from evaluation_strategy
        save_strategy="epoch",
        load_best_model_at_end=True,
        no_cuda=not torch.cuda.is_available(),
    )
    
    # Create trainer
    trainer = Trainer(
        model=model,
        args=training_args,
        train_dataset=train_dataset,
        eval_dataset=val_dataset
    )
    
    # Train the model
    print("Starting training...")
    trainer.train()
    
    # Save the model and tokenizer
    print(f"Saving model to {output_dir}")
    model.save_pretrained(output_dir)
    tokenizer.save_pretrained(output_dir)
    
    return output_dir

def run_fine_tuning():
    """Main function to run the fine-tuning process"""
    try:
        # Download the dataset
        dataset_path = download_amazon_reviews_dataset()
        if not dataset_path:
            return "Failed to download dataset"
        
        # Prepare the dataset
        dataset = prepare_dataset(dataset_path)
        if not dataset:
            return "Failed to prepare dataset"
        
        # Fine-tune the model
        output_dir = fine_tune_model(dataset)
        
        return f"Model fine-tuned and saved to {output_dir}"
    except Exception as e:
        import traceback
        print(f"Error during fine-tuning: {str(e)}")
        print(traceback.format_exc())
        return f"Fine-tuning failed: {str(e)}"

# Add this to make the script executable
if __name__ == "__main__":
    print("Starting model fine-tuning process...")
    result = run_fine_tuning()
    print(result)
    print("Fine-tuning complete. The model is now ready to use in your application.")