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

def download_sarcasm_dataset():
    """Download the sarcasm dataset from Kaggle"""
    try:
        print("Downloading sarcasm dataset from Kaggle...")
        path = kagglehub.dataset_download("danofer/sarcasm")
        print(f"Dataset downloaded to: {path}")
        return path
    except Exception as e:
        print(f"Error downloading dataset: {e}")
        return None

def prepare_dataset(dataset_path):
    """Prepare the dataset for fine-tuning"""
    # Find CSV files in the dataset directory
    csv_files = [f for f in os.listdir(dataset_path) if f.endswith('.csv') or f.endswith('.json')]
    
    if not csv_files:
        print("No CSV or JSON files found in the dataset")
        return None
    
    # Load and combine data from all files
    all_data = []
    for file in csv_files:
        file_path = os.path.join(dataset_path, file)
        try:
            if file.endswith('.csv'):
                df = pd.read_csv(file_path)
            else:  # JSON file
                df = pd.read_json(file_path, lines=True)
            
            # Check if the dataset has the required columns
            if 'headline' in df.columns or 'text' in df.columns or 'comment' in df.columns:
                # For sarcasm dataset, we need to map the text and label columns
                text_col = next((col for col in ['headline', 'text', 'comment'] if col in df.columns), None)
                label_col = next((col for col in ['is_sarcastic', 'label', 'class'] if col in df.columns), None)
                
                if text_col and label_col:
                    # Create a new dataframe with standardized column names
                    processed_df = pd.DataFrame({
                        'text': df[text_col],
                        'label': df[label_col]
                    })
                    
                    # Clean the text data - remove NaN values and convert to string
                    processed_df = processed_df.dropna()
                    processed_df['text'] = processed_df['text'].astype(str)
                    
                    all_data.append(processed_df)
                    print(f"Loaded {len(processed_df)} records from {file}")
                else:
                    print(f"Required columns not found in {file}")
            else:
                print(f"Required columns not found in {file}")
        except Exception as e:
            print(f"Error loading {file}: {e}")
    
    if not all_data:
        print("No valid data found in the dataset files")
        return None
    
    # Combine all dataframes
    combined_df = pd.concat(all_data, ignore_index=True)
    
    # Map sarcastic (1) to negative sentiment and non-sarcastic (0) to positive sentiment
    combined_df['sentiment'] = combined_df['label'].map({1: 0, 0: 1})  # 0=negative, 1=positive
    
    # Limit dataset size to prevent memory issues
    if len(combined_df) > 100000:
        print(f"Limiting dataset from {len(combined_df)} to 100,000 records to prevent memory issues")
        combined_df = combined_df.sample(100000, random_state=42)
    
    print(f"Total records after processing: {len(combined_df)}")
    
    # Split into train and validation sets
    train_df, val_df = train_test_split(combined_df, test_size=0.2, random_state=42)
    
    return train_df, val_df

def fine_tune_model():
    """Fine-tune a pre-trained model on the sarcasm dataset"""
    # Download the dataset
    dataset_path = download_sarcasm_dataset()
    if not dataset_path:
        print("Failed to download dataset")
        return
    
    # Prepare the dataset
    data = prepare_dataset(dataset_path)
    if not data:
        print("Failed to prepare dataset")
        return
    
    train_df, val_df = data
    
    # Load tokenizer and model
    tokenizer = AutoTokenizer.from_pretrained("distilbert-base-uncased")
    model = AutoModelForSequenceClassification.from_pretrained("distilbert-base-uncased", num_labels=2)
    
    # Convert lists to clean strings and handle any potential None values
    train_texts = [str(text) for text in train_df['text'].tolist()]
    val_texts = [str(text) for text in val_df['text'].tolist()]
    
    print(f"Tokenizing {len(train_texts)} training examples...")
    
    # Use padding='max_length' to ensure all sequences have the same length
    max_length = 128
    
    # Process in smaller batches to avoid memory issues
    batch_size = 1000
    train_encodings = {}
    
    for i in range(0, len(train_texts), batch_size):
        print(f"Tokenizing batch {i//batch_size + 1}/{(len(train_texts) + batch_size - 1)//batch_size}")
        batch_texts = train_texts[i:i+batch_size]
        batch_encodings = tokenizer(
            batch_texts, 
            truncation=True, 
            padding='max_length',  # Changed from 'padding=True' to ensure fixed length
            max_length=max_length,
            return_tensors=None  # Return lists, not tensors
        )
        
        # Initialize train_encodings with the first batch
        if not train_encodings:
            train_encodings = {k: v for k, v in batch_encodings.items()}
        else:
            # Append subsequent batches
            for key, value in batch_encodings.items():
                train_encodings[key].extend(value)
    
    print(f"Tokenizing {len(val_texts)} validation examples...")
    val_encodings = tokenizer(
        val_texts, 
        truncation=True, 
        padding='max_length',  # Changed to ensure fixed length
        max_length=max_length,
        return_tensors=None  # Return lists, not tensors
    )
    
    # Create datasets
    train_dataset = ReviewsDataset(train_encodings, train_df['sentiment'].tolist())
    val_dataset = ReviewsDataset(val_encodings, val_df['sentiment'].tolist())
    
    # Define training arguments with reduced batch size and epochs
    training_args = TrainingArguments(
        output_dir='./fine_tuned_model',
        num_train_epochs=2,
        per_device_train_batch_size=8,  # Reduced batch size to help with memory
        per_device_eval_batch_size=8,
        warmup_steps=500,
        weight_decay=0.01,
        logging_dir='./logs',
        logging_steps=100,
        evaluation_strategy="steps",
        eval_steps=1000,
        save_steps=1000,
        load_best_model_at_end=True,
        fp16=False,  # Disable mixed precision to avoid potential issues
    )
    
    # Define trainer
    trainer = Trainer(
        model=model,
        args=training_args,
        train_dataset=train_dataset,
        eval_dataset=val_dataset
    )
    
    # Train the model
    print("Starting model fine-tuning...")
    trainer.train()
    
    # Save the model
    model_path = os.path.join(os.path.dirname(__file__), "fine_tuned_model")
    model.save_pretrained(model_path)
    tokenizer.save_pretrained(model_path)
    print(f"Model saved to {model_path}")

if __name__ == "__main__":
    fine_tune_model()
