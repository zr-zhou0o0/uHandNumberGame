#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ESP32-CAM 图像捕获脚本
从 http://192.168.5.1:81/stream 捕获视频流并每秒保存一张图片

使用方法:
1. 上电顺序：电池-扩展板-uno端口-摄像头端口
2. 断电重启摄像头：重新拔插一下IIS线 + RESET按键 + 重新拔插一下相机扩展板 + 天线摆正
3. 烧录图像回传固件：erase-start DIO或DOUT 注意等待finish
4. 蓝灯点亮说明有WiFi；如果没有WiFi就再重启一次
5. 电脑连接到ESP32-CAM的WiFi热点
6. 在浏览器中打开 http://192.168.5.1 并启动视频流
7. 运行此脚本开始保存图像

依赖库:
pip install opencv-python requests pillow
"""

import cv2
import time
import os
import glob
from datetime import datetime
import requests
from PIL import Image
import numpy as np

class ESP32CamCapture:
    def __init__(self, stream_url="http://192.168.5.1:81/stream", save_dir="captured_images"):
        """
        初始化ESP32-CAM捕获器
        
        Args:
            stream_url: 视频流URL
            save_dir: 保存图像的目录
        """
        self.stream_url = stream_url
        self.save_dir = save_dir
        self.running = False
        
        # 创建保存目录
        if not os.path.exists(save_dir):
            os.makedirs(save_dir)
            print(f"已创建目录: {save_dir}")
    
    def test_connection(self):
        """测试与ESP32-CAM的连接"""
        try:
            response = requests.get("http://192.168.5.1", timeout=5)
            if response.status_code == 200:
                print("✓ 成功连接到ESP32-CAM")
                return True
            else:
                print(f"✗ 连接失败，状态码: {response.status_code}")
                return False
        except requests.exceptions.RequestException as e:
            print(f"✗ 连接失败: {e}")
            return False
    
    def clear_images_folder(self):
        """清空图像文件夹"""
        try:
            files = glob.glob(os.path.join(self.save_dir, "*.jpg"))
            files.extend(glob.glob(os.path.join(self.save_dir, "*.jpeg")))
            files.extend(glob.glob(os.path.join(self.save_dir, "*.png")))
            
            if not files:
                print(f"✓ 文件夹 {self.save_dir} 已经为空")
                return
            
            print(f"找到 {len(files)} 个图像文件")
            confirm = input("确认要删除所有图像文件吗？(y/N): ").strip().lower()
            
            if confirm == 'y' or confirm == 'yes':
                deleted_count = 0
                for file in files:
                    try:
                        os.remove(file)
                        deleted_count += 1
                    except Exception as e:
                        print(f"✗ 删除文件失败 {file}: {e}")
                
                print(f"✓ 成功删除 {deleted_count} 个文件")
            else:
                print("取消删除操作")
                
        except Exception as e:
            print(f"✗ 清空文件夹时发生错误: {e}")
    
    def manage_image_count(self, max_keep):
        """
        管理图像数量，只保留最新的指定数量的图像
        
        Args:
            max_keep: 最多保留的图像数量
        """
        try:
            # 获取所有图像文件
            pattern = os.path.join(self.save_dir, "esp32cam_*.jpg")
            files = glob.glob(pattern)
            
            if len(files) <= max_keep:
                return
            
            # 按修改时间排序，最新的在后
            files.sort(key=lambda x: os.path.getmtime(x))
            
            # 删除多余的文件（保留最新的max_keep个）
            files_to_delete = files[:-max_keep]
            
            for file in files_to_delete:
                try:
                    os.remove(file)
                    print(f"删除旧文件: {os.path.basename(file)}")
                except Exception as e:
                    print(f"✗ 删除文件失败 {file}: {e}")
                    
        except Exception as e:
            print(f"✗ 管理文件数量时发生错误: {e}")

    def capture_images_with_limit(self, interval=1, max_keep=10):
        """
        连续捕获图像，只保留最后的指定数量的图像
        
        Args:
            interval: 保存间隔（秒）
            max_keep: 最多保留的图像数量
        """
        print(f"开始从 {self.stream_url} 连续捕获图像...")
        print(f"保存间隔: {interval}秒")
        print(f"最多保留: {max_keep}张图像")
        print(f"保存目录: {self.save_dir}")
        print("按 Ctrl+C 停止捕获\n")
        
        # 打开视频流
        cap = cv2.VideoCapture(self.stream_url)
        
        if not cap.isOpened():
            print("✗ 无法打开视频流，请确保:")
            print("  1. 已连接到ESP32-CAM的WiFi")
            print("  2. ESP32-CAM已启动视频流")
            print("  3. 可以在浏览器中访问 http://192.168.5.1")
            return
        
        print("✓ 视频流已连接")
        
        self.running = True
        image_count = 0
        last_save_time = 0
        
        try:
            while self.running:
                ret, frame = cap.read()
                
                if not ret:
                    print("✗ 无法读取帧，可能连接中断")
                    time.sleep(1)
                    continue
                
                current_time = time.time()
                
                # 每隔指定时间保存一张图片
                if current_time - last_save_time >= interval:
                    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                    filename = f"esp32cam_{timestamp}_{image_count:04d}.jpg"
                    filepath = os.path.join(self.save_dir, filename)
                    
                    # 保存图像
                    success = cv2.imwrite(filepath, frame)
                    
                    if success:
                        image_count += 1
                        print(f"✓ 保存图像 #{image_count}: {filename}")
                        last_save_time = current_time
                        
                        # 管理图像数量，只保留最新的max_keep张
                        self.manage_image_count(max_keep)
                        
                    else:
                        print(f"✗ 保存图像失败: {filename}")
                
                # 显示实时视频 (可选)
                cv2.imshow('ESP32-CAM Stream', frame)
                
                # 按 'q' 键或关闭窗口退出
                if cv2.waitKey(1) & 0xFF == ord('q'):
                    print("\n用户按 'q' 键退出")
                    break
                
        except KeyboardInterrupt:
            print("\n\n用户中断，停止捕获...")
        
        finally:
            self.running = False
            cap.release()
            cv2.destroyAllWindows()
            print(f"\n捕获结束，共保存 {image_count} 张图像")

    def capture_images(self, interval=1, max_images=None):
        """
        捕获图像
        
        Args:
            interval: 保存间隔（秒）
            max_images: 最大保存图像数量，None表示无限制
        """
        print(f"开始从 {self.stream_url} 捕获图像...")
        print(f"保存间隔: {interval}秒")
        print(f"保存目录: {self.save_dir}")
        print("按 Ctrl+C 停止捕获\n")
        
        # 打开视频流
        cap = cv2.VideoCapture(self.stream_url)
        
        if not cap.isOpened():
            print("✗ 无法打开视频流，请确保:")
            print("  1. 已连接到ESP32-CAM的WiFi")
            print("  2. ESP32-CAM已启动视频流")
            print("  3. 可以在浏览器中访问 http://192.168.5.1")
            return
        
        print("✓ 视频流已连接")
        
        self.running = True
        image_count = 0
        last_save_time = 0
        
        try:
            while self.running:
                ret, frame = cap.read()
                
                if not ret:
                    print("✗ 无法读取帧，可能连接中断")
                    time.sleep(1)
                    continue
                
                current_time = time.time()
                
                # 每隔指定时间保存一张图片
                if current_time - last_save_time >= interval:
                    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                    filename = f"esp32cam_{timestamp}_{image_count:04d}.jpg"
                    filepath = os.path.join(self.save_dir, filename)
                    
                    # 保存图像
                    success = cv2.imwrite(filepath, frame)
                    
                    if success:
                        image_count += 1
                        print(f"✓ 保存图像 #{image_count}: {filename}")
                        last_save_time = current_time
                        
                        # 检查是否达到最大图像数量
                        if max_images and image_count >= max_images:
                            print(f"\n已达到最大图像数量 ({max_images})，停止捕获")
                            break
                    else:
                        print(f"✗ 保存图像失败: {filename}")
                
                # 显示实时视频 (可选)
                cv2.imshow('ESP32-CAM Stream', frame)
                
                # 按 'q' 键或关闭窗口退出
                if cv2.waitKey(1) & 0xFF == ord('q'):
                    print("\n用户按 'q' 键退出")
                    break
                
        except KeyboardInterrupt:
            print("\n\n用户中断，停止捕获...")
        
        finally:
            self.running = False
            cap.release()
            cv2.destroyAllWindows()
            print(f"\n捕获结束，共保存 {image_count} 张图像")
    
    def capture_single_image(self):
        """捕获单张图像"""
        cap = cv2.VideoCapture(self.stream_url)
        
        if not cap.isOpened():
            print("✗ 无法打开视频流")
            return None
        
        ret, frame = cap.read()
        cap.release()
        
        if ret:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"esp32cam_single_{timestamp}.jpg"
            filepath = os.path.join(self.save_dir, filename)
            
            success = cv2.imwrite(filepath, frame)
            if success:
                print(f"✓ 保存单张图像: {filename}")
                return filepath
            else:
                print(f"✗ 保存失败: {filename}")
                return None
        else:
            print("✗ 无法读取帧")
            return None


def main():
    """主函数"""
    print("ESP32-CAM 图像捕获工具")
    print("=" * 40)
    
    # 创建捕获器实例
    capture = ESP32CamCapture()
    
    # 测试连接
    if not capture.test_connection():
        print("\n请检查连接后重试")
        return
    
    # 显示菜单
    while True:
        print("\n请选择操作:")
        print("1. 连续捕获图像 (每1秒保存)")
        print("2. 连续捕获图像 (自定义间隔)")
        print("3. 连续捕获图像 (限制保留数量)")
        print("4. 捕获单张图像")
        print("5. 清空图像文件夹")
        print("6. 退出")
        
        choice = input("\n请输入选择 (1-6): ").strip()
        
        if choice == '1':
            capture.capture_images(interval=1)
        
        elif choice == '2':
            try:
                interval = float(input("请输入保存间隔(秒): "))
                max_images = input("最大图像数量 (回车=无限制): ").strip()
                max_images = int(max_images) if max_images else None
                capture.capture_images(interval=interval, max_images=max_images)
            except ValueError:
                print("✗ 输入无效")
        
        elif choice == '3':
            try:
                interval = float(input("请输入保存间隔(秒，默认1): ") or "1")
                max_keep = int(input("请输入最多保留的图像数量(默认10): ") or "10")
                capture.capture_images_with_limit(interval=interval, max_keep=max_keep)
            except ValueError:
                print("✗ 输入无效")
        
        elif choice == '4':
            capture.capture_single_image()
        
        elif choice == '5':
            capture.clear_images_folder()
        
        elif choice == '6':
            print("退出程序")
            break
        
        else:
            print("✗ 无效选择")


if __name__ == "__main__":
    main()

