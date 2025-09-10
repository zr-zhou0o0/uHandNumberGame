# pip install pyserial
# pip install serial
# 如果报错 Serial port error: could not open port 'COM19': PermissionError(13, '拒绝访问。', None, 5)
# 原因是arduino的串口监视器占用了port,导致Py脚本串口发送时无法打开port,关闭所有的arduino的串口监视器即可。

import serial
import time
import random

# 配置串口参数
SERIAL_PORT = 'COM19'  # 请根据实际情况修改串口号
BAUD_RATE = 115200

def main():
    try:
        # 打开串口
        ser = serial.Serial(SERIAL_PORT, BAUD_RATE, timeout=1)
        print(f"Connected to {SERIAL_PORT} at {BAUD_RATE} baud")
        time.sleep(2)  # 等待Arduino初始化
        
        # 有效数字列表
        valid_numbers = [1, 2, 3]
        
        while True:
            # 随机选择一个有效数字
            valid_num = random.choice(valid_numbers)
            
            # 发送有效数字
            ser.write(f"{valid_num}\n".encode())
            print(f"Sent: {valid_num}")
            
            # 等待一小段时间
            # time.sleep(0.1)
            
            # # 发送-1
            # ser.write("-1\n".encode())
            # print("Sent: -1")
            
            # 等待2秒
            time.sleep(5)
            
    except serial.SerialException as e:
        print(f"Serial port error: {e}")
    except Exception as e:
        print(f"Error: {e}")
    except KeyboardInterrupt:
        print("\nProgram terminated by user")
    finally:
        if 'ser' in locals() and ser.is_open:
            ser.close()
            print("Serial connection closed")

if __name__ == "__main__":
    main()