# Gesture Recognition with PyTorch

这是一个基于PyTorch的中文数字手势识别系统，是对原始TensorFlow版本的现代化重写。

## 项目结构

```
scripts/gesture_recognition/
├── cnn_pytorch.py          # 主要的CNN模型和训练代码
├── inference.py            # 推理脚本，用于预测新图像
├── data_preprocessing.py   # 数据预处理工具
├── config.py              # 配置管理
├── requirements.txt        # Python依赖包
└── README.md              # 本文件
```

## 功能特点

- **现代化的PyTorch实现**：使用最新的PyTorch最佳实践
- **模块化设计**：代码结构清晰，易于维护和扩展
- **灵活的配置管理**：支持多种训练配置
- **完整的数据预处理**：包含数据增强和格式转换
- **多种推理模式**：支持单图像、批量和实时摄像头预测
- **详细的日志记录**：完整的训练过程跟踪

## 安装依赖

```bash
pip install -r requirements.txt
```

主要依赖包：
- torch
- torchvision
- opencv-python
- numpy
- matplotlib
- scikit-learn
- Pillow

## 使用方法

### 1. 数据预处理

数据预处理脚本现在直接分析文件夹结构，无需创建额外的数据文件：

```bash
# 分析数据集结构并生成统计信息
python data_preprocessing.py --input datasets/captured --output dataset_info

# 查看数据集样本（包含可视化）
python data_preprocessing.py --input datasets/captured --output dataset_info --visualize
```

预期的输入目录结构：
```
datasets/captured/
├── img0/          # 数字0的图像
├── img1/          # 数字1的图像
├── img2/          # 数字2的图像
...
└── img10/         # 数字10的图像
```

**注意**：与原始版本不同，现在不再需要创建HDF5文件。模型直接从图像文件夹加载数据，这样更加灵活且节省内存。

### 2. 模型训练

```bash
# 使用默认配置训练
python cnn_pytorch.py

# 使用自定义配置
python config.py  # 生成配置文件
python cnn_pytorch.py --config config/production_config.json
```

训练过程中会：
- 自动划分训练集和测试集
- 应用数据增强（如果启用）
- 定期评估模型性能
- 保存最佳模型
- 生成训练历史图表

### 3. 模型推理

#### 单张图像预测
```bash
python inference.py --model models/cnn_gesture_pytorch.pth --mode image --input path/to/image.jpg
```

#### 批量图像预测
```bash
python inference.py --model models/cnn_gesture_pytorch.pth --mode batch --input path/to/images/ --output results.json
```

#### 实时摄像头预测
```bash
python inference.py --model models/cnn_gesture_pytorch.pth --mode camera
```

## 配置说明

### 模型配置 (ModelConfig)
- `num_classes`: 类别数量（默认11，包含0-10）
- `dropout_rate`: Dropout率（默认0.5）
- `input_size`: 输入图像尺寸（默认64x64）

### 训练配置 (TrainingConfig)
- `num_epochs`: 训练轮数（默认100）
- `batch_size`: 批大小（默认16）
- `learning_rate`: 学习率（默认0.001）
- `weight_decay`: L2正则化系数（默认1e-4）
- `early_stopping`: 是否使用早停（默认True）

### 数据配置 (DataConfig)
- `data_path`: 数据文件路径
- `train_split`: 训练集比例（默认0.9）
- `use_augmentation`: 是否使用数据增强
- `augmentation_params`: 数据增强参数

## 模型架构

CNN模型包含以下层：

1. **卷积层1**: 3 → 32 通道，5x5卷积核，ReLU激活
2. **最大池化层1**: 2x2池化
3. **卷积层2**: 32 → 64 通道，5x5卷积核，ReLU激活
4. **最大池化层2**: 2x2池化
5. **全连接层1**: 16384 → 200，ReLU激活，Dropout
6. **输出层**: 200 → 11，用于11个手势类别

## 手势类别

系统能识别以下中文数字手势：

| 类别ID | 手势名称 |
|--------|----------|
| 0      | 0 (零)   |
| 1      | 1 (一)   |
| 2      | 2 (二)   |
| 3      | 3 (三)   |
| 4      | 4 (四)   |
| 5      | 5 (五)   |
| 6      | 6 (六)   |
| 7      | 7 (七)   |
| 8      | 8 (八)   |
| 9      | 9 (九)   |
| 10     | 10 (十)  |

## 性能优化建议

1. **数据质量**：
   - 确保图像质量良好，光线充足
   - 手势清晰可见，背景简单
   - 每个类别的样本数量尽量均衡

2. **训练优化**：
   - 使用GPU加速训练
   - 调整批大小以适应显存
   - 使用学习率调度器
   - 启用早停防止过拟合

3. **模型改进**：
   - 尝试不同的网络架构
   - 调整dropout率和正则化参数
   - 使用预训练模型进行迁移学习

## 故障排除

### 常见问题

1. **CUDA out of memory**：
   - 减小batch_size
   - 使用更小的图像尺寸

2. **训练不收敛**：
   - 降低学习率
   - 增加训练数据
   - 调整模型架构

3. **预测准确率低**：
   - 检查数据质量
   - 增加数据增强
   - 调整模型复杂度

### 日志分析

训练过程中的关键指标：
- **Train Loss**: 训练损失，应该逐渐下降
- **Test Loss**: 测试损失，不应该持续上升
- **Test Accuracy**: 测试准确率，目标是尽可能高

## 扩展功能

### 添加新的手势类别

1. 收集新手势的图像数据
2. 更新`config.py`中的`GESTURE_CLASSES`
3. 修改`num_classes`参数
4. 重新训练模型

### 使用不同的网络架构

1. 继承`CNNGestureRecognizer`类
2. 重写`__init__`和`forward`方法
3. 在训练脚本中使用新模型

### 实时应用集成

参考`inference.py`中的`predict_from_camera`函数，可以轻松集成到实时应用中。

## 许可证

本项目基于原始的TensorFlow实现进行重写和改进，保持开源协议。

## 贡献

欢迎提交问题报告和功能请求。如果您想贡献代码，请：

1. Fork项目
2. 创建功能分支
3. 提交更改
4. 创建Pull Request

## 联系信息

如有问题或建议，请通过GitHub Issues联系。
