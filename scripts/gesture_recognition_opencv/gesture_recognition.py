import cv2
import mediapipe as mp
import time
import sys

print(f"OpenCV版本: {cv2.__version__}")
print(f"MediaPipe版本: {mp.__version__}")

stream_url="http://192.168.5.1:81/stream"

finger_map = {
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

def check_finger_status(fingers):
    """检查手指状态，返回对应数字或-1"""
    return finger_map.get(tuple(fingers), -1)


cap = cv2.VideoCapture(stream_url)
# cap = cv2.VideoCapture(0)
# cap.set(3, 640)  # 设置帧宽度
# cap.set(4, 480)  # 设置帧高度

# 检查视频流是否成功打开
if not cap.isOpened():
    print("错误：无法连接到视频流")
else:
    print("成功连接到视频流")

print("初始化MediaPipe...")
mpHand = mp.solutions.hands
hands = mpHand.Hands(
    static_image_mode=False,
    max_num_hands=2,
    min_detection_confidence=0.5,
    min_tracking_confidence=0.5
)
mpDraw = mp.solutions.drawing_utils

#  ['Thumb', 'Index', 'Middle', 'Ring', 'Pinky']
tipIds = [4, 8, 12, 16, 20]  # 指尖关键点索引
thumbIds = [2, 3, 4]  # 拇指关键点索引
indexIds = [5, 6, 7, 8]  # 食指关键点索引
middleIds = [9, 10, 11, 12]  # 中指关键点索引
ringIds = [13, 14, 15, 16]  # 无名指关键点索引
pinkyIds = [17, 18, 19, 20]  # 小指关键点索引

frame_count = 0
last_detection_time = 0  # 上次检测时间
# detection_interval = 0.5  # 检测间隔（秒）
detection_interval = 0.1  # 检测间隔（秒）

while True:
    current_time = time.time()
    success, img = cap.read()

    if not success:
        print(f"错误：无法读取视频帧 (第{frame_count}帧)")
        break

    cv2.imshow('Hand Gesture Recognition', img)

    if current_time - last_detection_time < detection_interval:
        # 等待0.1秒
        time.sleep(0.02)
        continue

    last_detection_time = current_time
    frame_count += 1
    print(f"进行手势检测 (第{frame_count}帧)")
    
    imgRGB = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
    results = hands.process(imgRGB)

    # 初始化左右手信息
    left_hand_info = {"number": -1, "fingers": []}
    right_hand_info = {"number": -1, "fingers": []}
    total_hands = 0

    if results.multi_hand_landmarks:
        total_hands = len(results.multi_hand_landmarks)
        print(f"检测到 {total_hands} 只手")
        
        for hand_idx, handLms in enumerate(results.multi_hand_landmarks):
            mpDraw.draw_landmarks(img, handLms, mpHand.HAND_CONNECTIONS)
                
            lmList = []
            for id, lm in enumerate(handLms.landmark):
                h, w, _ = img.shape
                cx, cy = int(lm.x * w), int(lm.y * h)
                lmList.append([id, cx, cy])

            if len(lmList) < 21:
                print(f"手部 {hand_idx+1}: 关键点不足，跳过")
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
            
            print(f"手部 {hand_idx+1}: {hand_type} (节点2: {node2_x}, 节点17: {node17_x})")
                
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
                    
            print(f"手指状态: {fingers}")
            
            fingerCount = fingers.count(1)
            number = check_finger_status(fingers)
            
            print(f"{hand_type}: 数字={number}, 手指状态={fingers}")
            
            # 存储左右手信息
            if is_left_hand:
                left_hand_info["number"] = number
                left_hand_info["fingers"] = fingers.copy()
            else:
                right_hand_info["number"] = number
                right_hand_info["fingers"] = fingers.copy()
    else:
        print("未检测到手部")

    # 显示左右手信息
    y_offset = 30
    font_scale = 0.6
    thickness = 2
    
    # 显示左手信息
    left_text = f"Left Hand: {left_hand_info['number']}, {left_hand_info['fingers']}"
    cv2.putText(img, left_text, (10, y_offset), 
                cv2.FONT_HERSHEY_SIMPLEX, font_scale, (0, 255, 0), thickness)
    
    # 显示右手信息
    right_text = f"Right Hand: {right_hand_info['number']}, {right_hand_info['fingers']}"
    cv2.putText(img, right_text, (10, y_offset + 30), 
                cv2.FONT_HERSHEY_SIMPLEX, font_scale, (0, 0, 255), thickness)

    cv2.imshow('Hand Gesture Recognition', img)
    print("成功显示图像")

    key = cv2.waitKey(1) & 0xFF
    if key == ord('q'):
        print("用户按下 'q' 键，退出程序")
        break
    elif key != 255:  # 如果有其他按键被按下
        print(f"按键被按下: {chr(key)} (ASCII: {key})")

cap.release()
cv2.destroyAllWindows()