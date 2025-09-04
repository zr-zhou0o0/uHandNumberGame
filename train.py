"""
PyTorch implementation of CNN for Chinese number gesture recognition.
This is a modern, clean rewrite of the original TensorFlow CNN model.
"""

import torch
import torch.nn as nn
import torch.optim as optim
import torch.nn.functional as F
from torch.utils.data import Dataset, DataLoader
import cv2
import numpy as np
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score, classification_report
import matplotlib.pyplot as plt
import time
import os
import glob
from typing import Tuple, Dict, List
import logging
from tqdm import tqdm

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class GestureDataset(Dataset):
    """Custom Dataset class for gesture recognition data."""
    
    def __init__(self, image_paths: List[str], labels: List[int], transform=None, target_size=(64, 64)):
        """
        Initialize the dataset.
        
        Args:
            image_paths: List of paths to image files
            labels: List of corresponding labels
            transform: Optional transform to be applied on images
            target_size: Target image size (height, width)
        """
        self.image_paths = image_paths
        self.labels = labels
        self.transform = transform
        self.target_size = target_size
    
    def __len__(self) -> int:
        return len(self.image_paths)
    
    def __getitem__(self, idx: int) -> Tuple[torch.Tensor, torch.Tensor]:
        # Load image
        image_path = self.image_paths[idx]
        image = cv2.imread(image_path)
        
        if image is None:
            # Create a black image if loading fails
            image = np.zeros((self.target_size[0], self.target_size[1], 3), dtype=np.uint8)
        else:
            # Convert BGR to RGB
            image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
            # Resize image
            image = cv2.resize(image, self.target_size, interpolation=cv2.INTER_AREA)
        
        # Normalize to [0, 1]
        image = image.astype(np.float32) / 255.0
        
        # Convert to tensor and change from (H, W, C) to (C, H, W)
        image_tensor = torch.FloatTensor(image).permute(2, 0, 1)
        
        label = torch.LongTensor([self.labels[idx]])
        
        if self.transform:
            image_tensor = self.transform(image_tensor)
            
        return image_tensor, label.squeeze()


class CNNGestureRecognizer(nn.Module):
    """
    CNN model for Chinese number gesture recognition.
    
    Architecture:
    - Conv2D(3->32) + ReLU + MaxPool
    - Conv2D(32->64) + ReLU + MaxPool
    - Fully Connected(16*16*64->200) + ReLU + Dropout
    - Fully Connected(200->11) + Softmax
    """
    
    def __init__(self, num_classes: int = 11, dropout_rate: float = 0.5):
        """
        Initialize the CNN model.
        
        Args:
            num_classes: Number of gesture classes (0-10)
            dropout_rate: Dropout rate for regularization
        """
        super(CNNGestureRecognizer, self).__init__()
        
        # Convolutional layers
        self.conv1 = nn.Conv2d(3, 32, kernel_size=5, padding=2)
        self.conv2 = nn.Conv2d(32, 64, kernel_size=5, padding=2)
        
        # Pooling layer
        self.pool = nn.MaxPool2d(kernel_size=2, stride=2)
        
        # Fully connected layers
        self.fc1 = nn.Linear(16 * 16 * 64, 200)
        self.fc2 = nn.Linear(200, num_classes)
        
        # Dropout for regularization
        self.dropout = nn.Dropout(dropout_rate)
        
        # Initialize weights
        self._initialize_weights()
    
    def _initialize_weights(self):
        """Initialize model weights."""
        for module in self.modules():
            if isinstance(module, nn.Conv2d):
                nn.init.normal_(module.weight, std=0.1)
                if module.bias is not None:
                    nn.init.constant_(module.bias, 0)
            elif isinstance(module, nn.Linear):
                nn.init.normal_(module.weight, std=0.1)
                nn.init.constant_(module.bias, 0)
    
    def forward(self, x: torch.Tensor) -> torch.Tensor:
        """
        Forward pass of the model.
        
        Args:
            x: Input tensor of shape (batch_size, 3, 64, 64)
            
        Returns:
            Output logits of shape (batch_size, num_classes)
        """
        # First convolutional block
        x = self.pool(F.relu(self.conv1(x)))  # (batch_size, 32, 32, 32)
        
        # Second convolutional block
        x = self.pool(F.relu(self.conv2(x)))  # (batch_size, 64, 16, 16)
        
        # Flatten for fully connected layers
        x = x.view(-1, 16 * 16 * 64)  # (batch_size, 16384)
        
        # First fully connected layer with dropout
        x = self.dropout(F.relu(self.fc1(x)))  # (batch_size, 200)
        
        # Output layer
        x = self.fc2(x)  # (batch_size, num_classes)
        
        return x


