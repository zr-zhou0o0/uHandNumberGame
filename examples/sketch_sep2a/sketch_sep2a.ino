/***********************************/
/********uHand UNO 碰数例程(单手碰数）********/
/****本例程适用于uHand UNO右手手掌****/
/***********************************/
#include <FastLED.h> //RGB控制库（需要导入库）
#include <Servo.h> //舵机库
#include "tone.h" //音调库 

//#define Touch_pin 12  //定义触摸传感器的信号端接控制板的数字口2

//音调定义
const static uint16_t DOC5[] = { TONE_C5 };
const static uint16_t DOC6[] = { TONE_C6 };
const static uint16_t DO_RE_MI[3] = { TONE_C5, TONE_D5, TONE_E5 };
const static uint16_t MI_RE_DO[3] = { TONE_E5, TONE_D5, TONE_C5 };
const static uint16_t MI_RE_MI_RE[4] = { TONE_C7, TONE_C6, TONE_C7, TONE_C6 };

//按键引脚
const static uint8_t keyPins[2] = { 8, 9 };
// 舵机引脚
const static uint8_t servoPins[6] = { 7, 6, 5, 4, 3, 2 };
// 蜂鸣器引脚
const static uint8_t buzzerPin = 11;
// RGB灯引脚
const static uint8_t rgbPin = 13;

// RGB灯颜色对象
static CRGB rgbs[1];

//模式控制
typedef enum {
  MODE_IDLE,//开始自动进入IDLE状态
  MODE_GAME,//由Idle状态按K1进入Game状态，开始碰数游戏，出现胜负后进入END状态
  MODE_END,//包含胜负两个结果，按K2回到GAME状态，开始下一句游戏
  MODE_a,//未使用，可以加入其他功能
} UhandMode;

//模式变量
static UhandMode g_mode = MODE_IDLE;
static UhandMode g_mode_old = MODE_IDLE;

static uint8_t if_reset_number = 1; //记录是否需要更新舵机期望角度，0表示不需要，1表示需要

// 舵机角度相关变量 （舵机下标对应的位置： 0-大拇指 1-食指 2-中指 3-无名指 4-小指 5-云台）
static uint8_t extended_func_angles[6] = { 0,0,0,0,0,90 }; /* 二次开发例程使用的角度数值 */
static float servo_angles[6] = { 0,0,0,0,0,90 };  /* 舵机实际控制的角度数值 */
static uint8_t figure_finger[10][6] = {{0,0,0,0,0,90},{0,180,0,0,0,90},{0,180,180,0,0,90},{0,180,180,180,0,90},{0,180,180,180,180,90},
{180,180,180,180,180,90},{180,0,0,0,180,90},{180,180,0,0,0,90},{180,180,180,0,0,90},{0,90,0,0,0,90}};
/*从0到9对应的舵机角度数值*/
static uint8_t win_finger[6]  = {0,180,180,0,0,90};
static uint8_t lose_finger[6] = {0,0,180,0,0,90};

// 蜂鸣器相关变量
static uint16_t tune_num = 0;
static uint32_t tune_beat = 10;
static uint16_t *tune;

// 创建舵机控制对象
Servo servos[6];

// 舵机控制任务
static void servo_control(void);
// 蜂鸣器鸣响函数
void play_tune(uint16_t *p, uint32_t beat, uint16_t len);
// 蜂鸣器任务
void tune_task(void);
// 主要计算任务
void count_task(void);

//从键盘读取数字作为输入量
uint8_t read_from_keyboard(void);
uint8_t read_from_keyboard_left(void);
//按键扫描
void key_scan(void);

//对方轮次，读取输入，验证是否合法，以及对方是否胜利
void opp_turn(void);
//我方轮次，做出决策(通过PC端通信），验证我方是否胜利
void my_turn(void);

static uint8_t turn = 0;//记录轮次信息，0表示对方轮，1表示我方轮，开始默认轮次为对方轮2

//机器手指数字
static uint8_t myFigure[2] = {1,0};
//对方手指数字
static uint8_t yourFigure[2] = {1,0};



