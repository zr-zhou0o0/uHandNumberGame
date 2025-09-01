#include <FastLED.h>
#include <Servo.h>


// 定义音符频率（单位：Hz），这里定义了两个音符（中音Do和高音Do）
const static uint16_t DOC5[] = { 523 };
const static uint16_t DOC6[] = { 1047u };

const static uint8_t servoPins[6] = { 7, 6, 5, 4, 3, 2 }; // 6个舵机连接的引脚
const static uint8_t buzzerPin = 11;// 蜂鸣器引脚
const static uint8_t rgbPin = 13; // RGB灯引脚
// 定义枚举类型，表示机械臂的四种控制模式
typedef enum {
  MODE_KNOB,          // 旋钮控制模式
  MODE_APP,           // 手机APP控制模式（未实现）
  MODE_ACTIONGROUP,   // 动作组模式（未实现）
  MODE_EXTENDED,      // 扩展模式（未实现）
} UhandMode;

static CRGB rgbs[1];  // 定义一个RGB灯对象（只有一个灯）

static UhandMode g_mode = MODE_KNOB;                          /* mode, 0 -> panel, 1 -> app */
static uint8_t knob_angles[6] = { 90, 90, 90, 90, 90, 90 };   /* 旋钮产生的角度数值 */
static float servo_angles[6] = { 90, 90, 90, 90, 90, 90 };  /* 舵机实际控制的角度数值 */

static uint16_t tune_num = 0;
static uint32_t tune_beat = 10;
static uint16_t *tune;

Servo servos[6]; // 创建6个舵机对象

static void knob_update(void);   /* 旋钮读取更新 */
static void servo_control(void); /* 舵机控制 */
void tune_task(void);// 蜂鸣器播放任务



// 初始化函数
void setup() {
  Serial.begin(115200);
  // 设置串行端口读取数据的超时时间
  Serial.setTimeout(500);
  pinMode(buzzerPin, OUTPUT);
  // 绑定舵机IO口
  for (int i = 0; i < 6; ++i) {
    servos[i].attach(servoPins[i],500,2500);
  }

  // 初始化RGB灯
  FastLED.addLeds<WS2812, rgbPin, GRB>(rgbs, 1);
  rgbs[0] = CRGB(0, 255, 0);
  FastLED.show();
  tone(buzzerPin, 1000);
  delay(100);
  noTone(buzzerPin);
}



void loop() {
  // 蜂鸣器鸣响任务
  tune_task();
  // 旋钮读取更新
  knob_update();
  // 舵机控制
  servo_control();
}



// 旋钮更新函数：读取6个模拟输入引脚的值并映射为角度
void knob_update(void) { /* 旋钮读取更新 */
  static uint32_t last_tick = 0;
  static float values[6];
  float angle = 0;
  // 每10ms执行一次
  if (millis() - last_tick < 10) {  // millis: 代表从Arduino板上电或程序开始运行以来，所经过的毫秒数
    return;
  }
  last_tick = millis();
  // 读取模拟引脚并应用低通滤波（平滑处理）
  values[0] = values[0] * 0.7 + analogRead(A0) * 0.3;
  values[1] = values[1] * 0.7 + analogRead(A1) * 0.3;
  values[2] = values[2] * 0.7 + analogRead(A2) * 0.3;
  values[3] = values[3] * 0.7 + analogRead(A3) * 0.3;
  values[4] = values[4] * 0.7 + analogRead(A4) * 0.3;
  values[5] = values[5] * 0.7 + analogRead(A5) * 0.3;
  for (int i = 0; i < 6; ++i) {
    angle = map(values[i], 0, 1023, 0, 180);  // 将模拟值映射到0-180度范围
    angle = angle < 0 ? 0 : (angle > 180 ? 180 : angle);  // 限制角度在有效范围内
    if (fabs(angle - knob_angles[i]) > 5 && g_mode != MODE_KNOB) { /* 当发现旋钮被旋转超过阈值则恢复旋钮控制模式(可能处于手机app控制模式) */
      g_mode = MODE_KNOB;
      rgbs[0].r = 0;
      rgbs[0].g = 255;
      rgbs[0].b = 0;
      FastLED.show();
    }
    // 如果是旋钮模式，更新目标角度
    if (g_mode == MODE_KNOB) {
      knob_angles[i] = angle;
      if (i == 5) {
      }
    }
  }
}



// 舵机控制函数：平滑移动舵机并发送角度数据到串口
// 数据格式：{1 ,18 ,177 ,179 ,0 ,0 ,108},
void servo_control(void) {
  static uint32_t last_tick = 0;
  if (millis() - last_tick < 25) { // 25
    return;
  }
  last_tick = millis();
  Serial.print("{1");
  for (int i = 0; i < 6; ++i) {
    // 使用加权平均实现平滑移动（85%当前角度 + 15%目标角度）
    servo_angles[i] = servo_angles[i] * 0.85 + knob_angles[i] * 0.15; 
    // 控制舵机（注意：第0和第5号舵机方向反转）
    servos[i].write(i == 0 || i == 5 ? 180 - servo_angles[i] : servo_angles[i]);
    // 通过串口输出角度数据
    Serial.print(" ,");
    Serial.print((int)servo_angles[i]);
  }
  Serial.println("},");
}



// 蜂鸣器任务函数：按节奏播放音符
void tune_task(void) {
  static uint32_t l_tune_beat = 0;  // 记录当前音符的持续时间（剩余应该持续的时间）
  static uint32_t last_tick = 0;  // 记录上次播放时间
  // 若未到定时时间 且 响的次数跟上一次的一样
  if (millis() - last_tick < l_tune_beat && tune_beat == l_tune_beat) {
    return;
  }
  l_tune_beat = tune_beat;
  last_tick = millis();
  if (tune_num > 0) {
    tune_num -= 1;
    tone(buzzerPin, *tune++); // 播放当前音符并移动到下一个
  } else {
    noTone(buzzerPin);
    tune_beat = 10;
    l_tune_beat = 10;
  }
}
