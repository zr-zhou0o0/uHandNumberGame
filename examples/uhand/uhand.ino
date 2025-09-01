#include <FastLED.h> //导入库
#include <EEPROM.h>
#include <Servo.h>
#include "tone.h"

#define EEPROM_START_FLAG "HIWONDER"
#define EEPROM_ACTION_NUM_ADDR 16u   /* 存放动作组内的动作个数 */
#define EEPROM_ACTION_START_ADDR 32u /* 动作组的起始地址 */
#define EEPROM_ACTION_UNIT_LENGTH 6u /* 动作组的单个动作字节长度 */

const static uint16_t DOC5[] = { TONE_C5 };
const static uint16_t DOC6[] = { TONE_C6 };
const static uint16_t DO_RE_MI[3] = { TONE_C5, TONE_D5, TONE_E5 };
const static uint16_t MI_RE_DO[3] = { TONE_E5, TONE_D5, TONE_C5 };
const static uint16_t MI_RE_MI_RE[4] = { TONE_C7, TONE_C6, TONE_C7, TONE_C6 };

const static uint8_t keyPins[2] = { 8, 9 };
const static uint8_t servoPins[6] = { 7, 6, 5, 4, 3, 2 };
const static uint8_t buzzerPin = 11;
const static uint8_t rgbPin = 13;
typedef enum {
  MODE_KNOB,
  MODE_APP,
  MODE_ACTIONGROUP,
  MODE_EXTENDED,
} UhandMode;

static CRGB rgbs[1];
static uint8_t eeprom_read_buf[16];
static bool learning = false;

static UhandMode g_mode = MODE_KNOB;                          /* mode, 0 -> panel, 1 -> app */
static UhandMode g_mode_old = MODE_KNOB;

static uint8_t knob_angles[6] = { 90, 90, 90, 90, 90, 90 };   /* 旋钮产生的角度数值 */
static uint8_t app_angles[6] = { 90, 90, 90, 90, 90, 90 };    /* app 发送过来的角度数值 */
static uint8_t action_angles[6] = { 90, 90, 90, 90, 90, 90 }; /* 动作组的角度数值 */
static uint8_t extended_func_angles[6] = { 90, 90, 90, 90, 90, 90 }; /* 二次开发例程使用的角度数值 */

static float servo_angles[6] = { 90, 90, 90, 90, 90, 90 };  /* 舵机实际控制的角度数值 */
static uint8_t action_group[80][6];

static uint16_t action_index;
static uint8_t action_group_running_step = 0;

static uint16_t tune_num = 0;
static uint32_t tune_beat = 10;
static uint16_t *tune;

Servo servos[6];

static void knob_update(void);   /* 旋钮读取更新 */
static void key_scan(void);      /* 按键扫描 */
static void servo_control(void); /* 舵机控制 */
void play_tune(uint16_t *p, uint32_t beat, uint16_t len);
void tune_task(void);
void action_group_task(void);
void recv_handler(void);
void servos_middle(void); //中位任务

void setup() {
  // put your setup code here, to run once:
  Serial.begin(9600);
  // 设置串行端口读取数据的超时时间
  Serial.setTimeout(500);
  pinMode(keyPins[0], INPUT_PULLUP);
  pinMode(keyPins[1], INPUT_PULLUP);
  pinMode(buzzerPin, OUTPUT);
  // 绑定舵机IO口
  for (int i = 0; i < 6; ++i) {
    servos[i].attach(servoPins[i],500,2500);
  }

  // 显示白色灯
  FastLED.addLeds<WS2812, rgbPin, GRB>(rgbs, 1);
  rgbs[0] = CRGB(100 , 100 , 100);
  FastLED.show();
  // 蜂鸣器鸣响一声
  tone(buzzerPin, 1000);
  delay(100);
  noTone(buzzerPin);

  //中位任务
  servos_middle();
  // 显示绿色灯
  FastLED.clear();
  rgbs[0].g = 250; 
  FastLED.show();
  delay(2000);

  Serial.println("Start...");
}

