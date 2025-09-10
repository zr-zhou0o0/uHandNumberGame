import cv2
import mediapipe as mp
import time
import serial
import random
import threading
from enum import Enum

print(f"OpenCV版本: {cv2.__version__}")
print(f"MediaPipe版本: {mp.__version__}")

# 游戏状态枚举
class GameState(Enum):
    MENU = 0
    STARTING = 1
    WAITING_INPUT = 2
    PROCESSING = 3
    GAME_OVER = 4
    PAUSED = 5



#  ['Thumb', 'Index', 'Middle', 'Ring', 'Pinky']
tipIds = [4, 8, 12, 16, 20]  # 指尖关键点索引
thumbIds = [2, 3, 4]  # 拇指关键点索引
indexIds = [5, 6, 7, 8]  # 食指关键点索引
middleIds = [9, 10, 11, 12]  # 中指关键点索引
ringIds = [13, 14, 15, 16]  # 无名指关键点索引
pinkyIds = [17, 18, 19, 20]  # 小指关键点索引


class NumberGame:
    def __init__(self):
        # 串口配置
        self.SERIAL_PORT = 'COM19'  # 根据实际情况修改
        self.BAUD_RATE = 115200
        self.ser = None
        
        # 视频流配置
        self.stream_url = "http://192.168.5.1:81/stream"
        self.cap = None
        
        # MediaPipe配置
        self.mpHand = mp.solutions.hands
        self.hands = None
        self.mpDraw = mp.solutions.drawing_utils
        
        # 手势识别配置
        self.tipIds = [4, 8, 12, 16, 20]
        self.finger_map = {
            (0,0,0,0,0): 0,
            (0,1,0,0,0): 1,
            (0,1,1,0,0): 2,
            (0,1,1,1,0): 3,
            (0,1,1,1,1): 4,
            (1,1,1,1,1): 5,
            (1,0,0,0,1): 6,
            (1,1,0,0,0): 7,
            (1,1,1,0,0): 8,
            (0,2,0,0,0): 9,
        }
        
        # 游戏状态
        self.game_state = GameState.MENU
        self.my_number = 1  # 自身数字
        self.choice = 0 # 0 是左手 1 是右手 每次当机械手更新状态之后都会更新一次choice
        self.opponent_left = -1  # 对手左手
        self.opponent_right = -1  # 对手右手
        self.game_history = []  # 游戏历史
        self.opponent_last_time = [-1, -1]
        
        # 输入识别状态
        self.current_input_left = -1  # 当前识别的数字
        self.current_input_right = -1  # 当前识别的数字
        self.input_start_time_left = 0  # 开始识别时间
        self.input_start_time_right = 0  # 开始识别时间
        self.input_stable_time = 3.0  # 需要保持3秒
        self.last_detection_time = 0
        self.detection_interval = 1.0  # 1秒检测一次
        
        # 游戏计时
        self.game_start_time = 0
        self.round_count = 0

        self.last_time_detect_number = [0,0,0,0]
        
    def init_serial(self):
        """初始化串口通信"""
        try:
            self.ser = serial.Serial(self.SERIAL_PORT, self.BAUD_RATE, timeout=1)
            print(f"串口连接成功: {self.SERIAL_PORT}")
            # time.sleep(2)  # 等待Arduino初始化
            return True
        except Exception as e:
            print(f"串口连接失败: {e}")
            return False
    
    def test_connection_with_timeout(self, url, timeout=10):
        """测试连接是否可用，带超时机制"""
        print(f"正在测试连接: {url} (超时: {timeout}秒)")
        
        connection_result = {"success": False, "cap": None}
        
        def try_connect():
            try:
                cap = cv2.VideoCapture(url)
                # 设置缓冲区大小，减少延迟
                cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
                # 设置连接超时（如果支持）
                cap.set(cv2.CAP_PROP_OPEN_TIMEOUT_MSEC, timeout * 1000)
                cap.set(cv2.CAP_PROP_READ_TIMEOUT_MSEC, 5000)  # 5秒读取超时
                
                if cap.isOpened():
                    # 尝试读取一帧来验证连接
                    ret, frame = cap.read()
                    if ret and frame is not None:
                        print("✓ 连接成功，可以读取视频帧")
                        connection_result["success"] = True
                        connection_result["cap"] = cap
                    else:
                        print("✗ 连接失败：无法读取视频帧")
                        cap.release()
                else:
                    print("✗ 连接失败：无法打开视频流")
                    cap.release()
            except Exception as e:
                print(f"✗ 连接异常: {e}")
                if 'cap' in locals():
                    cap.release()
        
        # 在单独线程中尝试连接
        connect_thread = threading.Thread(target=try_connect)
        connect_thread.daemon = True
        connect_thread.start()
        
        # 等待连接完成或超时
        connect_thread.join(timeout)
        
        if connect_thread.is_alive():
            print(f"✗ 连接超时 ({timeout}秒)")
            return False, None
        
        return connection_result["success"], connection_result["cap"]


    def init_video_capture(self):
        """初始化视频捕获，支持多种源"""
        print("=== 初始化视频源 ===")
        
        # 首先尝试网络流
        success, cap = self.test_connection_with_timeout(self.stream_url, timeout=10)
        
        if success:
            print(f"✓ 使用网络视频流: {self.stream_url}")
            return cap
        
        else:
            return None
        
    # def init_camera(self):
    #     """初始化摄像头"""
    #     try:
    #         # self.cap = cv2.VideoCapture(self.stream_url)
    #         self.cap = self.init_video_capture()
    #         if not self.cap.isOpened():
    #             print("错误：无法连接到视频流")
    #             return False
    #         print("视频流连接成功")
    #         return True
    #     except Exception as e:
    #         print(f"摄像头初始化失败: {e}")
    #         return False
    
    def init_mediapipe(self):
        """初始化MediaPipe"""
        try:
            self.hands = self.mpHand.Hands(
                static_image_mode=False,
                max_num_hands=2,
                min_detection_confidence=0.5,
                min_tracking_confidence=0.5
            )
            print("MediaPipe初始化成功")
            return True
        except Exception as e:
            print(f"MediaPipe初始化失败: {e}")
            return False
    
    def send_command(self, command):
        """发送命令到Arduino"""
        if self.ser and self.ser.is_open:
            try:
                self.ser.write(f"{command}\n".encode())
                print(f"发送命令: {command}")
                return True
            except Exception as e:
                print(f"发送命令失败: {e}")
                return False
        return False
    
    def check_finger_status(self, fingers):
        """检查手指状态，返回对应数字或-1"""
        return self.finger_map.get(tuple(fingers), -1)
    
    def detect_hand_gesture(self, img):
        """检测手势，返回左右手数字"""
        imgRGB = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
        results = self.hands.process(imgRGB)
        
        left_hand_number = -1
        right_hand_number = -1
        
        if results.multi_hand_landmarks:
            for hand_idx, handLms in enumerate(results.multi_hand_landmarks):
                # 绘制手部关键点
                self.mpDraw.draw_landmarks(img, handLms, self.mpHand.HAND_CONNECTIONS)
                
                # 获取关键点坐标
                lmList = []
                for id, lm in enumerate(handLms.landmark):
                    h, w, _ = img.shape
                    cx, cy = int(lm.x * w), int(lm.y * h)
                    lmList.append([id, cx, cy])
                
                if len(lmList) < 21:
                    continue
                
                # 判断左右手
                node2_x = lmList[2][1]
                node17_x = lmList[17][1]
                is_left_hand = node2_x < node17_x
                
                # 检测手指状态
                fingers = []
                
                # 拇指检测
                if is_left_hand:
                    if lmList[self.tipIds[0]][1] < lmList[self.tipIds[0] - 1][1]:
                        fingers.append(1)
                    else:
                        fingers.append(0)
                else:
                    if lmList[self.tipIds[0]][1] > lmList[self.tipIds[0] - 1][1]:
                        fingers.append(1)
                    else:
                        fingers.append(0)
                
                # 食指特殊检测
                if lmList[self.tipIds[1]][2] > lmList[self.tipIds[1] - 3][2]:
                    fingers.append(0)
                elif -30 < (lmList[self.tipIds[1]][2] - lmList[self.tipIds[1] - 2][2]):
                    fingers.append(2)
                else:
                    fingers.append(1)
                
                # 其余三指检测
                for id in range(2, 5):
                    if lmList[self.tipIds[id]][2] < lmList[self.tipIds[id] - 2][2]:
                        fingers.append(1)
                    else:
                        fingers.append(0)
                
                # 识别数字
                number = self.check_finger_status(fingers)
                
                if is_left_hand:
                    left_hand_number = number
                else:
                    right_hand_number = number
        
        return left_hand_number, right_hand_number
    
    def process_input(self, left_num, right_num):
        """处理输入，检查是否稳定"""
        # -1 是没有手 -2 是无效

        current_time = time.time()
        self.last_time_detect_number[0] = current_time
        self.last_time_detect_number[1] = left_num
        self.last_time_detect_number[2] = right_num

        confirmed_input_left = -2
        confirmed_input_right = -2
        
        # 检查left输入稳定性
        if left_num == self.current_input_left:
            if current_time - self.input_start_time_left >= self.input_stable_time:
                # 输入稳定超过3秒，确认输入
                confirmed_input_left = self.current_input_left
                self.current_input_left = -2  # -1 是没有手 -2 是禁止输入
                self.input_start_time_left = 0
        else:
            # 输入改变，重新开始计时
            self.current_input_left = left_num
            self.input_start_time_left = current_time
            confirmed_input_left = -2

        # 检查right输入稳定性
        if right_num == self.current_input_right:
            if current_time - self.input_start_time_right >= self.input_stable_time:
                # 输入稳定超过3秒，确认输入
                confirmed_input_right = self.current_input_right
                self.current_input_right = -2  
                self.input_start_time_right = 0
        else:
            # 输入改变，重新开始计时
            self.current_input_right = right_num
            self.input_start_time_right = current_time
            confirmed_input_right = -2

        if confirmed_input_right != -2 and confirmed_input_left != -2:
            if confirmed_input_right == -1 and confirmed_input_left != -1:
                detected_number = confirmed_input_left
            elif confirmed_input_right != -1 and confirmed_input_left == -1:
                detected_number = confirmed_input_right
            elif confirmed_input_right == -1 and confirmed_input_left == -1:
                detected_number = -1
            else:
                if (self.my_number + confirmed_input_right) % 10 == 0:
                    detected_number = confirmed_input_right
                elif (self.my_number + confirmed_input_left) % 10 == 0:
                    detected_number = confirmed_input_left
                else:
                    # detected_number = random.choice([left_num, right_num]) # 这样会导致不连续
                    if self.choice == 0:
                        detected_number = confirmed_input_left
                    else:
                        detected_number = confirmed_input_right
        else:
            detected_number = -1
        
        self.last_time_detect_number[3] = detected_number

        return detected_number, confirmed_input_left, confirmed_input_right
        
        # 只有一个detectnumber的逻辑
        # 检查输入稳定性
        # if detected_number != -1 and detected_number == self.current_input:
        #     # 继续保持相同输入
        #     if current_time - self.input_start_time >= self.input_stable_time:
        #         # 输入稳定超过3秒，确认输入
        #         confirmed_input = self.current_input
        #         self.current_input = -1  # 重置
        #         self.input_start_time = 0
        #         return confirmed_input, detected_number
        # else:
        #     # 输入改变，重新开始计时
        #     self.current_input = detected_number
        #     self.input_start_time = current_time
        
        # return -1, detected_number  # 还未确认
    
    def start_game(self):
        print("=== 开始新游戏 ===")
        self.game_state = GameState.STARTING
        self.my_number = 1
        self.opponent_left = -1
        self.opponent_right = -1
        self.opponent_last_time = [1, 1]
        self.round_count = 0
        self.choice = random.choice([0,1])
        self.game_start_time = time.time()
        
        time.sleep(2) # 必须等待 否则串口会丢掉这个命令
        self.send_command(11)  # 开始手势，开始提示音，摆成1的动作
        
        self.game_state = GameState.WAITING_INPUT
        print(f"我的数字: {self.my_number}")
        print("等待对手输入...")
    
    def process_game_logic(self, opponent_input):
        """处理游戏逻辑"""
        if self.game_state != GameState.WAITING_INPUT:
            return
        
        self.game_state = GameState.PROCESSING
        self.round_count += 1
        
        print(f"=== 第{self.round_count}轮 ===")
        print(f"对手输入: {opponent_input}")
        print(f"我的当前数字: {self.my_number}")
        
        # 检查对手是否出0（失败）
        if opponent_input == 0:
            print("对手出0，失败！")
            self.send_command(10)  # 失败提示音 & 动作
            self.game_state = GameState.GAME_OVER
            return
        
        # 计算我的新数字（加法取余）
        new_my_number = (self.my_number + opponent_input) % 10
        print(f"计算: ({self.my_number} + {opponent_input}) % 10 = {new_my_number}")
        
        # 检查我是否变成0（失败）
        if new_my_number == 0:
            print("我方数字为0，我方胜利！")
            self.send_command(0)  # 胜利提示音 & 动作
            self.game_state = GameState.GAME_OVER
            return
            
        
        # 更新我的数字
        self.my_number = new_my_number
        
        # 记录游戏历史
        self.game_history.append({
            'round': self.round_count,
            'opponent_input': opponent_input,
            'my_number': self.my_number,
            'time': time.time() - self.game_start_time
        })
        
        # 发送新数字给Arduino显示
        self.send_command(self.my_number)  # 摆出新数字手势
        
        print(f"我的新数字: {self.my_number}")
        print("等待下一轮输入...")
        
        # 等待Arduino执行动作
        # time.sleep(1)
        
        self.game_state = GameState.WAITING_INPUT
    
    def draw_game_info(self, img, font_scale, y_offset, thickness):
        """在图像上绘制游戏信息"""
        h, w, _ = img.shape
        
        # 绘制游戏状态
        state_text = f"State: {self.game_state.name}"
        cv2.putText(img, state_text, (10, 90), 
                   cv2.FONT_HERSHEY_SIMPLEX, font_scale, (255, 0, 0), 2)
        
        # 绘制轮次
        round_text = f"Round: {self.round_count}"
        cv2.putText(img, round_text, (10, 110), 
                   cv2.FONT_HERSHEY_SIMPLEX, font_scale, (255, 0, 0), 2)
    
    def run(self):
        """运行游戏主循环"""
        # 初始化所有组件
        if not self.init_serial():
            print("串口初始化失败，继续运行（仅测试模式）")
        
        cap = self.init_video_capture()
        if not cap.isOpened():
            print("摄像头初始化失败，退出程序")
            return
        
        if not self.init_mediapipe():
            print("MediaPipe初始化失败，退出程序")
            return
        
        mpHand = mp.solutions.hands
        hands = mpHand.Hands(
            static_image_mode=False,
            max_num_hands=2,
            min_detection_confidence=0.5,
            min_tracking_confidence=0.5
        )
        mpDraw = mp.solutions.drawing_utils

        
        print("=== 碰数游戏启动成功 ===")

        frame_count = 0
        last_detection_time = 0  # 上次检测时间
        detection_interval = 0.1  # 检测间隔（秒）

        last_info_time = 0
        info_interval = 1
        
        self.start_game()

        while True:
            current_time = time.time()
            success, img = cap.read()
            
            if not success:
                print("无法读取视频帧")
                break

            # 显示图像
            # cv2.imshow('Number Game', img)

            if current_time - last_detection_time < detection_interval:
                # 等待0.1秒
                time.sleep(0.02)
                continue

            last_detection_time = current_time
            frame_count += 1
            # print(f"进行手势检测 (第{frame_count}帧)")
            
            # 检测手势（1秒一次）
            # left_num, right_num = -1, -1
            # if current_time - self.last_detection_time >= self.detection_interval:
                # self.last_detection_time = current_time
                # left_num, right_num = self.detect_hand_gesture(img)

            
            imgRGB = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
            results = hands.process(imgRGB)

            # 初始化左右手信息
            left_hand_info = {"number": -1, "fingers": []}
            right_hand_info = {"number": -1, "fingers": []}
            total_hands = 0

            if results.multi_hand_landmarks:
                total_hands = len(results.multi_hand_landmarks)
                # print(f"检测到 {total_hands} 只手")
                
                for hand_idx, handLms in enumerate(results.multi_hand_landmarks):
                    mpDraw.draw_landmarks(img, handLms, mpHand.HAND_CONNECTIONS)
                        
                    lmList = []
                    for id, lm in enumerate(handLms.landmark):
                        h, w, _ = img.shape
                        cx, cy = int(lm.x * w), int(lm.y * h)
                        lmList.append([id, cx, cy])

                    if len(lmList) < 21:
                        # print(f"手部 {hand_idx+1}: 关键点不足，跳过")
                        continue
                    
                    # 判断左右手：比较节点2和节点17的x坐标
                    node2_x = lmList[2][1]  # 拇指根部
                    node17_x = lmList[17][1]  # 小指根部
                    
                    if node2_x < node17_x:
                        hand_type = "左手"
                        is_left_hand = True
                    else:
                        hand_type = "右手"
                        is_left_hand = False
                    
                    # print(f"手部 {hand_idx+1}: {hand_type} (节点2: {node2_x}, 节点17: {node17_x})")
                        
                    fingers = []
                    
                    # 拇指检测：根据左右手使用不同逻辑
                    if is_left_hand:
                        # 左手
                        if lmList[tipIds[0]][1] < lmList[tipIds[0] - 1][1]:
                            fingers.append(1)  # 伸展
                        else:
                            fingers.append(0)  # 弯曲
                    else:
                        # 右手
                        if lmList[tipIds[0]][1] > lmList[tipIds[0] - 1][1]:
                            fingers.append(1)  # 伸展
                        else:
                            fingers.append(0)  # 弯曲
                    
                    if lmList[tipIds[1]][2] > lmList[tipIds[1] - 3][2]:
                        fingers.append(0)
                    elif -30 < (lmList[tipIds[1]][2] - lmList[tipIds[1] - 2][2]):
                        fingers.append(2)
                    else:
                        fingers.append(1)

                    # 其余三指检测（上下关系，左右手相同）
                    for id in range(2, 5):
                        if lmList[tipIds[id]][2] < lmList[tipIds[id] - 2][2]:
                            fingers.append(1)
                        else:
                            fingers.append(0)
                            
                    # print(f"手指状态: {fingers}")
                    
                    fingerCount = fingers.count(1)
                    number = self.check_finger_status(fingers)
                    
                    # print(f"{hand_type}: 数字={number}, 手指状态={fingers}")
                    
                    # 存储左右手信息
                    if is_left_hand:
                        left_hand_info["number"] = number
                        left_hand_info["fingers"] = fingers.copy()
                    else:
                        right_hand_info["number"] = number
                        right_hand_info["fingers"] = fingers.copy()
                
            # 显示左右手信息
            y_offset = 30
            font_scale = 0.5
            thickness = 2
            
            # 显示左手信息
            left_text = f"Left Hand: {left_hand_info['number']}, {left_hand_info['fingers']}"
            cv2.putText(img, left_text, (10, y_offset), 
                        cv2.FONT_HERSHEY_SIMPLEX, font_scale, (0, 255, 0), thickness)
            
            # 显示右手信息
            right_text = f"Right Hand: {right_hand_info['number']}, {right_hand_info['fingers']}"
            cv2.putText(img, right_text, (10, y_offset + 30), 
                        cv2.FONT_HERSHEY_SIMPLEX, font_scale, (0, 0, 255), thickness)

            left_num = left_hand_info['number']
            right_num = right_hand_info['number']

            
            # 处理游戏逻辑
            if self.game_state == GameState.WAITING_INPUT:
                confirmed_input, confirm_left, confirm_right = self.process_input(left_num, right_num)
                if confirmed_input != -1:
                    print(f"************** execuate game ********************")
                    if confirm_left != self.opponent_last_time[0] or confirm_right != self.opponent_last_time[1]:
                        # 和上次输入有差别才算做一次新的输入
                        self.opponent_last_time[0] = confirm_left
                        self.opponent_last_time[1] = confirm_right
                        self.choice = random.choice([0,1])
                        self.process_game_logic(confirmed_input)
            
            # 绘制游戏信息
            self.draw_game_info(img, font_scale, y_offset, thickness)

            cv2.imshow('Hand Gesture Recognition', img)
            
            # 处理按键
            # 作用是等待一段时间 保证imshow顺利执行
            key = cv2.waitKey(1) & 0xFF
            if key == ord('q'):
                print("退出游戏")
                break
            elif key == ord('s') and self.game_state == GameState.MENU:
                self.start_game()
            elif key == ord('r'):
                if self.game_state == GameState.GAME_OVER:
                    self.game_state = GameState.MENU
                    print("准备重新开始游戏")
            elif key == ord('p'):
                if self.game_state == GameState.PAUSED:
                    self.game_state = GameState.WAITING_INPUT
                    print("游戏继续")
                elif self.game_state == GameState.WAITING_INPUT:
                    self.game_state = GameState.PAUSED
                    print("游戏暂停")

            if current_time - last_info_time > info_interval:
                last_info_time = current_time
                print(f"游戏状态：{self.game_state}")
                print(f"机械手状态: {self.my_number}")
                print(f"对手左手: {left_num}")
                print(f"对手右手: {right_num}")
                print(f"上次检测时间: {self.last_time_detect_number[0]}")
                print(f"confirm_input: {confirmed_input}")
                print(f"confirm_right: {confirm_right}")
                print(f"confirm_left: {confirm_left}")
                print(f"上次检测左手输入: {self.opponent_last_time[0]}")
                print(f"上次检测右手输入: {self.opponent_last_time[1]}")

        
        # # 清理资源
        # self.cleanup()
    
    def cleanup(self):
        """清理资源"""
        if self.cap:
            self.cap.release()
        if self.ser and self.ser.is_open:
            self.ser.close()
        cv2.destroyAllWindows()
        print("资源清理完成")

