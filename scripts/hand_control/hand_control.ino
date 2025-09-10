#include <Servo.h> 
#include <FastLED.h> 
#include "uhand_servo.h" 
#include "tone.h" 


//引脚定义 
const static uint8_t servoPins[6] = { 7, 6, 5, 4, 3, 2 };//舵机引脚定义
const static uint8_t buzzerPin = 11;
const static uint8_t rgbPin = 13;


// 蜂鸣器音调组合
const static uint16_t DOC5[] = { TONE_C5 }; 
const static uint16_t DOC6[] = { TONE_C6 };
const static uint16_t MI_RE_MI_RE_MI[5] = { TONE_C7, TONE_C6, TONE_C7, TONE_C6, TONE_C7}; // 胜利提示音
const static uint16_t MI_RE_DO[3] = { TONE_E5, TONE_D5, TONE_C5 }; // 失败提示音
const static uint16_t START[3] = { TONE_E5,TONE_E5,TONE_E5 }; //开始提示音
const static uint16_t ROUND[3] = { TONE_A5,TONE_A5,TONE_A5 }; //回合提示音


// 定义对象和变量
HW_ACTION_CTL action_ctl; //动作组控制对象
Servo servos[6]; //舵机控制对象
const uint8_t limt_angles[6][2] = {{0,82},{0,180},{0,180},{25,180},{0,180},{0,180}}; //各个关节角度的限制
static float servo_angles[6] = { 0,0,0,0,0, 90 };  // 舵机实际控制的角度数值 
static CRGB rgbs[1];
static uint16_t *tune = NULL; 
static uint32_t tune_beat = 10;
static uint16_t tune_num = 0;
static uint16_t tune_index = 0;
static uint32_t last_tune_tick = 0;


// 函数声明
static void servo_control(void); // 舵机控制 
void process_serial_command(void); // 处理串口命令
void play_tune(uint16_t *p, uint32_t beat, uint16_t len); // 播放音调函数
void tune_task(void); // 蜂鸣器任务


// 初始化函数
void setup() {

  Serial.begin(115200);
  Serial.setTimeout(500);
  
  // 绑定舵机IO口
  for (int i = 0; i < 6; ++i) {
    servos[i].attach(servoPins[i]);
  }

  // 初始化蜂鸣器引脚
  pinMode(buzzerPin, OUTPUT);

  // 初始化RGB控制对象
  FastLED.addLeds<WS2812, rgbPin, GRB>(rgbs, 1);
  rgbs[0] = CRGB(0, 255, 0); // 初始化为绿色
  FastLED.show();

  delay(2000);
  Serial.println("System ready. Send commands: 0 ~ 10");
}


// 循环执行命令
void loop() {
  // 处理串口命令
  process_serial_command();
  
  // Action group executing tasks
  action_ctl.action_task();
  
  //Servo control
  servo_control();

  // 蜂鸣器任务
  tune_task();
}


// 处理串口命令
/*
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
*/
// 手势 1~9 对应 ActionGroup 1~9
// 手势 0 对应 ActionGroup 10
// 手势胜利对应 ActionGroup 11
// 手势失败对应 ActionGroup 12
// 检验手势对应 ActionGroup 13 无需使用

