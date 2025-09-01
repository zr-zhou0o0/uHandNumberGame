/* 
 * 2024/02/21 hiwonder CuZn
 * 人脸识别打招呼例程
 * 人脸识别打招呼例程，用IIC连接ESP32Cam，检测到人脸，机械手掌摇动打招呼
 * 注意：每个不同的功能，ESP32Cam也要下载对应功能的ESP32Cam程序
 */
#include <FastLED.h> //导入LED库
#include <Servo.h> //导入舵机库
#include "hw_esp32cam_ctl.h" //导入ESP32Cam通讯库
#include "tone.h" //导入音调库

const static uint16_t DOC5[] = { TONE_C5 };
const static uint16_t DOC6[] = { TONE_C6 };

/* 引脚定义 */
const static uint8_t servoPins[6] = { 7, 6, 5, 4, 3, 2 };
const static uint8_t buzzerPin = 11;
const static uint8_t rgbPin = 13;

//RGB灯控制对象
static CRGB rgbs[1];
//ESP32Cam通讯对象
HW_ESP32Cam hw_cam;
//舵机控制对象
Servo servos[6];

// 舵机角度相关变量
static uint8_t extended_func_angles[6] = { 180, 180, 180, 180, 180, 90 }; /* 二次开发例程使用的角度数值 */
static float servo_angles[6] = { 180, 180, 180, 180, 180, 90 };  /* 舵机实际控制的角度数值 */

// 蜂鸣器相关变量
static uint16_t tune_num = 0;
static uint32_t tune_beat = 10;
static uint16_t *tune;

static void servo_control(void); /* 舵机控制 */
void play_tune(uint16_t *p, uint32_t beat, uint16_t len); /* 蜂鸣器控制接口 */
void tune_task(void); /* 蜂鸣器控制任务 */
void espcam_task(void);  /* esp32cam通讯任务 */

void setup() {
  Serial.begin(115200);
  // 设置串行端口读取数据的超时时间
  Serial.setTimeout(500);

  // 绑定舵机IO口
  for (int i = 0; i < 6; ++i) {
    servos[i].attach(servoPins[i],500,2500);
  }

  hw_cam.begin(); //初始化与ESP32Cam通讯接口

  //RGB灯初始化并控制
  FastLED.addLeds<WS2812, rgbPin, GRB>(rgbs, 1);
  rgbs[0] = CRGB(0, 255, 0);
  FastLED.show();

  //蜂鸣器初始化并鸣响一声
  pinMode(buzzerPin, OUTPUT);
  tone(buzzerPin, 1000);
  delay(100);
  noTone(buzzerPin);
  
  delay(500);
  Serial.println("start");
}

void loop() {
  // esp32cam通讯任务
  espcam_task();
  // 蜂鸣器鸣响任务
  tune_task();
  // 舵机控制
  servo_control();
}

// esp32cam通讯任务
void espcam_task(void)
{
  static uint32_t last_tick = 0;
  static int posi = 90;
  static uint8_t step = 0;
  static uint8_t delay_count = 0;
  int res = 0;
  
  if (millis() - last_tick < 50) {
    return;
  }
  last_tick = millis();

  res = hw_cam.faceDetect();

  switch(step)
  {
    case 0:
      if(res != 0) 
      {
        rgbs[0].r = 250;
        rgbs[0].g = 0;
        rgbs[0].b = 0;
        FastLED.show();
        play_tune(DOC6, 300u, 1u);
        Serial.println("find face");
        step++;
      }else{
        rgbs[0].r = 0;
        rgbs[0].g = 100;
        rgbs[0].b = 100;
        FastLED.show();
      }
      break;
    case 1:  //等待
      delay_count++;
      if(delay_count > 5)
      {
        step++;
        delay_count = 0;
      }
      break;
    case 2://闭合
      control_hand(0);
      delay_count = 0;
      step++;
      break;
    case 3: //等待
      delay_count++;
      if(delay_count > 10)
      {
        step++;
      }
      break;
    case 4://张开
      control_hand(180);
      delay_count = 0;
      step++;
      break;
    case 5: //等待
      delay_count++;
      if(delay_count > 15)
      {
        step++;
      }
      break;
    case 6://闭合
      control_hand(0);
      delay_count = 0;
      step++;
      break;
    case 7: //等待
      delay_count++;
      if(delay_count > 15)
      {
        step++;
      }
      break;
    case 8://张开
      control_hand(180);
      delay_count = 0;
      step++;
      break;
    case 9: //等待
      delay_count++;
      if(delay_count > 15)
      {
        step = 0;
      }
      break;
    default:
      step = 0;
      break;
  }
}

void control_hand(uint8_t angle)
{
  angle = angle > 180 ? 180 : angle;
  for(int i = 0 ; i < 5 ; i++)
  {
    extended_func_angles[i] = angle;
  }
}

//舵机控制任务
void servo_control(void) {
  static uint32_t last_tick = 0;
  if (millis() - last_tick < 40) {
    return;
  }
  last_tick = millis();
  for (int i = 0; i < 6; ++i) {
    servo_angles[i] = servo_angles[i] * 0.85 + extended_func_angles[i] * 0.15;
    servos[i].write(i == 0 || i == 5 ? 180 - servo_angles[i] : servo_angles[i]);
  }
}

// 蜂鸣器任务
void tune_task(void) {
  static uint32_t l_tune_beat = 0;
  static uint32_t last_tick = 0;
  // 若未到定时时间 且 响的次数跟上一次的一样
  if (millis() - last_tick < l_tune_beat && tune_beat == l_tune_beat) {
    return;
  }
  l_tune_beat = tune_beat;
  last_tick = millis();
  if (tune_num > 0) {
    tune_num -= 1;
    tone(buzzerPin, *tune++);
  } else {
    noTone(buzzerPin);
    tune_beat = 10;
    l_tune_beat = 10;
  }
}

// 蜂鸣器鸣响函数
void play_tune(uint16_t *p, uint32_t beat, uint16_t len) {
  tune = p;
  tune_beat = beat;
  tune_num = len;
}
