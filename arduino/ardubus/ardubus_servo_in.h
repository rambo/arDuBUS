#ifndef ardubus_servo_in_h
#define ardubus_servo_in_h
// Based on https://github.com/rambo/Arduino_rcreceiver
#include <Arduino.h> 
// Get this from https://github.com/rambo/PinChangeInt_userData
#include "PinChangeInt_userData.h"
#ifndef ARDUBUS_SERVO_IN_INITIAL_POSITION
#define ARDUBUS_SERVO_IN_INITIAL_POSITION 1500
#endif

// To hold data for reach RC input pin.
typedef struct {
    const uint8_t pin;
    volatile unsigned long start_micros;
    volatile unsigned long stop_micros;
    volatile boolean new_data;
    uint16_t servo_position; // microseconds
} ardubus_servo_in_RCInput;

// In format of { { pin1 }, { pin2 } } 
ardubus_servo_in_RCInput ardubus_servo_in_inputs[] = ARDUBUS_SERVO_INPUTS;
const uint8_t ardubus_servo_in_inputs_len = sizeof(ardubus_servo_in_inputs) / sizeof(ardubus_servo_in_RCInput);

// Called whenever a control pulse ends
void ardubus_servo_in_rc_pulse_low(void* inptr)
{
    ardubus_servo_in_RCInput* input = (ardubus_servo_in_RCInput*)inptr;
    input->stop_micros = micros();
    input->new_data = true;
}

// Called whenever a control pulse starts
void ardubus_servo_in_rc_pulse_high(void* inptr)
{
    ardubus_servo_in_RCInput* input = (ardubus_servo_in_RCInput*)inptr;
    input->new_data = false;
    input->start_micros = micros();
}

// Calculates the servo position, called from the update whenever there is new data
void ardubus_servo_in_calc_servo_position(void* inptr)
{
    ardubus_servo_in_RCInput* input = (ardubus_servo_in_RCInput*)inptr;
    input->servo_position = (uint16_t)(input->stop_micros - input->start_micros);
    input->new_data = false;
}


inline void ardubus_servo_in_setup()
{
    // Attach pin change interrupts for the RCInputs
    for (uint8_t i=0; i < ardubus_servo_in_inputs_len; i++)
    {
        // And set the init value
        ardubus_servo_in_inputs[i].servo_position = ARDUBUS_SERVO_IN_INITIAL_POSITION;
        PCintPort::attachInterrupt(ardubus_servo_in_inputs[i].pin, &ardubus_servo_in_rc_pulse_high, RISING, &ardubus_servo_in_inputs[i]);
        PCintPort::attachInterrupt(ardubus_servo_in_inputs[i].pin, &ardubus_servo_in_rc_pulse_low, FALLING, &ardubus_servo_in_inputs[i]);
    }
}

inline void ardubus_servo_in_update()
{
    for (uint8_t i=0; i < ardubus_servo_in_inputs_len; i++)
    {
        if (ardubus_servo_in_inputs[i].new_data)
        {
            calc_servo_position(&ardubus_servo_in_inputs[i]);
            // TODO: output value
            Serial.print(F("CS")); // CS<index_byte><pulse_duration_in_us>
            Serial.write(i);
            ardubus_print_int_as_4hex(ardubus_servo_in_inputs[i].servo_position);
            Serial.println(F(""));
        }
    }
}

inline void ardubus_servo_in_report()
{
    for (uint8_t i=0; i < ardubus_servo_in_inputs_len; i++)
    {
        Serial.print(F("RS")); // RS<index_byte><position_in_us>
        Serial.write(i);
        ardubus_print_int_as_4hex(ardubus_servo_in_inputs[i].servo_position);
        Serial.println(F(""));
    }
}

inline void ardubus_servo_in_process_command(char *incoming_command)
{
    // This is a no-op (but defined so that all submodules have same API)
}

#endif
