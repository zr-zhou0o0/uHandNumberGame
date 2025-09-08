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
            augmentation_params: Augmentation parameters dictionary containing:
                - rotation_range: Range for random rotation in degrees
                - brightness_range: Tuple (min, max) for brightness scaling
                - horizontal_flip: Boolean for random horizontal flipping
                - noise_factor: Standard deviation for Gaussian noise
                - color_temperature: Range for color temperature shift (0.0-1.0)
                  Positive values make image warmer (more yellow/red)
                  Negative values make image cooler (more blue)
                - hue_shift: Range for hue shift in degrees (0-180)
                  Shifts the overall color hue in HSV space
                - color_tint: Range for color tint adjustment (0.0-1.0)
                  Positive values add green tint, negative adds magenta tint
            
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
        
        # Color temperature adjustment (warm/cool)
        if 'color_temperature' in augmentation_params and augmentation_params['color_temperature'] > 0:
            temp_factor = np.random.uniform(-augmentation_params['color_temperature'], 
                                          augmentation_params['color_temperature'])
            # Warm (positive): increase red, decrease blue
            # Cool (negative): decrease red, increase blue
            if temp_factor > 0:  # Warmer (more yellow/red)
                augmented[:, :, 0] = np.clip(augmented[:, :, 0] * (1 + temp_factor * 0.3), 0, 255)  # Red
                augmented[:, :, 2] = np.clip(augmented[:, :, 2] * (1 - temp_factor * 0.2), 0, 255)  # Blue
            else:  # Cooler (more blue)
                augmented[:, :, 0] = np.clip(augmented[:, :, 0] * (1 + temp_factor * 0.2), 0, 255)  # Red
                augmented[:, :, 2] = np.clip(augmented[:, :, 2] * (1 - temp_factor * 0.3), 0, 255)  # Blue
            augmented = augmented.astype(np.uint8)
        
        # Color hue shift (green/magenta)
        if 'hue_shift' in augmentation_params and augmentation_params['hue_shift'] > 0:
            # Convert to HSV for hue adjustment
            hsv = cv2.cvtColor(augmented, cv2.COLOR_RGB2HSV)
            hue_delta = np.random.uniform(-augmentation_params['hue_shift'], 
                                        augmentation_params['hue_shift'])
            # Adjust hue channel (wrap around 0-179 in OpenCV HSV)
            hsv[:, :, 0] = (hsv[:, :, 0] + hue_delta) % 180
            augmented = cv2.cvtColor(hsv, cv2.COLOR_HSV2RGB)
        
        # Color tint (green/magenta bias in RGB)
        if 'color_tint' in augmentation_params and augmentation_params['color_tint'] > 0:
            tint_factor = np.random.uniform(-augmentation_params['color_tint'], 
                                          augmentation_params['color_tint'])
            if tint_factor > 0:  # Green tint
                augmented[:, :, 1] = np.clip(augmented[:, :, 1] * (1 + tint_factor * 0.2), 0, 255)  # Green
                augmented[:, :, 0] = np.clip(augmented[:, :, 0] * (1 - tint_factor * 0.1), 0, 255)  # Red
                augmented[:, :, 2] = np.clip(augmented[:, :, 2] * (1 - tint_factor * 0.1), 0, 255)  # Blue
            else:  # Magenta tint
                augmented[:, :, 1] = np.clip(augmented[:, :, 1] * (1 + tint_factor * 0.2), 0, 255)  # Green
                augmented[:, :, 0] = np.clip(augmented[:, :, 0] * (1 - tint_factor * 0.1), 0, 255)  # Red
                augmented[:, :, 2] = np.clip(augmented[:, :, 2] * (1 - tint_factor * 0.1), 0, 255)  # Blue
            augmented = augmented.astype(np.uint8)
        
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
                                   augment: bool = True, augmentation_factor: int = 3,
                                   save_augmented: bool = False):
    """
    Prepare the Chinese gesture dataset with optional data augmentation.
    
    Args:
        root_dir: Root directory containing gesture images
        output_dir: Output directory for dataset info and augmented images
        augment: Whether to apply data augmentation
        augmentation_factor: Number of augmented versions per original image
        save_augmented: Whether to save augmented images to disk
    """
    # Class mapping for Chinese number gestures
    class_mapping = {
        'img0': 0, 'img1': 1, 'img2': 2, 'img3': 3, 'img4': 4,
        'img5': 5, 'img6': 6, 'img7': 7, 'img8': 8, 'img9': 9, 
    }
    
    class_names = {
        0: "0", 1: "1", 2: "2", 3: "3", 4: "4",
        5: "5", 6: "6", 7: "7", 8: "8", 9: "9", 
    }
    
    # Data augmentation parameters
    augmentation_params = {
        'rotation_range': 15,
        'brightness_range': (0.8, 1.2),
        'horizontal_flip': True,
        'noise_factor': 5,
        'color_temperature': 0.3,  # Color temperature shift (warm/cool)
        'hue_shift': 10,          # Hue shift in degrees (0-180)
        'color_tint': 0.2         # Color tint (green/magenta bias)
    }
    
    # Initialize preprocessor
    preprocessor = DataPreprocessor(target_size=(64, 64))
    
    # Load original images
    logger.info("Loading original dataset...")
    images, labels = preprocessor.load_images_from_directory(root_dir, class_mapping)
    
    # Visualize original samples
    logger.info("Visualizing original sample images...")
    preprocessor.visualize_samples(images, labels, num_samples=16, class_names=class_names)
    
    # Apply data augmentation if requested
    if augment:
        logger.info(f"Applying data augmentation with factor {augmentation_factor}...")
        augmented_images, augmented_labels = preprocessor.create_augmented_dataset(
            images, labels, augmentation_params, augmentation_factor
        )
        
        logger.info(f"Original dataset: {len(images)} images")
        logger.info(f"Augmented dataset: {len(augmented_images)} images")
        
        # Visualize augmented samples
        logger.info("Visualizing augmented sample images...")
        # Show only the augmented versions (exclude original images)
        aug_only_images = augmented_images[len(images):]
        aug_only_labels = augmented_labels[len(labels):]
        if len(aug_only_images) > 0:
            preprocessor.visualize_samples(aug_only_images, aug_only_labels, 
                                         num_samples=16, class_names=class_names)
        
        # Save augmented images to disk if requested
        if save_augmented:
            logger.info("Saving augmented dataset to disk...")
            save_augmented_dataset(augmented_images, augmented_labels, output_dir, 
                                 class_names, class_mapping)
        
        # Save dataset information for augmented dataset
        preprocessor.save_dataset_info(augmented_images, augmented_labels, output_dir)
        
    else:
        # Save dataset information for original dataset only
        preprocessor.save_dataset_info(images, labels, output_dir)
    
    logger.info("Dataset preprocessing completed!")
    if augment and save_augmented:
        logger.info(f"Augmented images saved to: {output_dir}")
    logger.info("The model can load images directly from the folder structure.")


