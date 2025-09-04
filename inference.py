"""
Inference script for the PyTorch CNN gesture recognition model.
This script loads a trained model and performs predictions on new images.
"""

'''
python inference.py --model models/cnn_gesture.pth --mode image --input datasets\resized_img_split\resized_img5\4_2_0_48.jpg
'''

import torch
import torch.nn.functional as F
import cv2
import numpy as np
from PIL import Image
import os
from typing import List, Union
import logging

from train import CNNGestureRecognizer

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Gesture class names (0-10 for Chinese number gestures)
GESTURE_CLASSES = {
        0: "0", 1: "1", 2: "2", 3: "3", 4: "4",
        5: "5", 6: "6", 7: "7", 8: "8", 9: "9", 10: "10"
    }


class GesturePredictor:
    """Class for making predictions with the trained gesture recognition model."""
    
    def __init__(self, model_path: str, device: str = 'auto'):
        """
        Initialize the predictor.
        
        Args:
            model_path: Path to the trained model file
            device: Device to use ('auto', 'cpu', 'cuda')
        """
        if device == 'auto':
            self.device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
        else:
            self.device = torch.device(device)
            
        # Initialize and load the model
        self.model = CNNGestureRecognizer(num_classes=11)
        self.load_model(model_path)
        self.model.eval()
        
        logger.info(f"Model loaded on device: {self.device}")
    
    def load_model(self, model_path: str):
        """Load the trained model."""
        try:
            checkpoint = torch.load(model_path, map_location=self.device)
            self.model.load_state_dict(checkpoint['model_state_dict'])
            self.model.to(self.device)
            logger.info(f"Model successfully loaded from {model_path}")
        except FileNotFoundError:
            logger.error(f"Model file not found: {model_path}")
            raise
        except Exception as e:
            logger.error(f"Error loading model: {str(e)}")
            raise
    
    def preprocess_image(self, image: Union[str, np.ndarray, Image.Image]) -> torch.Tensor:
        """
        Preprocess an image for model input.
        
        Args:
            image: Input image (file path, numpy array, or PIL Image)
            
        Returns:
            Preprocessed image tensor
        """
        # Load image if it's a file path
        if isinstance(image, str):
            if not os.path.exists(image):
                raise FileNotFoundError(f"Image file not found: {image}")
            image = cv2.imread(image)
            image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
        elif isinstance(image, Image.Image):
            image = np.array(image)
        
        # Ensure image is RGB
        if len(image.shape) == 3 and image.shape[2] == 3:
            pass  # Already RGB
        elif len(image.shape) == 3 and image.shape[2] == 4:
            # Convert RGBA to RGB
            image = image[:, :, :3]
        else:
            raise ValueError("Unsupported image format")
        
        # Resize to 64x64 (model input size)
        image = cv2.resize(image, (64, 64))
        
        # Normalize to [0, 1]
        image = image.astype(np.float32) / 255.0
        
        # Convert to PyTorch tensor and add batch dimension
        # Convert from (H, W, C) to (1, C, H, W)
        image_tensor = torch.FloatTensor(image).permute(2, 0, 1).unsqueeze(0)
        
        return image_tensor.to(self.device)
    
    def predict(self, image: Union[str, np.ndarray, Image.Image], 
                return_probabilities: bool = False) -> Union[int, tuple]:
        """
        Make a prediction on a single image.
        
        Args:
            image: Input image
            return_probabilities: If True, return probabilities along with prediction
            
        Returns:
            Predicted class (and probabilities if requested)
        """
        # Preprocess the image
        image_tensor = self.preprocess_image(image)
        
        # Make prediction
        with torch.no_grad():
            output = self.model(image_tensor)
            probabilities = F.softmax(output, dim=1)
            predicted_class = torch.argmax(probabilities, dim=1).item()
        
        if return_probabilities:
            probs = probabilities.squeeze().cpu().numpy()
            return predicted_class, probs
        else:
            return predicted_class
    
    def predict_batch(self, images: List[Union[str, np.ndarray, Image.Image]]) -> List[int]:
        """
        Make predictions on a batch of images.
        
        Args:
            images: List of input images
            
        Returns:
            List of predicted classes
        """
        predictions = []
        for image in images:
            pred = self.predict(image)
            predictions.append(pred)
        return predictions
    
    def get_top_k_predictions(self, image: Union[str, np.ndarray, Image.Image], 
                             k: int = 3) -> List[tuple]:
        """
        Get top-k predictions with class names and probabilities.
        
        Args:
            image: Input image
            k: Number of top predictions to return
            
        Returns:
            List of tuples (class_id, class_name, probability)
        """
        predicted_class, probabilities = self.predict(image, return_probabilities=True)
        
        # Get top-k predictions
        top_k_indices = np.argsort(probabilities)[-k:][::-1]
        
        results = []
        for idx in top_k_indices:
            class_name = GESTURE_CLASSES.get(idx, f"Class_{idx}")
            probability = probabilities[idx]
            results.append((idx, class_name, probability))
        
        return results


