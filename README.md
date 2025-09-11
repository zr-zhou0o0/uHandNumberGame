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
    - 通过python实现碰数游戏逻辑
        - 识别输入：调用 gesture recognition 脚本，得到实时的手势信息；手势识别，维持同一个有效数字超过3秒钟则判定输入
        - 串口通信： serial command脚本：向 arduino 输出一个编号 在arduino中执行编号对应的动作策略和提示音
        - （按键重定义 & 回传：红色代表重新开始游戏，黄色代表暂停游戏）
    - 1 对 1
        - 开始游戏：串口输出11，代表开始手势，开始提示音，然后摆成1的动作
        - 维护一个列表 自身数字、对手左手、对手右手数字 
        - 然后开始等待识别输入
        - 输入判定：维持相同输入超过2秒钟并且与上回合输入不同，则判定为一次新的有效输入
        - 加法取余：一旦识别到输入，则输入数字与自身数字相加并取余，并更新列表
        - 若对方输入是0，则游戏结束，串口输出10，失败提示音 & 动作
    	- 若自身相加取余后是0，则游戏结束，串口输出0，胜利提示音 & 动作
    	- 否则，就摆出更新后的自身数字手势（1~9，对应串口编号也为1~9），并开始下一轮游戏
    - 1 对 2
        - 机械手能够通过手势识别区分对方左右手
        - 轮到机械手时，首先判断对手左右手是否还在场上；然后判定是否存在可以碰成0的数；若无，则从对手左右手中随机选择一个手来碰。
        - 若对手只剩下一个手，并且这一个手碰为了0，那么则判定对手胜利。
    - 1 对 2 提升版 （暴力枚举法）
        - 当对手左右手均在场、且不存在机械手直接碰成0的情况时，轮到机械手碰玩家时，不再随机选择，而是遵循最优策略。
        - 定义机械手碰一次+玩家碰一次为一个回合；定义 [a, b, c] 分别代表机械手、玩家左手、玩家右手的数值；我们预计算了导致机械手负的倒数三个回合的情况，游戏时只需要查询胜负表即可确定碰左或碰右：
            - **最后一个回合**：单手碰数，机械手没有选择。`scripts\game\one_one_enum.json` 显示了当场上只剩下1只机械手和1只玩家手的情况时（此时一定是机械手先出，因为玩家刚刚碰出0并收回了一个手），机械手的胜负情况。1对1的时候，胜负是固定的，因此只需当出现玩家收手的时候，确保场上剩余手的情况落在机械手胜的区域即可。
            - 出现玩家收手的情况只有四种：条件1或2：碰b后c消失，碰c后b消失；条件3或4：碰b后b消失，碰c后c消失。
                - a + b + c = 10
                - a + b + c = 20
                - a + 2b = 10 且 a + 2c = 20
                - a + 2c = 10 且 a + 2b = 20
            - **倒数第二个回合**：玩家收手回合，碰左/右决定了玩家收哪只手。遍历 a、b、c 从 0~9 分别枚举这四种情况，得到 `scripts\game\one_two_enum.json` 显示了当玩家必须要收手的时候，碰玩家左手和右手所带来的最终胜负。*因此如果检测到满足玩家收手回合时，通过查询`scripts\game\one_two_enum.json`碰左右来控制胜负。*
            - 经过枚举，收手回合存在八种情况，会导致无论碰左或右，机械手都会输，定义为`loss_states_two`：
				- (2, 3, 5)
				- (2, 5, 3)
				- (4, 1, 5)
				- (4, 5, 1)
				- (6, 5, 9)
				- (6, 9, 5)
				- (8, 5, 7)
				- (8, 7, 5)
			- 所以需要通过倒数第三个回合来避免倒数第二个回合掉入`loss_states_two`；只要未进入`loss_states_two`，那么机械手不会输。
			- **倒数第三个回合**：普通回合。一个回合经历了机械手碰玩家一次、玩家碰机械手一次，两个动作。因此一组回合开始状态 [a, b, c] 对应四组回合结束状态，根据机械手碰b或者c分成两种情况，有一种情况完全未落到`loss_states_two`即可。因此在普通回合，预先计算四种结束状态，选择一个对应的两种不属于`loss_states_two`的结果去碰即可。
			- 经过枚举，普通回合存在四种情况，会导致这一回合的四个结束状态均落入`loss_states_two`中，定义为`loss_states_three`, 分别是：
    			- (1, 7, 7)
				- (3, 1, 1)
				- (7, 9, 9)
				- (9, 3, 3)
    		- 所以需要保证普通回合不出现这四种情况，以至于引向必败的情况。
    		- **倒数第四个回合**：普通回合。根据机械手碰b或者c分成两种情况，有一种情况完全未落到`loss_states_three`里面即可。经过枚举，不存在 [a, b, c] 使得碰b或者c都存在落进去的可能性。
    		- 最后一种情况：一些结果落到 `loss_states_two` 一些落到 `loss_states_three`，经过枚举，并不存在。*所以在普通回合，直接避免这 8 + 4 种情况即可。*


- 蜂鸣器
    - 游戏开始 提示音 1
    - 胜利/失败提示音 提示音2 3
    - 回合提示音 提示音 4
- 2 对 2 （由于实验器材和时间的限制未实现）
	- 强化学习

## **环境**
conda activate handgesture-medi
连接串口，关闭arduino的串口监视器
连接摄像头网络，启动视频流，关闭网页


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
python scripts\gesture_recognition_opencv\gesture_recognition_timeout.py


## **serial command**
python scripts\serial\serial_command.py


## **play**
python scripts\game\game.py

