"""
Configuration file for gesture recognition training.
This file contains all the hyperparameters and settings for the CNN model.
"""

import os
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple


@dataclass
class ModelConfig:
    """Configuration for the CNN model architecture."""
    num_classes: int = 11
    dropout_rate: float = 0.5
    input_size: Tuple[int, int, int] = (3, 64, 64)  # (channels, height, width)


@dataclass
class TrainingConfig:
    """Configuration for training parameters."""
    num_epochs: int = 100
    batch_size: int = 16
    learning_rate: float = 0.001
    weight_decay: float = 1e-4
    
    # Learning rate scheduling
    use_scheduler: bool = True
    scheduler_step_size: int = 30
    scheduler_gamma: float = 0.1
    
    # Early stopping
    early_stopping: bool = True
    early_stopping_patience: int = 15
    early_stopping_delta: float = 0.001
    
    # Validation
    validation_split: float = 0.1
    
    # Device
    device: str = 'auto'  # 'auto', 'cpu', 'cuda'


@dataclass
class DataConfig:
    """Configuration for data handling."""
    data_dir: str = 'datasets/captured'
    train_split: float = 0.9
    random_state: int = 42
    
    # Data loading
    num_workers: int = 0  # Set to 0 for Windows compatibility
    pin_memory: bool = True
    
    # Data augmentation
    use_augmentation: bool = True
    augmentation_params: Dict = field(default_factory=lambda: {
        'rotation_range': 15,
        'brightness_range': (0.8, 1.2),
        'horizontal_flip': True,
        'noise_factor': 5
    })


@dataclass
class ExperimentConfig:
    """Configuration for experiment tracking and output."""
    experiment_name: str = 'cnn_gesture_recognition'
    output_dir: str = 'experiments'
    
    # Model saving
    save_best_model: bool = True
    save_last_model: bool = True
    model_checkpoint_dir: str = 'models'
    
    # Logging
    log_level: str = 'INFO'
    save_training_plots: bool = True
    plot_save_path: str = 'plots'
    
    # Metrics tracking
    track_metrics: bool = True
    metrics_save_path: str = 'metrics'


@dataclass
class Config:
    """Main configuration class combining all sub-configurations."""
    model: ModelConfig = field(default_factory=ModelConfig)
    training: TrainingConfig = field(default_factory=TrainingConfig)
    data: DataConfig = field(default_factory=DataConfig)
    experiment: ExperimentConfig = field(default_factory=ExperimentConfig)
    
    def __post_init__(self):
        """Post-initialization to set up paths."""
        # Create output directories
        base_dir = os.path.join(self.experiment.output_dir, self.experiment.experiment_name)
        
        self.experiment.model_checkpoint_dir = os.path.join(base_dir, 'models')
        self.experiment.plot_save_path = os.path.join(base_dir, 'plots')
        self.experiment.metrics_save_path = os.path.join(base_dir, 'metrics')
        
        # Create directories if they don't exist
        os.makedirs(self.experiment.model_checkpoint_dir, exist_ok=True)
        os.makedirs(self.experiment.plot_save_path, exist_ok=True)
        os.makedirs(self.experiment.metrics_save_path, exist_ok=True)
    
    @classmethod
    def from_dict(cls, config_dict: Dict) -> 'Config':
        """Create configuration from dictionary."""
        model_config = ModelConfig(**config_dict.get('model', {}))
        training_config = TrainingConfig(**config_dict.get('training', {}))
        data_config = DataConfig(**config_dict.get('data', {}))
        experiment_config = ExperimentConfig(**config_dict.get('experiment', {}))
        
        return cls(
            model=model_config,
            training=training_config,
            data=data_config,
            experiment=experiment_config
        )
    
    def to_dict(self) -> Dict:
        """Convert configuration to dictionary."""
        return {
            'model': {
                'num_classes': self.model.num_classes,
                'dropout_rate': self.model.dropout_rate,
                'input_size': self.model.input_size
            },
            'training': {
                'num_epochs': self.training.num_epochs,
                'batch_size': self.training.batch_size,
                'learning_rate': self.training.learning_rate,
                'weight_decay': self.training.weight_decay,
                'use_scheduler': self.training.use_scheduler,
                'scheduler_step_size': self.training.scheduler_step_size,
                'scheduler_gamma': self.training.scheduler_gamma,
                'early_stopping': self.training.early_stopping,
                'early_stopping_patience': self.training.early_stopping_patience,
                'early_stopping_delta': self.training.early_stopping_delta,
                'validation_split': self.training.validation_split,
                'device': self.training.device
            },
            'data': {
                'data_dir': self.data.data_dir,
                'train_split': self.data.train_split,
                'random_state': self.data.random_state,
                'num_workers': self.data.num_workers,
                'pin_memory': self.data.pin_memory,
                'use_augmentation': self.data.use_augmentation,
                'augmentation_params': self.data.augmentation_params
            },
            'experiment': {
                'experiment_name': self.experiment.experiment_name,
                'output_dir': self.experiment.output_dir,
                'save_best_model': self.experiment.save_best_model,
                'save_last_model': self.experiment.save_last_model,
                'log_level': self.experiment.log_level,
                'save_training_plots': self.experiment.save_training_plots,
                'track_metrics': self.experiment.track_metrics
            }
        }
    
    def save_to_file(self, file_path: str):
        """Save configuration to JSON file."""
        import json
        
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(self.to_dict(), f, indent=2, ensure_ascii=False)
    
    @classmethod
    def load_from_file(cls, file_path: str) -> 'Config':
        """Load configuration from JSON file."""
        import json
        
        with open(file_path, 'r', encoding='utf-8') as f:
            config_dict = json.load(f)
        
        return cls.from_dict(config_dict)