void setup() {
   // 初始化串口并设置速率
  Serial.begin(9600);
  // 设置串行端口读取数据的超时时间
  Serial.setTimeout(500);
  // 初始化按键引脚
  pinMode(keyPins[0], INPUT_PULLUP);
  pinMode(keyPins[1], INPUT_PULLUP);
  // 初始化蜂鸣器引脚
  pinMode(buzzerPin, OUTPUT);
  // 绑定舵机IO口
  for (int i = 0; i < 6; ++i) {
    servos[i].attach(servoPins[i],500,2500);
  }
  // 初始化RGB控制对象
  FastLED.addLeds<WS2812, rgbPin, GRB>(rgbs, 1);
  // 初始化颜色对象
  rgbs[0] = CRGB(0, 255, 0);
  // 根据颜色发光
  FastLED.show();
  // 蜂鸣器鸣响，频率1000Hz
  tone(buzzerPin, 1000);
  // 延时
  delay(100);
  // 蜂鸣器停止
  noTone(buzzerPin);
  //摆出1手势，开始游戏
  servo_control();
  //pinMode(Touch_pin, INPUT);//将TOUCH配置为输入(输入状态一般是将要读取这个引脚的状态，即读取传感器的反馈值）
  // put your setup code here, to run once:

}

void loop() {
  // 计算任务
  count_task();
  // 蜂鸣器鸣响任务
  tune_task();
  // 舵机控制
  servo_control();
  // 按键扫描
  key_scan();


}

void servo_control(void) {
  static uint32_t last_tick = 0;
  // 间隔25毫秒
  if (millis() - last_tick < 25) {
    return;
  }
  last_tick = millis();

  if(if_reset_number==1){
    if(g_mode==MODE_GAME){
      for (int i = 0; i < 6; ++i){
        extended_func_angles[i] = figure_finger[myFigure[0]][i];
      }
    }
    else if(g_mode == MODE_END){
      if(myFigure[0]==0&&myFigure[1]==0){
       for (int i = 0; i < 6; ++i){
        extended_func_angles[i] = win_finger[i];
        }
      }
      if(yourFigure[0]==0 &&yourFigure[1]==0){
       for (int i = 0; i < 6; ++i){
       extended_func_angles[i] = lose_finger[i];
        }
      }
    }
    else{
      for (int i = 0; i < 6; ++i){
        extended_func_angles[i] = figure_finger[myFigure[0]][i];
      }
    }
    if_reset_number = 0;
  }

  // 对6个舵机分别赋值
  for (int i = 0; i < 6; ++i) {
    
    servo_angles[i] = servo_angles[i] * 0.5 + extended_func_angles[i] * 0.5;
    servos[i].write(i == 0 || i == 5 ? 180 - servo_angles[i] : servo_angles[i]);
  }


}

// 蜂鸣器鸣响函数 参数1：音调组，参数2：音调鸣响时间，参数3：音调组元素个数
void play_tune(uint16_t *p, uint32_t beat, uint16_t len) {
  tune = p;
  tune_beat = beat;
  tune_num = len;
}

// 蜂鸣器任务
void tune_task(void) {
  static uint32_t l_tune_beat = 0;
  static uint32_t last_tick = 0;
  // 若未到定时时间 且 响的时间跟上一次的一样
  if (millis() - last_tick < l_tune_beat && tune_beat == l_tune_beat) {
    return;
  }
  l_tune_beat = tune_beat;
  last_tick = millis();
  // 若还有音调
  if (tune_num > 0) {
    tune_num -= 1;
    tone(buzzerPin, *tune++);
  } else { //无则暂停
    noTone(buzzerPin);
    tune_beat = 10;
    l_tune_beat = 10;
  }
}

void count_task(void)
{
  static uint32_t last_tick = 0;
  // 间隔400ms
  if (millis() - last_tick < 400) {
    return;
  }
  last_tick = millis();

  if(g_mode==MODE_GAME)
  {
    if(turn==0)
    {
      opp_turn();
    }
    else if(turn==1)
    {
      my_turn();
    }
    
  }

}

