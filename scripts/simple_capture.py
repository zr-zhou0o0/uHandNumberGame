#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ESP32-CAM 简单图像捕获脚本
每秒保存一张图片

使用前请安装依赖:
pip install opencv-python requests
"""

import cv2
import time
import os
from datetime import datetime

def capture_esp32cam_images():
    """从ESP32-CAM每秒捕获一张图像"""
    
    # 配置参数
    stream_url = "http://192.168.5.1:81/stream"
    save_dir = "captured_images"
    
    # 创建保存目录
    if not os.path.exists(save_dir):
        os.makedirs(save_dir)
        print(f"已创建目录: {save_dir}")
    
    print("开始捕获ESP32-CAM图像...")
    print("按 Ctrl+C 停止")
    
    # 打开视频流
    cap = cv2.VideoCapture(stream_url)
    
    if not cap.isOpened():
        print("无法连接到视频流，请检查:")
        print("1. 是否已连接ESP32-CAM的WiFi")
        print("2. 是否已在网页上启动视频流")
        return
    
    print("视频流连接成功！")
    
    image_count = 0
    last_save_time = 0
    
    try:
        while True:
            ret, frame = cap.read()
            
            if not ret:
                print("读取帧失败，重试中...")
                time.sleep(0.1)
                continue
            
            current_time = time.time()
            
            # 每秒保存一张图片
            if current_time - last_save_time >= 1.0:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                filename = f"esp32cam_{timestamp}.jpg"
                filepath = os.path.join(save_dir, filename)
                
                # 保存图像
                if cv2.imwrite(filepath, frame):
                    image_count += 1
                    print(f"保存第 {image_count} 张图片: {filename}")
                    last_save_time = current_time
                else:
                    print(f"保存失败: {filename}")
            
            # 显示视频 (可选，按q键退出)
            cv2.imshow('ESP32-CAM', frame)
            if cv2.waitKey(1) & 0xFF == ord('q'):
                break
                
    except KeyboardInterrupt:
        print("\n停止捕获...")
    
    finally:
        cap.release()
        cv2.destroyAllWindows()
        print(f"总共保存了 {image_count} 张图片")

if __name__ == "__main__":
    capture_esp32cam_images()