# Predefined configurations for different scenarios

def get_quick_test_config() -> Config:
    """Get configuration for quick testing with reduced epochs."""
    config = Config()
    config.training.num_epochs = 10
    config.training.batch_size = 32
    config.experiment.experiment_name = 'quick_test'
    return config


def get_production_config() -> Config:
    """Get configuration for production training with optimal settings."""
    config = Config()
    config.training.num_epochs = 200
    config.training.batch_size = 16
    config.training.learning_rate = 0.0001
    config.training.use_scheduler = True
    config.training.early_stopping = True
    config.experiment.experiment_name = 'production_training'
    return config


def get_research_config() -> Config:
    """Get configuration for research with extensive tracking."""
    config = Config()
    config.training.num_epochs = 500
    config.training.batch_size = 8
    config.training.learning_rate = 0.0005
    config.data.use_augmentation = True
    config.experiment.experiment_name = 'research_experiment'
    config.experiment.track_metrics = True
    return config


# Gesture class mappings
GESTURE_CLASSES = {
        0: "0", 1: "1", 2: "2", 3: "3", 4: "4",
        5: "5", 6: "6", 7: "7", 8: "8", 9: "9", 10: "10"
    }

# Color mappings for visualization
CLASS_COLORS = {
    0: '#FF0000',  # Red
    1: '#00FF00',  # Green
    2: '#0000FF',  # Blue
    3: '#FFFF00',  # Yellow
    4: '#FF00FF',  # Magenta
    5: '#00FFFF',  # Cyan
    6: '#FFA500',  # Orange
    7: '#800080',  # Purple
    8: '#FFC0CB',  # Pink
    9: '#A52A2A',  # Brown
    10: '#808080'  # Gray
}


if __name__ == "__main__":
    """Example usage of configuration."""
    
    # Create default configuration
    config = Config()
    print("Default configuration created")
    
    # Save to file
    config.save_to_file('config/default_config.json')
    print("Configuration saved to config/default_config.json")
    
    # Create and save different configurations
    configs = {
        'quick_test': get_quick_test_config(),
        'production': get_production_config(),
        'research': get_research_config()
    }
    
    for name, cfg in configs.items():
        cfg.save_to_file(f'config/{name}_config.json')
        print(f"Saved {name} configuration")
    
    # Load and verify
    loaded_config = Config.load_from_file('config/default_config.json')
    print(f"Loaded configuration: {loaded_config.experiment.experiment_name}")
    
    print("\nAvailable gesture classes:")
    for class_id, class_name in GESTURE_CLASSES.items():
        print(f"  {class_id}: {class_name}")