def main():
    game = NumberGame()
    game.run()


if __name__ == "__main__":
    main()
    # game = NumberGame()
   
    # cap = game.init_video_capture()
    # # cap = cv2.VideoCapture(stream_url)
    # # cap = cv2.VideoCapture(0)
    # # cap.set(3, 640)  # 设置帧宽度
    # # cap.set(4, 480)  # 设置帧高度

    # # 检查视频流是否成功打开
    # if not cap.isOpened():
    #     print("错误：无法连接到视频流")
    # else:
    #     print("成功连接到视频流")

    # print("初始化MediaPipe...")
    # mpHand = mp.solutions.hands
    # hands = mpHand.Hands(
    #     static_image_mode=False,
    #     max_num_hands=2,
    #     min_detection_confidence=0.5,
    #     min_tracking_confidence=0.5
    # )
    # mpDraw = mp.solutions.drawing_utils

    # #  ['Thumb', 'Index', 'Middle', 'Ring', 'Pinky']
    # tipIds = [4, 8, 12, 16, 20]  # 指尖关键点索引
    # thumbIds = [2, 3, 4]  # 拇指关键点索引
    # indexIds = [5, 6, 7, 8]  # 食指关键点索引
    # middleIds = [9, 10, 11, 12]  # 中指关键点索引
    # ringIds = [13, 14, 15, 16]  # 无名指关键点索引
    # pinkyIds = [17, 18, 19, 20]  # 小指关键点索引

    # frame_count = 0
    # last_detection_time = 0  # 上次检测时间
    # # detection_interval = 0.5  # 检测间隔（秒）
    # detection_interval = 0.1  # 检测间隔（秒）

    # while True:
    #     current_time = time.time()
    #     success, img = cap.read()

    #     if not success:
    #         print(f"错误：无法读取视频帧 (第{frame_count}帧)")
    #         break

    #     if current_time - last_detection_time < detection_interval:
    #         # 等待0.1秒
    #         time.sleep(0.02)
    #         continue

    #     last_detection_time = current_time
    #     frame_count += 1
    #     print(f"进行手势检测 (第{frame_count}帧)")
        
    #     imgRGB = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
    #     results = hands.process(imgRGB)

      

    #     cv2.imshow('Hand Gesture Recognition', img)
    #     print("成功显示图像")

    #     key = cv2.waitKey(1) & 0xFF # 居然没有这个waitkey 就显示不出来视频！！！！！！！！
    #     if key == ord('q'):
    #         print("用户按下 'q' 键，退出程序")
    #         break
    #     elif key != 255:  # 如果有其他按键被按下
    #         print(f"按键被按下: {chr(key)} (ASCII: {key})")
       