class GestureTrainer:
    """Trainer class for the gesture recognition model."""
    
    def __init__(self, model: nn.Module, device: str = 'auto'):
        """
        Initialize the trainer.
        
        Args:
            model: The CNN model to train
            device: Device to use ('auto', 'cpu', 'cuda')
        """
        if device == 'auto':
            self.device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
        else:
            self.device = torch.device(device)
            
        self.model = model.to(self.device)
        logger.info(f"Using device: {self.device}")
    
    def train_epoch(self, train_loader: DataLoader, optimizer: optim.Optimizer, 
                   criterion: nn.Module) -> float:
        """Train the model for one epoch."""
        self.model.train()
        total_loss = 0.0
        
        # Create progress bar for batches
        pbar = tqdm(train_loader, desc="Training", leave=False)
        for batch_idx, (data, target) in enumerate(pbar):
            data, target = data.to(self.device), target.to(self.device)
            
            optimizer.zero_grad()
            output = self.model(data)
            loss = criterion(output, target)
            loss.backward()
            optimizer.step()
            
            total_loss += loss.item()
            
            # Update progress bar with current loss
            pbar.set_postfix({'Loss': f'{loss.item():.4f}'})
            
        return total_loss / len(train_loader)
    
    def evaluate(self, test_loader: DataLoader, criterion: nn.Module) -> Tuple[float, float]:
        """Evaluate the model on test data."""
        self.model.eval()
        total_loss = 0.0
        correct = 0
        total = 0
        
        with torch.no_grad():
            # Create progress bar for evaluation
            pbar = tqdm(test_loader, desc="Evaluating", leave=False)
            for data, target in pbar:
                data, target = data.to(self.device), target.to(self.device)
                output = self.model(data)
                loss = criterion(output, target)
                
                total_loss += loss.item()
                _, predicted = torch.max(output.data, 1)
                total += target.size(0)
                correct += (predicted == target).sum().item()
                
                # Update progress bar with current accuracy
                current_acc = 100 * correct / total
                pbar.set_postfix({'Acc': f'{current_acc:.2f}%'})
        
        accuracy = 100 * correct / total
        avg_loss = total_loss / len(test_loader)
        
        return avg_loss, accuracy
    
    def train(self, train_loader: DataLoader, test_loader: DataLoader,
              num_epochs: int = 100, learning_rate: float = 0.001,
              weight_decay: float = 1e-4) -> Dict:
        """
        Train the model.
        
        Args:
            train_loader: Training data loader
            test_loader: Test data loader
            num_epochs: Number of training epochs
            learning_rate: Learning rate for optimizer
            weight_decay: L2 regularization weight
            
        Returns:
            Dictionary containing training history
        """
        criterion = nn.CrossEntropyLoss()
        optimizer = optim.Adam(self.model.parameters(), lr=learning_rate, 
                              weight_decay=weight_decay)
        
        history = {
            'train_loss': [],
            'test_loss': [],
            'test_accuracy': []
        }
        
        logger.info(f"Starting training for {num_epochs} epochs...")
        start_time = time.time()
        
        # Create progress bar for epochs
        epoch_pbar = tqdm(range(num_epochs), desc="Epochs")
        
        for epoch in epoch_pbar:
            # Train for one epoch
            train_loss = self.train_epoch(train_loader, optimizer, criterion)
            
            # Evaluate on test set
            test_loss, test_accuracy = self.evaluate(test_loader, criterion)
            
            # Record history
            history['train_loss'].append(train_loss)
            history['test_loss'].append(test_loss)
            history['test_accuracy'].append(test_accuracy)
            
            # Update epoch progress bar
            epoch_pbar.set_postfix({
                'Train Loss': f'{train_loss:.4f}',
                'Test Loss': f'{test_loss:.4f}', 
                'Test Acc': f'{test_accuracy:.2f}%'
            })
            
            # Log progress less frequently
            if epoch % 20 == 0 or epoch == num_epochs - 1:
                logger.info(f"Epoch [{epoch+1}/{num_epochs}] - "
                           f"Train Loss: {train_loss:.4f}, "
                           f"Test Loss: {test_loss:.4f}, "
                           f"Test Accuracy: {test_accuracy:.2f}%")
        
        training_time = time.time() - start_time
        logger.info(f"Training completed in {training_time:.2f} seconds")
        
        return history
    
    def save_model(self, save_path: str):
        """Save the trained model."""
        os.makedirs(os.path.dirname(save_path), exist_ok=True)
        torch.save({
            'model_state_dict': self.model.state_dict(),
            'model_architecture': type(self.model).__name__
        }, save_path)
        logger.info(f"Model saved to {save_path}")
    
    def load_model(self, load_path: str):
        """Load a trained model."""
        checkpoint = torch.load(load_path, map_location=self.device)
        self.model.load_state_dict(checkpoint['model_state_dict'])
        logger.info(f"Model loaded from {load_path}")


