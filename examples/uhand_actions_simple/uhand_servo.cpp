#include "uhand_servo.h"

void HW_ACTION_CTL::action_set(int num){
  action_num = num;
}

static int HW_ACTION_CTL::action_state_get(void){
  return action_num;
}

//执行单一动作时使用
void HW_ACTION_CTL::action_task(void){
  static uint32_t last_tick = 0;
  static uint8_t step = 0;
  static uint8_t num = 0 , delay_count = 0;
  if(action_num != 0 && action_num <= action_count)
  {

    extended_func_angles[0] = action[action_num-1][1];
    extended_func_angles[1] = action[action_num-1][2];
    extended_func_angles[2] = action[action_num-1][3];
    extended_func_angles[3] = action[action_num-1][4];
    extended_func_angles[4] = action[action_num-1][5];
    extended_func_angles[5] = action[action_num-1][6];

    // 清空动作变量
    action_num = 0;
  }
}