// 处理串口命令
void process_serial_command(void) {
  if (Serial.available() > 0) {
    int command = Serial.parseInt(); // 读取整数命令
    
    while (Serial.available() > 0) {
      Serial.read();
    }
    
    if (command >= 0 && command <= 11) {
      switch(command) {
        case 0: // 手势0，手势胜利
          action_ctl.action_set(11); 
          play_tune(MI_RE_MI_RE_MI, 200, 5); // 胜利提示音
          rgbs[0] = CRGB(255, 255, 0); // 黄色
          Serial.println("Executing victory gesture (Action Group 10)");
          break;
          
        case 1: // 手势1
        case 2: // 手势2
        case 3: // 手势3
        case 4: // 手势4
        case 5: // 手势5
        case 6: // 手势6
        case 7: // 手势7
        case 8: // 手势8
        case 9: // 手势9
          action_ctl.action_set(command); // 执行对应的动作组(1-9)
          play_tune(ROUND, 200, 3); // 回合提示音
          rgbs[0] = CRGB(0, 0, 255); // 蓝色
          Serial.print("Executing gesture ");
          Serial.print(command);
          Serial.print(" (Action Group ");
          Serial.print(command);
          Serial.println(")");
          break;
          
        case 10: // 手势失败
          action_ctl.action_set(12); // 执行动作组12
          play_tune(MI_RE_DO, 200, 3); // 失败提示音
          rgbs[0] = CRGB(255, 0, 0); // 红色
          Serial.println("Executing defeat gesture (Action Group 12)");
          break;
          
        case 11: // 手势1，开始
          action_ctl.action_set(1); // 执行动作组1
          play_tune(START, 200, 3); // 开始提示音
          rgbs[0] = CRGB(0, 255, 0); // 绿色
          Serial.println("Executing start gesture (Action Group 1)");
          break;
      }
      FastLED.show(); // 更新RGB灯颜色
    } else if (command == -1) {
      // 不执行新动作，打印成功信息
      Serial.println("The action group is running successfully!");
    } else {
      // 无效命令
      Serial.println("Invalid command. Please send values between -1 and 11");
      play_tune(DOC6, 100, 1); // 播放错误提示音
    }
  }
}


// 播放音调函数
void play_tune(uint16_t *p, uint32_t beat, uint16_t len) {
  tune = p;
  tune_beat = beat;
  tune_num = len;
  tune_index = 0;
  last_tune_tick = millis();
}


// 蜂鸣器任务
void tune_task(void) {
  // 如果没有音调要播放，直接返回
  if (tune_num == 0) {
    return;
  }
  
  // 检查是否到了播放下一个音调的时间
  if (millis() - last_tune_tick < tune_beat) {
    return;
  }
  
  last_tune_tick = millis();
  
  // 播放当前音调
  tone(buzzerPin, tune[tune_index]);
  
  // 移动到下一个音调
  tune_index++;
  
  // 如果所有音调都已播放完毕，停止蜂鸣器并重置状态
  if (tune_index >= tune_num) {
    noTone(buzzerPin);
    tune_num = 0;
    tune_index = 0;
    
    // 恢复RGB灯为绿色
    rgbs[0] = CRGB(0, 255, 0);
    FastLED.show();
  }
}


// 舵机控制任务（不需修改）
void servo_control(void) {
  static uint32_t last_tick = 0;
  if (millis() - last_tick < 20) {
    return;
  }
  last_tick = millis();

  for (int i = 0; i < 6; ++i) {
    if(servo_angles[i] > action_ctl.extended_func_angles[i])
    {
      servo_angles[i] = servo_angles[i] * 0.9 + action_ctl.extended_func_angles[i] * 0.1;
      if(servo_angles[i] < action_ctl.extended_func_angles[i])
        servo_angles[i] = action_ctl.extended_func_angles[i];
    }else if(servo_angles[i] < action_ctl.extended_func_angles[i])
    {
      servo_angles[i] = servo_angles[i] * 0.9 + (action_ctl.extended_func_angles[i] * 0.1 + 1);
      if(servo_angles[i] > action_ctl.extended_func_angles[i])
        servo_angles[i] = action_ctl.extended_func_angles[i];
    }

    servo_angles[i] = servo_angles[i] < limt_angles[i][0] ? limt_angles[i][0] : servo_angles[i];
    servo_angles[i] = servo_angles[i] > limt_angles[i][1] ? limt_angles[i][1] : servo_angles[i];
    servos[i].write(i == 0 || i == 5 ? 180 - servo_angles[i] : servo_angles[i]);
  }
}