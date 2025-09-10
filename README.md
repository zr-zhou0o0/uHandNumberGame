《碰数游戏》--机械手

- 机械手组装
- 环境搭建 串口连接 程序编译与下载
- 旋钮操作
- 运动控制
	- 手指屈伸
	- 摆出数字0-9
	- 胜利手势（比耶）
	- 失败手势（比中指/挥手拜拜）
	- 处理串口命令
		-1: 无
		0：手势0，手势胜利，胜利提示音，黄色
		1：手势1，回合提示音，蓝色
		2：手势2，回合提示音，蓝色
		3：手势3，回合提示音，蓝色
		4：手势4，回合提示音，蓝色
		5：手势5，回合提示音，蓝色
		6：手势6，回合提示音，蓝色
		7：手势7，回合提示音，蓝色
		8：手势8，回合提示音，蓝色
		9：手势9，回合提示音，蓝色
		10：手势失败，失败提示音，红色
		11：手势1，开始提示音，绿色
		- 手势 1~9 对应 ActionGroup 1~9
		- 手势 0 对应 ActionGroup 10
		- 手势胜利对应 ActionGroup 11
		- 手势失败对应 ActionGroup 12
		- 检验手势对应 ActionGroup 13 无需使用
- 手势识别
    - 相机组装
    - 相机环境搭建
        - 固件烧录
        - 图像回传 192.168.5.1
	- 基于神经网络的手势识别
    	- 准备数据集
        	- github数据集
        	- 扩展数据集（现场拍摄）：包含左手、右手；正手、反手、侧面；干净的墙面背景和杂乱背景；
        	- 数据增强：旋转、左右上下翻转、加噪音
        	- 数据集大小问题：MINIST数据集包含70000张手写数字；手势数据集在扩展前应该至少包含7000张手势图片，即一个手势需要约700张图片。
        	- 目前的数据集只支持右手、正手朝上、在浅色背景下的情况
        	- 目前网络上没有较为完整的手势数据集
        	- 模型参数量 132,826，参数量与数据集比例应当在 1:5 ~ 1:50 之间，因此需要约 600,000 手势图片；实际数据 在 160，000左右，准确率达到 72.97%
        	- 增加到 241,863 张手势图片，效果反而下降。
        	- 缩减版模型参数量 42,362，数据量 67,066 张图片， Best Acc=56.76%
        	<!-- - 减少模型参数量到 42,362 并增加数据集到约 240,000 张图片，识别效果提升到 91.35% -->
	- 基于OpenCV和Medpipe的手势识别
      	- 准确率非常高
	- 体感手套数字识别
	- 左右手颜色识别
	- 通过逻辑计算进行游戏
- python到arduino的串口通信
    - 使用pyserial库实现
- 游戏逻辑
    - 通过python实现游戏逻辑
        - 调用 gesture recognition 脚本 和 get img 脚本，得到实时的手势信息
        - 向 arduino 输出一个元组 (number, music) 其中 number 代表预先设置好的动作索引，music 代表预先设置好的提示音索引
        - （按键重定义 & 回传：红色代表重新开始游戏，黄色代表暂停游戏）
    - 1 对 1
        - 开始游戏：开始手势，开始提示音，然后摆成1的动作
        - 维护一个列表 自身数字、对手左手、对手右手数字
        - 识别输入：维持同一个有效数字超过3秒钟则判定输入，发出回合提示音；若对方输入是0，则游戏结束，失败提示音 & 动作
        - 加法取余：输入与自身数字相加并取余
    	- 游戏结束判定：若自身取余后是0，则游戏结束，胜利提示音 & 动作
    - 1 对 2
        - 
	
- 蜂鸣器
    - 游戏开始 提示音 1
    - 胜利/失败提示音 提示音2 3
    - 回合提示音 提示音 4
- 2 对 2 （由于实验器材和时间的限制未实现）
	- 强化学习

## **环境**
conda activate handgesture-medi


## **获取图像**
在浏览器中打开 http://192.168.5.1 并启动视频流

python scripts\camera\get_img.py


## **data augmentation**

<!-- python scripts\datasets\binary_dataset.py --input datasets\camera_phone_raw --output datasets\camera_phone_bin --threshold 150 -->

<!-- python scripts\gesture_recognition\data_preprocessing.py --input datasets\camera_phone_raw --output datasets\camera_phone_aug --target-size 64 64 --save-augmented --augmentation-factor 15 -->
python scripts\gesture_recognition\data_preprocessing.py --input datasets\camera_phone_raw --output datasets\camera_phone_aug --target-size 64 64 --save-augmented --augmentation-factor 10

python scripts\datasets\merge_dataset.py --augmented-dir datasets\camera_phone_aug\augmented_dataset --target-dir datasets\train --mode copy 


## **train**
python train.py


## **inference**
python inference.py --model models\best-7297\cnn_gesture_best.pth --mode image --input datasets\camera_phone_aug\augmented_dataset\img3\img3_000039.jpg


## **gesture recognition**
python scripts\gesture_recognition_opencv\gesture_recognition.py