def predict_from_camera(model_path: str, camera_id: int = 0):
    """
    Real-time gesture prediction from camera feed.
    
    Args:
        model_path: Path to the trained model
        camera_id: Camera device ID
    """
    predictor = GesturePredictor(model_path)
    cap = cv2.VideoCapture(camera_id)
    
    if not cap.isOpened():
        logger.error(f"Cannot open camera {camera_id}")
        return
    
    logger.info("Starting camera feed. Press 'q' to quit.")
    
    try:
        while True:
            ret, frame = cap.read()
            if not ret:
                break
            
            # Make prediction
            try:
                predicted_class = predictor.predict(frame)
                class_name = GESTURE_CLASSES.get(predicted_class, f"Class_{predicted_class}")
                
                # Display result on frame
                cv2.putText(frame, f"Prediction: {class_name}", (10, 30),
                           cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
                
            except Exception as e:
                cv2.putText(frame, f"Error: {str(e)}", (10, 30),
                           cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)
            
            cv2.imshow('Gesture Recognition', frame)
            
            # Break on 'q' key press
            if cv2.waitKey(1) & 0xFF == ord('q'):
                break
                
    except KeyboardInterrupt:
        logger.info("Camera feed interrupted by user")
    finally:
        cap.release()
        cv2.destroyAllWindows()


def predict_from_images(model_path: str, image_paths: List[str], output_file: str = None):
    """
    Make predictions on a list of image files.
    
    Args:
        model_path: Path to the trained model
        image_paths: List of image file paths
        output_file: Optional file to save results
    """
    predictor = GesturePredictor(model_path)
    results = []
    
    logger.info(f"Making predictions on {len(image_paths)} images...")
    
    for image_path in image_paths:
        try:
            top_predictions = predictor.get_top_k_predictions(image_path, k=3)
            results.append({
                'image': image_path,
                'predictions': top_predictions
            })
            
            # Log the top prediction
            top_pred = top_predictions[0]
            logger.info(f"{image_path}: {top_pred[1]} (confidence: {top_pred[2]:.2f})")
            
        except Exception as e:
            logger.error(f"Error processing {image_path}: {str(e)}")
            results.append({
                'image': image_path,
                'error': str(e)
            })
    
    # Save results to file if specified
    if output_file:
        import json
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(results, f, ensure_ascii=False, indent=2)
        logger.info(f"Results saved to {output_file}")
    
    return results


def main():
    """Main function for testing the predictor."""
    import argparse
    
    parser = argparse.ArgumentParser(description='Gesture Recognition Inference')
    parser.add_argument('--model', '-m', type=str, required=True,
                       help='Path to the trained model file')
    parser.add_argument('--mode', choices=['camera', 'image', 'batch'], default='image',
                       help='Prediction mode')
    parser.add_argument('--input', '-i', type=str,
                       help='Input image file or directory (for batch mode)')
    parser.add_argument('--camera', type=int, default=0,
                       help='Camera device ID')
    parser.add_argument('--output', '-o', type=str,
                       help='Output file for batch results')
    
    args = parser.parse_args()
    
    if args.mode == 'camera':
        predict_from_camera(args.model, args.camera)
    elif args.mode == 'image':
        if not args.input:
            logger.error("Input image required for image mode")
            return
        
        predictor = GesturePredictor(args.model)
        top_predictions = predictor.get_top_k_predictions(args.input)
        
        print(f"\nPredictions for {args.input}:")
        for i, (class_id, class_name, prob) in enumerate(top_predictions):
            print(f"{i+1}. {class_name}: {prob:.3f}")
    
    elif args.mode == 'batch':
        if not args.input:
            logger.error("Input directory required for batch mode")
            return
        
        # Get all image files in directory
        image_extensions = {'.jpg', '.jpeg', '.png', '.bmp', '.tiff'}
        image_paths = []
        
        if os.path.isfile(args.input):
            image_paths = [args.input]
        elif os.path.isdir(args.input):
            for filename in os.listdir(args.input):
                if any(filename.lower().endswith(ext) for ext in image_extensions):
                    image_paths.append(os.path.join(args.input, filename))
        
        if not image_paths:
            logger.error("No image files found")
            return
        
        predict_from_images(args.model, image_paths, args.output)


if __name__ == "__main__":
    main()