void loop() {
  // 蜂鸣器鸣响任务
  tune_task();
  // 按键扫描及其动作实现
  key_scan();
  // 旋钮读取更新
  knob_update();
  // 舵机控制
  servo_control();
  // 动作组任务
  action_group_task();
  // 接收中断
  recv_handler();
}

void servos_middle(void)
{
  // Set the servo to the center angle
  for(int i = 0 ; i < 6 ; i++)
  {
    servos[i].write(90);
  }
  uint16_t count = 0;
  /* Loop detection, if two buttons are pressed simultaneously for 1 second, 
  exit the middle position task */
  while(true)
  {
    if(!digitalRead(keyPins[0]))
    {
      if(!digitalRead(keyPins[1]))
      {
        delay(100);
        count++;
        if(count > 10)
          return;
      }else{
        count = 0;
      }
    }else{
      count = 0;
    }
  }
}

void recv_handler(void) {
  while (Serial.available() > 0) {
    String cmd = Serial.readStringUntil('$');
    Serial.println(cmd);
    switch (cmd[0]) {
      case 'A':
        app_angles[0] = atoi(cmd.c_str() + 1);
        g_mode = MODE_APP;
        break;
      case 'B':
        app_angles[1] = atoi(cmd.c_str() + 1);
        g_mode = MODE_APP;
        break;
      case 'C':
        app_angles[2] = atoi(cmd.c_str() + 1);
        // Serial.println(app_angles[2]);
        g_mode = MODE_APP;
        break;
      case 'D':
        app_angles[3] = atoi(cmd.c_str() + 1);
        g_mode = MODE_APP;
        break;
      case 'E':
        app_angles[4] = atoi(cmd.c_str() + 1);
        g_mode = MODE_APP;
        break;
      case 'F':
        app_angles[5] = atoi(cmd.c_str() + 1);
        g_mode = MODE_APP;
        break;
      case 'G':
        g_mode = MODE_APP;
        rgbs[0].r = atoi(cmd.c_str() + 1);
        break;
      case 'H':
        g_mode = MODE_APP;
        rgbs[0].g = atoi(cmd.c_str() + 1);
        break;
      case 'I':
        g_mode = MODE_APP;
        rgbs[0].b = atoi(cmd.c_str() + 1);
        break;
      case 'J':
        g_mode = MODE_APP;
        FastLED.show();
        break;
      case 'Z':
        {
          g_mode = MODE_APP;
          if (cmd[1] == '1') {
            play_tune(DOC6, 10000u, 1u);
          }
          if (cmd[1] == '0') {
            play_tune(DOC6, 1u, 0u);
          }
          break;
        }
      default:
        break;
    }
  }
  if ((g_mode_old != MODE_APP)&&(g_mode == MODE_APP)) {
    rgbs[0].r = 0;
    rgbs[0].g = 0;
    rgbs[0].b = 255;
    FastLED.show();
  }
  g_mode_old = g_mode;
}
void knob_update(void) { /* Read knob Function*/
  static uint32_t last_tick = 0;
  static float values[6];
  float angle = 0;
  if (millis() - last_tick < 10) {
    return;
  }
  last_tick = millis();
  values[0] = values[0] * 0.7 + analogRead(A0) * 0.3;
  values[1] = values[1] * 0.7 + analogRead(A1) * 0.3;
  values[2] = values[2] * 0.7 + analogRead(A2) * 0.3;
  values[3] = values[3] * 0.7 + analogRead(A3) * 0.3;
  values[4] = values[4] * 0.7 + analogRead(A4) * 0.3;
  values[5] = values[5] * 0.7 + analogRead(A5) * 0.3;
  for (int i = 0; i < 6; ++i) {
    angle = map(values[i], 0, 1023, 0, 180);
    angle = angle < 0 ? 0 : (angle > 180 ? 180 : angle);
    if (fabs(angle - knob_angles[i]) > 5 && g_mode != MODE_KNOB) { 
      /* When it is found that the knob has been rotated beyond the threshold,
      the knob control mode will be restored 
      (it may currently be in the mobile app control mode) */
      g_mode = MODE_KNOB;
      action_group_running_step = 0;
      rgbs[0].r = 0;
      rgbs[0].g = 255;
      rgbs[0].b = 0;
      FastLED.show();
    }
    if (g_mode == MODE_KNOB) {
      knob_angles[i] = angle;
      if (i == 5) {
        // rgbs[0] = CHSV(map(values[i], 0, 1023, 0, 225), 255, 255);
        // FastLED.show();
      }
    }
  }
}

