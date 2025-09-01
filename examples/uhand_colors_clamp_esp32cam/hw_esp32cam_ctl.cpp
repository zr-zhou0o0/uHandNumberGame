/* 
 * 2024/02/21 hiwonder CuZn
 * Arduino与ESP32Cam的IIC通讯类
 */
#include "hw_esp32cam_ctl.h"

// 初始化IIC通信函数
void HW_ESP32Cam::begin(void)
{
  Wire.begin();
}

//向esp32Cam发送多个字节
// addr：esp32Cam设备地址（0x52）
// reg：向esp32Cam写入的目标内存地址
// *val:需要发送的数据地址
// len：需要发送的字长
static bool wireWriteDataArray(uint8_t addr, uint8_t reg,uint8_t *val,unsigned int len)
{
    unsigned int i;

    Wire.beginTransmission(addr);
    Wire.write(reg);
    for(i = 0; i < len; i++) 
    {
        Wire.write(val[i]);
    }
    if( Wire.endTransmission() != 0 ) 
    {
        return false;
    }
    return true;
}

// 向esp32Cam发送1个字节 
static bool WireWriteByte(uint8_t val)
{
    Wire.beginTransmission(ESP32CAM_ADDR);
    Wire.write(val);
    if( Wire.endTransmission() != 0 ) {
        return false;
    }
    return true;
}


// 从esp32Cam读取多字节的数据
//  reg：esp32Cam中需要读取的数据地址
// *val：arduino主设备中用于存放数据的地址
// len：需要读取的字长
static int WireReadDataArray(uint8_t reg, uint8_t *val, unsigned int len)
{
    unsigned char i = 0;
    
    /* Indicate which register we want to read from */
    if (!WireWriteByte(reg)) {
        return -1;
    }
    
    /* Read block data */
    Wire.requestFrom(ESP32CAM_ADDR, len);
    while (Wire.available()) {
        if (i >= len) {
            return -1;
        }
        val[i] = Wire.read();
        i++;
    }   
    return i;
}


//读取ESP32Cam检测人脸
bool HW_ESP32Cam::faceDetect(void)
{
  uint8_t face_info[4];
  Serial.print("face ");
  int num = WireReadDataArray(0x01,face_info,4);
  if((num == 4) && (face_info[2] > 0)) //接收识别到的人脸的x,y,w,h值
  {
      Serial.println(" 1");
      return true;
  }
  Serial.println(" 0");
  return false;
}


//读取ESP32Cam识别颜色，返回颜色代号
int HW_ESP32Cam::colorDetect(void)
{
  uint8_t color_info[3][4];
  int num = WireReadDataArray(0x00,color_info[0],4);
  if((num == 4) && (color_info[0][2] > 0)) //接收识别到的颜色的x,y,w,h值
  {
      return 1;  //红色
  }
  num = WireReadDataArray(0x01,color_info[1],4);
  if(num == 4)
  {
    if(color_info[1][2] > 0) //若w值大于0，则识别到颜色1
    {
      return 2;  //绿色
    }
  }
  num = WireReadDataArray(0x02,color_info[2],4);
  if(num == 4)
  {
    if(color_info[2][2] > 0) //若w值大于0，则识别到颜色2
    {
      return 3;  //蓝色
    }
  }
  return 0;
}

//读取ESP32Cam识别颜色位置，读取成功返回true和位置数据
bool HW_ESP32Cam::color_position(uint8_t *color_info)
{
  int num = WireReadDataArray(0x01,color_info,4);
  if((num == 4) && (color_info[2] > 0)) //接收识别到的颜色的x,y,w,h值
  {
    return true;
  }
  return false;
}