def load_dataset_from_folders(data_dir: str = "../../datasets/captured") -> Tuple[List[str], List[str], List[int], List[int]]:
    """
    Load the gesture recognition dataset from folder structure.
    
    Args:
        data_dir: Path to the directory containing class folders (img0, img1, ..., img10)
        
    Returns:
        Tuple of (train_paths, test_paths, train_labels, test_labels)
    """
    logger.info(f"Loading dataset from {data_dir}...")
    
    if not os.path.exists(data_dir):
        logger.error(f"Dataset directory not found: {data_dir}")
        raise FileNotFoundError(f"Dataset directory not found: {data_dir}")
    
    # Define class mapping
    # class_mapping = {
    #     'img0': 0, 'img1': 1, 'img2': 2, 'img3': 3, 'img4': 4,
    #     'img5': 5, 'img6': 6, 'img7': 7, 'img8': 8, 'img9': 9, 'img10': 10
    # }

    class_mapping = {
        'resized_img0': 0, 'resized_img1': 1, 'resized_img2': 2, 'resized_img3': 3, 'resized_img4': 4,
        'resized_img5': 5, 'resized_img6': 6, 'resized_img7': 7, 'resized_img8': 8, 'resized_img9': 9, 'resized_img10': 10
    }
    
    image_paths = []
    labels = []
    
    # Load images from each class folder
    for class_name, class_id in class_mapping.items():
        class_dir = os.path.join(data_dir, class_name)
        
        if not os.path.exists(class_dir):
            logger.warning(f"Class directory not found: {class_dir}")
            continue
        
        # Get all image files in the class directory
        image_extensions = ['*.jpg', '*.jpeg', '*.png', '*.bmp', '*.tiff']
        class_images = []
        
        for ext in image_extensions:
            class_images.extend(glob.glob(os.path.join(class_dir, ext)))
            class_images.extend(glob.glob(os.path.join(class_dir, ext.upper())))
        
        logger.info(f"Found {len(class_images)} images for class {class_name} (label {class_id})")
        
        # Add to dataset
        image_paths.extend(class_images)
        labels.extend([class_id] * len(class_images))
    
    logger.info(f"Total images loaded: {len(image_paths)}")
    logger.info(f"Class distribution: {np.bincount(labels)}")
    
    # Split into training and testing sets
    train_paths, test_paths, train_labels, test_labels = train_test_split(
        image_paths, labels, train_size=0.9, test_size=0.1, random_state=42, stratify=labels
    )
    
    logger.info(f"Train samples: {len(train_paths)}, Test samples: {len(test_paths)}")
    
    return train_paths, test_paths, train_labels, test_labels


def plot_training_history(history: Dict, save_path: str = None):
    """Plot training history."""
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 4))
    
    # Plot loss
    ax1.plot(history['train_loss'], label='Train Loss')
    ax1.plot(history['test_loss'], label='Test Loss')
    ax1.set_xlabel('Epoch')
    ax1.set_ylabel('Loss')
    ax1.set_title('Training and Test Loss')
    ax1.legend()
    ax1.grid(True)
    
    # Plot accuracy
    ax2.plot(history['test_accuracy'])
    ax2.set_xlabel('Epoch')
    ax2.set_ylabel('Accuracy (%)')
    ax2.set_title('Test Accuracy')
    ax2.grid(True)
    
    plt.tight_layout()
    
    if save_path:
        plt.savefig(save_path)
        logger.info(f"Training plots saved to {save_path}")
    
    plt.show()


def main():
    """Main training function."""
    # Configuration
    config = {
        'data_dir': r'datasets\resized_img_split',
        'batch_size': 16,
        'num_epochs': 50,
        'learning_rate': 0.001,
        'weight_decay': 1e-4,
        'dropout_rate': 0.5,
        'model_save_path': 'models/cnn_gesture.pth'
    }
    
    # Create directories if they don't exist
    os.makedirs('models', exist_ok=True)
    
    # Load dataset
    train_paths, test_paths, train_labels, test_labels = load_dataset_from_folders(config['data_dir'])
    
    # Create datasets and data loaders
    train_dataset = GestureDataset(train_paths, train_labels)
    test_dataset = GestureDataset(test_paths, test_labels)
    
    train_loader = DataLoader(train_dataset, batch_size=config['batch_size'], 
                             shuffle=True, num_workers=0)  # Set num_workers=0 for Windows compatibility
    test_loader = DataLoader(test_dataset, batch_size=config['batch_size'], 
                            shuffle=False, num_workers=0)
    
    # Create model and trainer
    model = CNNGestureRecognizer(num_classes=11, dropout_rate=config['dropout_rate'])
    trainer = GestureTrainer(model)
    
    # Print model summary
    logger.info(f"Model architecture:\n{model}")
    total_params = sum(p.numel() for p in model.parameters())
    logger.info(f"Total parameters: {total_params:,}")
    
    # Train the model
    history = trainer.train(
        train_loader=train_loader,
        test_loader=test_loader,
        num_epochs=config['num_epochs'],
        learning_rate=config['learning_rate'],
        weight_decay=config['weight_decay']
    )
    
    # Save the model
    trainer.save_model(config['model_save_path'])
    
    # Plot training history
    plot_training_history(history, 'models/training_history.png')
    
    # Final evaluation
    final_loss, final_accuracy = trainer.evaluate(test_loader, nn.CrossEntropyLoss())
    logger.info(f"Final Test Accuracy: {final_accuracy:.2f}%")


if __name__ == "__main__":
    main()