def save_augmented_dataset(images: np.ndarray, labels: np.ndarray, 
                          output_dir: str, class_names: dict, class_mapping: dict):
    """
    Save augmented dataset to disk in organized folder structure.
    
    Args:
        images: Augmented image array
        labels: Corresponding labels
        output_dir: Output directory
        class_names: Mapping from class indices to names
        class_mapping: Original class mapping
    """
    # Create augmented dataset directory
    augmented_dir = os.path.join(output_dir, 'augmented_dataset')
    os.makedirs(augmented_dir, exist_ok=True)
    
    # Create class directories
    reverse_mapping = {v: k for k, v in class_mapping.items()}
    class_counters = {label: 0 for label in np.unique(labels)}
    
    for label in np.unique(labels):
        class_dir_name = reverse_mapping.get(label, f'class_{label}')
        class_dir = os.path.join(augmented_dir, class_dir_name)
        os.makedirs(class_dir, exist_ok=True)
    
    # Save images
    logger.info(f"Saving {len(images)} images to {augmented_dir}...")
    
    for i, (image, label) in enumerate(zip(images, labels)):
        class_dir_name = reverse_mapping.get(label, f'class_{label}')
        class_dir = os.path.join(augmented_dir, class_dir_name)
        
        # Generate filename
        filename = f"{class_dir_name}_{class_counters[label]:06d}.jpg"
        filepath = os.path.join(class_dir, filename)
        
        # Convert RGB to BGR for OpenCV
        image_bgr = cv2.cvtColor(image, cv2.COLOR_RGB2BGR)
        cv2.imwrite(filepath, image_bgr)
        
        class_counters[label] += 1
        
        if (i + 1) % 1000 == 0:
            logger.info(f"Saved {i + 1}/{len(images)} images")
    
    logger.info(f"All augmented images saved to: {augmented_dir}")
    logger.info("Class distribution in saved dataset:")
    for label, count in class_counters.items():
        class_name = class_names.get(label, f'Class_{label}')
        logger.info(f"  {class_name}: {count} images")


def main():
    """Main function for data preprocessing."""
    parser = argparse.ArgumentParser(description='Data preprocessing for gesture recognition')
    parser.add_argument('--input', '-i', type=str, required=True,
                       help='Input directory containing class subdirectories')
    parser.add_argument('--output', '-o', type=str, required=True,
                       help='Output directory for dataset info and augmented images')
    parser.add_argument('--no-augment', action='store_true',
                       help='Disable data augmentation')
    parser.add_argument('--augmentation-factor', type=int, default=3,
                       help='Number of augmented versions per original image (default: 3)')
    parser.add_argument('--save-augmented', action='store_true',
                       help='Save augmented images to disk')
    parser.add_argument('--target-size', type=int, nargs=2, default=[64, 64],
                       help='Target image size (width height)')
    parser.add_argument('--visualize', action='store_true',
                       help='Show sample visualizations')
    
    args = parser.parse_args()
    
    # Prepare dataset
    prepare_chinese_gesture_dataset(
        root_dir=args.input,
        output_dir=args.output,
        augment=not args.no_augment,
        augmentation_factor=args.augmentation_factor,
        save_augmented=args.save_augmented
    )


if __name__ == "__main__":
    main()
