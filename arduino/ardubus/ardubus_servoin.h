#ifndef ardubus_servo_in_h
#define ardubus_servo_in_h
#include <Arduino.h> 
// Get this from https://github.com/rambo/PinChangeInt_userData
#include "PinChangeInt_userData.h"
#ifndef ardubus_servo_in_SERVO_INITIAL_POSITION
#define ardubus_servo_in_SERVO_INITIAL_POSITION 1500
#endif

inline void ardubus_servo_in_setup()
{
}

inline void ardubus_servo_in_update()
{
}

inline void ardubus_servo_in_report()
{
}

inline void ardubus_servo_in_process_command(char *incoming_command)
{
    // This is a no-op (but defined so that all submodules have same API)
}

#endif