uint8_t read_from_keyboard(void)
{
  /*Serial.print("My: ");
  Serial.print(myFigure[0]);
  Serial.print(", Your: ");
  Serial.println(yourFigure[0]);
  */

  uint8_t ina;
  while (Serial.available() > 0) {
    String line = Serial.readStringUntil('\n');
    ina = line.toInt();
    return ina;
 
  }

  return 255; // 没有完整输入
}



uint8_t read_from_keyboard_left(void)
{
  return 0;
}

void key_scan(void){
  static uint16_t last_io_data[2];//上次扫描
  static bool keys_state[2];//记录当前按键是否按下
  static uint8_t key_step[2];//状态机步骤（0=未按下，1=按下等待释放，2=长按保持）
  static uint32_t pressed_tick[2];//按键按下的时间
  static uint32_t last_tick = 0;

  if(millis()- last_tick < 20){
    return;
  }
  last_tick = millis();

  for(int i = 0; i<2;++i){
    uint16_t io = digitalRead(keyPins[i]);
    //防抖处理,按键状态持续一段时间才进入if
    if (last_io_data[i]==io)
    {
      bool state = io == LOW? true: false;//state为ture表示按下
      switch(key_step[i]){
        case 0://未按下
        {
          if (state) {
              key_step[i] = 1;
              pressed_tick[i] = last_tick;
            }
            break;

        }
        case 1://短按
        {
          if(!state){
            key_step[i] = 0;
            if(i==0)//K1短按,从IDLE状态进入GAME状态
            {
              if(g_mode==MODE_IDLE){
                play_tune(DOC5, 100, 1);
                noTone(buzzerPin);
                g_mode = MODE_GAME;
                g_mode_old = g_mode;
                myFigure[0] = myFigure[1] = 1;
                yourFigure[0] = yourFigure[1] = 1;
              }
            }
            if(i==1)//K2短按，从end状态进入GAME状态
            {
              if(g_mode==MODE_END){
                play_tune(DOC5, 100, 1);
                noTone(buzzerPin);
                g_mode = MODE_GAME;
                g_mode_old = g_mode;
                //重置两数为1
                myFigure[0] = 1;
                myFigure[1] = 0;
                yourFigure[0] = 1;
                yourFigure[1] = 0;
              }
            }

          }
          break;
        }
      }
    }
    last_io_data[i] = io;

  }


}

//对方轮次，读取输入，验证是否合法，以及对方是否胜利
void opp_turn(void){


  uint8_t count[2];//读取的输入值
  uint8_t fit;//验证比较数组是否来自加数
  uint8_t fit_zero = 1;//验证已经存在的0是否被加

  count[0] = read_from_keyboard();
  /*Serial.print("解析结果: ");
  Serial.println(count[0]);*/
  count[1] = read_from_keyboard_left();//恒定读0
  

  uint8_t may_value[2];
  //right-right
  may_value[0] = (myFigure[0] + yourFigure[0])%10;
  may_value[1] = yourFigure[1];

  fit = (count[0] == may_value[0])&&(count[1] == may_value[1]);
  
  //对方输入的数合法，更新对方数字，判断对方是否获胜，否则进入我方轮
  if(fit){
    
    yourFigure[0] = count[0];
    yourFigure[1] = count[1];
      

    if((yourFigure[0]==0)&&(yourFigure[1]==0))
    {
      rgbs[0].r = 250;
      rgbs[0].g = 0;
      rgbs[0].b = 0;
      FastLED.show();
      g_mode_old = g_mode;
      g_mode = MODE_END;

      if_reset_number = 1;

    }
    else
      turn=1;
    
  
  }
}

//我方轮次，做出决策(直接加），验证我方是否胜利
void my_turn(void){

  myFigure[0]=myFigure[0]+yourFigure[0];

  if_reset_number = 1;

  //判断我方是否获胜
  if((myFigure[0]==0)&&(myFigure[1]==0))
  {
    rgbs[0].r = 250;
    rgbs[0].g = 250;
    rgbs[0].b = 0;
    FastLED.show();
    g_mode_old = g_mode;
    g_mode = MODE_END;
    if_reset_number = 1;
  }

  //进入对方轮，未获胜直接进入对方轮，若获胜下一局开始也是对方轮
  turn = 0;
}




