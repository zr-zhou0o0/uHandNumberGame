//Action group file
#include <Arduino.h>
#define action_count 3 //Number of action groups

/*数组成员：action[action_count][0]--数据有效性，=0时不被执行
           action[action_count][1-6]--该动作各个舵机的位置值
*/
static uint8_t action[action_count][7] = 
    {
      //Action  1
      {1,0,0,0,0,0,90}, 

      //Action  2
      // {1,180,180,180,180,180,0},
      {1 ,18 ,177 ,179 ,0 ,0 ,108},

      //Action  3
      {1,19,43,40,8,23,116}
    };