void servo_control(void) {
  static uint32_t last_tick = 0;
  if (millis() - last_tick < 25) {
    return;
  }
  last_tick = millis();
  for (int i = 0; i < 6; ++i) {
    if (g_mode == MODE_APP) {
      servo_angles[i] = servo_angles[i] * 0.85 + app_angles[i] * 0.15;
    } else if (g_mode == MODE_KNOB) {
      servo_angles[i] = servo_angles[i] * 0.85 + knob_angles[i] * 0.15;
    } else if (g_mode == MODE_EXTENDED) {
      servo_angles[i] = servo_angles[i] * 0.85 + extended_func_angles[i] * 0.15;
    } else{
      servo_angles[i] = servo_angles[i] * 0.85 + action_angles[i] * 0.15;
    }
    servos[i].write(i == 0 || i == 5 ? 180 - servo_angles[i] : servo_angles[i]);
  }
}

void tune_task(void) {
  static uint32_t l_tune_beat = 0;
  static uint32_t last_tick = 0;
  /* If the scheduled time is not reached and 
  the number of beeps is the same as the previous one */
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

void play_tune(uint16_t *p, uint32_t beat, uint16_t len) {
  tune = p;
  tune_beat = beat;
  tune_num = len;
}

void action_group_task(void) {
  static uint32_t last_tick = 0;
  static uint32_t tick_wait = 50;
  static uint16_t action_num = 0;
  static uint16_t action_index = 0;

  if (millis() - last_tick < tick_wait) {
    return;
  }
  last_tick = millis();
  switch (action_group_running_step) {
    case 0:
      break;
    case 1:
    case 2:
      {
        g_mode = MODE_ACTIONGROUP;
        action_index = 0;
        action_num = 0;
        for (int i = 0; i < 16; ++i) {
          eeprom_read_buf[i] = EEPROM.read(i);
        }
        if (strcmp(eeprom_read_buf, EEPROM_START_FLAG) == 0) {
          action_num = EEPROM.read(EEPROM_ACTION_NUM_ADDR);
          if (action_num > 0) {
            tick_wait = 1000;
            action_index = 0;
            if (action_group_running_step == 1) {
              action_group_running_step = 3;
            }
            if (action_group_running_step == 2) {
              action_group_running_step = 4;
            }
          } else {
            action_group_running_step = 0;
          }
        } else {
          action_group_running_step = 0;
        }
        break;
      }
    case 3:
    case 4:
    case 5:
      {
        memset(eeprom_read_buf, 0, 16);
        for (int i = 0; i < EEPROM_ACTION_UNIT_LENGTH; ++i) {
          eeprom_read_buf[i] = EEPROM.read(EEPROM_ACTION_START_ADDR + EEPROM_ACTION_UNIT_LENGTH * action_index + i);
        }
        for (int i = 0; i < 6; ++i) {
          action_angles[i] = eeprom_read_buf[i];
        }
        action_index += 1;
        if (action_index >= action_num) {
          if (action_group_running_step == 4) {
            action_group_running_step = 4;
            action_index = 0;
          } else {
            action_group_running_step = 6;
          }
        }
        break;
      }
    case 6:
      action_group_running_step = 0;
      tick_wait = 50;
      rgbs[0].r = 0;
      rgbs[0].g = 255;
      rgbs[0].b = 0;
      FastLED.show();
      break;
    default:
      break;
  }
}

void key_scan(void) { /* 按键扫描 */
  static uint16_t last_io_data[2];
  static bool keys_state[2];
  static uint8_t key_step[2];
  static uint32_t pressed_tick[2];
  static uint32_t last_tick = 0;
  if (millis() - last_tick < 20) {
    return;
  }
  last_tick = millis();
  for (int i = 0; i < 2; ++i) {
    uint16_t io = digitalRead(keyPins[i]);
    if (last_io_data[i] == io) {
      bool state = io == LOW ? true : false;
      switch (key_step[i]) {
        case 0:
          { /* Release in normal state */
            if (state) {
              key_step[i] = 1;
              pressed_tick[i] = last_tick;
            }
            break;
          }
        case 1:
          {
            if (!state) {
              key_step[i] = 0;
              if (i == 0)  //K1
              {
                if (learning) { /* Add new action */
                  memcpy(&action_group[action_index++], knob_angles, 6);
                  play_tune(DOC5, 100, 1);
                } else { /* Stop */
                  if (action_group_running_step != 0) {
                    action_group_running_step = 0;
                    play_tune(DOC6, 800, 1);
                    rgbs[0].r = 0;
                    rgbs[0].g = 255;
                    rgbs[0].b = 0;
                    FastLED.show();
                  }
                }
              }
              if (i == 1)  //K2
              {
                if (!learning) { /* Single run action group */
                  if (action_group_running_step == 0) {
                    action_group_running_step = 1;
                    play_tune(DOC6, 100u, 1u);
                    rgbs[0].r = 255;
                    rgbs[0].g = 200;
                    rgbs[0].b = 0;
                    FastLED.show();
                  }
                }
              }
            } else {
              if (last_tick - pressed_tick[i] > 1000)  //若是长按
              {
                key_step[i] = 2;
                if (i == 0) {
                  if (learning) {                            /* Exit action editing mode without saving */
                    for (int j = 0; j < action_index; ++j) { /* Save action group to EEPROM */
                      for (int k = 0; k < 6; ++k) {
                        EEPROM.write(EEPROM_ACTION_START_ADDR + EEPROM_ACTION_UNIT_LENGTH * j + k, action_group[j][k]);
                      }
                    }
                    EEPROM.write(EEPROM_ACTION_NUM_ADDR, action_index);       /* Save the number of actions included in the action group */
                    for (int j = 0; j < strlen(EEPROM_START_FLAG) + 1; ++j) { /* Storage space initialized flag */
                      EEPROM.write(0 + j, EEPROM_START_FLAG[j]);
                    }
                    learning = false;
                    play_tune(MI_RE_DO, 150, 3);
                    rgbs[0].r = 0;
                    rgbs[0].g = 255;
                    rgbs[0].b = 0;
                    FastLED.show();
                  } else { /* Enter action editing mode */
                    if (action_group_running_step == 0) {
                      learning = true;
                      action_index = 0;
                      play_tune(DO_RE_MI, 150, 3);
                      rgbs[0].r = 255;
                      rgbs[0].g = 0;
                      rgbs[0].b = 0;
                      FastLED.show();
                    }
                  }
                }
                if (i == 1) {
                  if (learning) { /* Exit action editing mode and save */
                    learning = false;
                    play_tune(MI_RE_DO, 150, 3);
                    rgbs[0].r = 0;
                    rgbs[0].g = 255;
                    rgbs[0].b = 0;
                    FastLED.show();

                  } else {
                    if (action_group_running_step == 0) { /* Loop operation action group */
                      play_tune(DOC6, 300u, 1u);
                      rgbs[0].r = 255;
                      rgbs[0].g = 200;
                      rgbs[0].b = 0;
                      FastLED.show();
                      action_group_running_step = 2; /* cycle operation */
                    }
                  }
                }
              }
            }
            break;
          }
        case 2:
          {
            if (!state) {
              key_step[i] = 0;
            }
            break;
          }
      }
      keys_state[i] = state;
    }
    last_io_data[i] = io;
  }
}
