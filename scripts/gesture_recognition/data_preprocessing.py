"""
Data preprocessing utilities for gesture recognition.
This script handles dataset preparation, augmentation, and conversion.

Author: AI Assistant
Date: 2025-09-04
"""

import os
import cv2
import numpy as np
from PIL import Image
import matplotlib.pyplot as plt
from sklearn.model_selection import train_test_split
from typing import List, Tuple, Optional
import logging
import argparse
from pathlib import Path
import json

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class DataPreprocessor:
    """Class for preprocessing gesture recognition data."""
    
    def __init__(self, target_size: Tuple[int, int] = (64, 64)):
        """
        Initialize the preprocessor.
        
        Args:
            target_size: Target image size (width, height)
        """
        self.target_size = target_size
        
    def load_images_from_directory(self, root_dir: str, 
                                  class_mapping: Optional[dict] = None) -> Tuple[np.ndarray, np.ndarray]:
        """
        Load images from a directory structure where each subdirectory represents a class.
        
        Expected structure:
        root_dir/
        ├── class_0/
        │   ├── image1.jpg
        │   └── image2.jpg
        ├── class_1/
        │   ├── image1.jpg
        │   └── image2.jpg
        └── ...
        
        Args:
            root_dir: Root directory containing class subdirectories
            class_mapping: Optional mapping from directory names to class indices
            
        Returns:
            Tuple of (images, labels)
        """
        if not os.path.exists(root_dir):
            raise FileNotFoundError(f"Root directory not found: {root_dir}")
        
        images = []
        labels = []
        class_dirs = sorted([d for d in os.listdir(root_dir) 
                           if os.path.isdir(os.path.join(root_dir, d))])
        
        if class_mapping is None:
            # Create mapping from directory names to indices
            class_mapping = {class_dir: idx for idx, class_dir in enumerate(class_dirs)}
        
        logger.info(f"Found {len(class_dirs)} classes: {class_dirs}")
        logger.info(f"Class mapping: {class_mapping}")
        
        for class_dir in class_dirs:
            class_path = os.path.join(root_dir, class_dir)
            
            if class_dir not in class_mapping:
                logger.warning(f"Class directory '{class_dir}' not in mapping, skipping")
                continue
                
            class_label = class_mapping[class_dir]
            image_files = [f for f in os.listdir(class_path) 
                          if f.lower().endswith(('.jpg', '.jpeg', '.png', '.bmp'))]
            
            logger.info(f"Loading {len(image_files)} images from class '{class_dir}'")
            
            for image_file in image_files:
                image_path = os.path.join(class_path, image_file)
                try:
                    image = self.load_and_preprocess_image(image_path)
                    images.append(image)
                    labels.append(class_label)
                except Exception as e:
                    logger.warning(f"Failed to load image {image_path}: {str(e)}")
        
        images = np.array(images)
        labels = np.array(labels)
        
        logger.info(f"Loaded {len(images)} images with shape {images.shape}")
        logger.info(f"Label distribution: {np.bincount(labels)}")
        
        return images, labels
    
    def load_and_preprocess_image(self, image_path: str) -> np.ndarray:
        """
        Load and preprocess a single image.
        
        Args:
            image_path: Path to the image file
            
        Returns:
            Preprocessed image array
        """
        # Load image
        image = cv2.imread(image_path)
        if image is None:
            raise ValueError(f"Cannot load image: {image_path}")
        
        # Convert BGR to RGB
        image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
        
        # Resize image
        image = cv2.resize(image, self.target_size, interpolation=cv2.INTER_AREA)
        
        # Ensure uint8 format
        image = image.astype(np.uint8)
        
        return image
    
    def augment_image(self, image: np.ndarray, augmentation_params: dict) -> np.ndarray:
        """
        Apply data augmentation to an image.
        
        Args:
            image: Input image
            augmentation_params: Augmentation parameters
            
        Returns:
            Augmented image
        """
        augmented = image.copy()
        
        # Rotation
        if 'rotation_range' in augmentation_params and augmentation_params['rotation_range'] > 0:
            angle = np.random.uniform(-augmentation_params['rotation_range'], 
                                    augmentation_params['rotation_range'])
            center = (image.shape[1] // 2, image.shape[0] // 2)
            rotation_matrix = cv2.getRotationMatrix2D(center, angle, 1.0)
            augmented = cv2.warpAffine(augmented, rotation_matrix, 
                                     (image.shape[1], image.shape[0]))
        
        # Brightness adjustment
        if 'brightness_range' in augmentation_params:
            brightness_factor = np.random.uniform(*augmentation_params['brightness_range'])
            augmented = cv2.convertScaleAbs(augmented, alpha=brightness_factor, beta=0)
        
        # Horizontal flip
        if 'horizontal_flip' in augmentation_params and augmentation_params['horizontal_flip']:
            if np.random.random() > 0.5:
                augmented = cv2.flip(augmented, 1)
        
        # Noise
        if 'noise_factor' in augmentation_params and augmentation_params['noise_factor'] > 0:
            noise = np.random.normal(0, augmentation_params['noise_factor'], augmented.shape)
            augmented = np.clip(augmented + noise, 0, 255).astype(np.uint8)
        
        return augmented
    
    def create_augmented_dataset(self, images: np.ndarray, labels: np.ndarray,
                               augmentation_params: dict, 
                               augmentation_factor: int = 2) -> Tuple[np.ndarray, np.ndarray]:
        """
        Create an augmented dataset.
        
        Args:
            images: Original images
            labels: Original labels
            augmentation_params: Parameters for augmentation
            augmentation_factor: Number of augmented versions per original image
            
        Returns:
            Augmented images and labels
        """
        augmented_images = []
        augmented_labels = []
        
        # Keep original images
        augmented_images.extend(images)
        augmented_labels.extend(labels)
        
        # Generate augmented images
        for i, (image, label) in enumerate(zip(images, labels)):
            for _ in range(augmentation_factor):
                augmented_image = self.augment_image(image, augmentation_params)
                augmented_images.append(augmented_image)
                augmented_labels.append(label)
                
            if (i + 1) % 1000 == 0:
                logger.info(f"Augmented {i + 1}/{len(images)} images")
        
        return np.array(augmented_images), np.array(augmented_labels)
    
    def save_dataset_info(self, images: np.ndarray, labels: np.ndarray, 
                         output_dir: str):
        """
        Save dataset information to JSON format (no longer using HDF5).
        
        Args:
            images: Image array
            labels: Label array
            output_dir: Output directory path
        """
        os.makedirs(output_dir, exist_ok=True)
        
        # Save metadata
        metadata = {
            'num_samples': len(images),
            'image_shape': list(images.shape[1:]),
            'num_classes': len(np.unique(labels)),
            'class_distribution': np.bincount(labels).tolist(),
            'classes': np.unique(labels).tolist()
        }
        
        metadata_path = os.path.join(output_dir, 'dataset_info.json')
        with open(metadata_path, 'w', encoding='utf-8') as f:
            json.dump(metadata, f, indent=2, ensure_ascii=False)
        
        logger.info(f"Dataset info saved to {metadata_path}")
        logger.info(f"Shape: {images.shape}, Classes: {len(np.unique(labels))}")
        logger.info("Note: Images are loaded directly from folders, no need for separate data files.")
    
    def visualize_samples(self, images: np.ndarray, labels: np.ndarray, 
                         num_samples: int = 16, class_names: Optional[dict] = None):
        """
        Visualize random samples from the dataset.
        
        Args:
            images: Image array
            labels: Label array
            num_samples: Number of samples to visualize
            class_names: Optional mapping from class indices to names
        """
        indices = np.random.choice(len(images), num_samples, replace=False)
        
        rows = int(np.sqrt(num_samples))
        cols = int(np.ceil(num_samples / rows))
        
        fig, axes = plt.subplots(rows, cols, figsize=(12, 8))
        axes = axes.flatten() if num_samples > 1 else [axes]
        
        for i, idx in enumerate(indices):
            if i >= num_samples:
                break
                
            image = images[idx]
            label = labels[idx]
            
            if class_names and label in class_names:
                title = f"Class: {class_names[label]}"
            else:
                title = f"Class: {label}"
            
            axes[i].imshow(image)
            axes[i].set_title(title)
            axes[i].axis('off')
        
        # Hide unused subplots
        for i in range(num_samples, len(axes)):
            axes[i].axis('off')
        
        plt.tight_layout()
        plt.show()


def prepare_chinese_gesture_dataset(root_dir: str, output_dir: str,
                                   augment: bool = True):
    """
    Prepare the Chinese gesture dataset and save info (no longer creates HDF5 files).
    
    Args:
        root_dir: Root directory containing gesture images
        output_dir: Output directory for dataset info
        augment: Whether to apply data augmentation (for info only)
    """
    # Class mapping for Chinese number gestures
    class_mapping = {
        'img0': 0, 'img1': 1, 'img2': 2, 'img3': 3, 'img4': 4,
        'img5': 5, 'img6': 6, 'img7': 7, 'img8': 8, 'img9': 9, 'img10': 10
    }
    
    class_names = {
        0: "0", 1: "1", 2: "2", 3: "3", 4: "4",
        5: "5", 6: "6", 7: "7", 8: "8", 9: "9", 10: "10"
    }
    
    # Initialize preprocessor
    preprocessor = DataPreprocessor(target_size=(64, 64))
    
    # Load images to get statistics
    logger.info("Analyzing dataset structure...")
    images, labels = preprocessor.load_images_from_directory(root_dir, class_mapping)
    
    # Visualize samples
    logger.info("Visualizing sample images...")
    preprocessor.visualize_samples(images, labels, num_samples=16, class_names=class_names)
    
    # Save dataset information
    preprocessor.save_dataset_info(images, labels, output_dir)
    
    logger.info("Dataset analysis completed!")
    logger.info("The model will load images directly from the folder structure.")
    logger.info("No need to create HDF5 files - this is more flexible and memory efficient.")


def main():
    """Main function for data preprocessing."""
    parser = argparse.ArgumentParser(description='Data preprocessing for gesture recognition')
    parser.add_argument('--input', '-i', type=str, required=True,
                       help='Input directory containing class subdirectories')
    parser.add_argument('--output', '-o', type=str, required=True,
                       help='Output directory for dataset info')
    parser.add_argument('--no-augment', action='store_true',
                       help='Disable data augmentation (info only)')
    parser.add_argument('--target-size', type=int, nargs=2, default=[64, 64],
                       help='Target image size (width height)')
    parser.add_argument('--visualize', action='store_true',
                       help='Show sample visualizations')
    
    args = parser.parse_args()
    
    # Prepare dataset
    prepare_chinese_gesture_dataset(
        root_dir=args.input,
        output_dir=args.output,
        augment=not args.no_augment
    )


if __name__ == "__main__":
    main()
