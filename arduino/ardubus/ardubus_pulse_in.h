#ifndef ardubus_pulse_in_h
#define ardubus_pulse_in_h
// Based on https://github.com/rambo/Arduino_rcreceiver
#include <Arduino.h> 
// Get this from https://github.com/rambo/PinChangeInt_userData
#include "PinChangeInt_userData.h"
#ifndef ARDUBUS_PULSE_IN_INITIAL_LENGTH
#define ARDUBUS_PULSE_IN_INITIAL_LENGTH 1500
#endif

// To hold data for reach RC input pin.
typedef struct {
    const uint8_t pin;
    volatile unsigned long start_micros;
    volatile unsigned long stop_micros;
    volatile boolean new_data;
    uint16_t pulse_length; // microseconds
} ardubus_pulse_in_RCInput;

// In format of { { pin1 }, { pin2 } } 
ardubus_pulse_in_RCInput ardubus_pulse_in_inputs[] = ARDUBUS_PULSE_INPUTS;
const uint8_t ardubus_pulse_in_inputs_len = sizeof(ardubus_pulse_in_inputs) / sizeof(ardubus_pulse_in_RCInput);

// Called whenever a control pulse ends
void ardubus_pulse_in_rc_pulse_low(void* inptr)
{
    ardubus_pulse_in_RCInput* input = (ardubus_pulse_in_RCInput*)inptr;
    input->stop_micros = micros();
    input->new_data = true;
}

// Called whenever a control pulse starts
void ardubus_pulse_in_rc_pulse_high(void* inptr)
{
    ardubus_pulse_in_RCInput* input = (ardubus_pulse_in_RCInput*)inptr;
    input->new_data = false;
    input->start_micros = micros();
}

// Calculates the servo position, called from the update whenever there is new data
void ardubus_pulse_in_calc_pulse_length(void* inptr)
{
    ardubus_pulse_in_RCInput* input = (ardubus_pulse_in_RCInput*)inptr;
    input->pulse_length = (uint16_t)(input->stop_micros - input->start_micros);
    input->new_data = false;
}


inline void ardubus_pulse_in_setup()
{
    // Attach pin change interrupts for the RCInputs
    for (uint8_t i=0; i < ardubus_pulse_in_inputs_len; i++)
    {
        // And set the init value
        ardubus_pulse_in_inputs[i].pulse_length = ARDUBUS_PULSE_IN_INITIAL_LENGTH;
        PCintPort::attachInterrupt(ardubus_pulse_in_inputs[i].pin, &ardubus_pulse_in_rc_pulse_high, RISING, &ardubus_pulse_in_inputs[i]);
        PCintPort::attachInterrupt(ardubus_pulse_in_inputs[i].pin, &ardubus_pulse_in_rc_pulse_low, FALLING, &ardubus_pulse_in_inputs[i]);
    }
}

inline void ardubus_pulse_in_update()
{
    for (uint8_t i=0; i < ardubus_pulse_in_inputs_len; i++)
    {
        if (ardubus_pulse_in_inputs[i].new_data)
        {
            ardubus_pulse_in_calc_pulse_length(&ardubus_pulse_in_inputs[i]);
            // TODO: output value
            Serial.print(F("CS")); // CS<index_byte><pulse_duration_in_us>
            Serial.write(i);
            ardubus_print_int_as_4hex(ardubus_pulse_in_inputs[i].pulse_length);
            Serial.println(F(""));
        }
    }
}

inline void ardubus_pulse_in_report()
{
    for (uint8_t i=0; i < ardubus_pulse_in_inputs_len; i++)
    {
        Serial.print(F("RS")); // RS<index_byte><position_in_us>
        Serial.write(i);
        ardubus_print_int_as_4hex(ardubus_pulse_in_inputs[i].pulse_length);
        Serial.println(F(""));
    }
}

inline void ardubus_pulse_in_process_command(char *incoming_command)
{
    // This is a no-op (but defined so that all submodules have same API)
}

#endif
