#ifndef ardubus_digital_in_h
#define ardubus_digital_in_h
#include <Arduino.h>
// TODO: Rewrite for Bounce2
#include <Bounce2.h>
#ifndef ARDUBUS_DIGITAL_IN_DEBOUNCE_TIME
#define ARDUBUS_DIGITAL_IN_DEBOUNCE_TIME 20 // milliseconds, see Bounce library
#endif
#ifndef ARDUBUS_DIGITAL_IN_DEBOUNCE_UPDATE_TIME
#define ARDUBUS_DIGITAL_IN_DEBOUNCE_UPDATE_TIME 5 // Milliseconds, how often to call update() on the ardubus_digital_in_update
#endif



// Enumerate the input pins from the preprocessor
const byte ardubus_digital_in_pins[] = ARDUBUS_DIGITAL_INPUTS;
// Declare and fake-initialize a debouncer for each
Bounce ardubus_digital_in_bouncers[sizeof(ardubus_digital_in_pins)] = Bounce(ardubus_digital_in_pins[0], ARDUBUS_DIGITAL_IN_DEBOUNCE_TIME); // We must initialize these here or things break, will overwrite with new instances in setup()


inline void ardubus_digital_in_setup()
{
    // Setup the deardubus_digital_in_bouncers
    for (byte i=0; i < sizeof(ardubus_digital_in_pins); i++)
    {
        pinMode(ardubus_digital_in_pins[i], INPUT);
#ifndef ARDUBUS_DIGITAL_IN_NO_PULLUP
        if (ardubus_digital_in_pins[i] != 13)
        {
            digitalWrite(ardubus_digital_in_pins[i], HIGH); // enable internal pull-up (except for #13 which has the led and external resistor, which will cause issues, see http://www.arduino.cc/en/Tutorial/DigitalPins)
        }
#endif
        ardubus_digital_in_bouncers[i] = Bounce(ardubus_digital_in_pins[i], ARDUBUS_DIGITAL_IN_DEBOUNCE_TIME);
    }
}

// Calls update method on all of the digital inputs and outputs message to Serial if state changed
unsigned long ardubus_digital_in_last_debounce_time;
inline void ardubus_digital_in_update_bouncers()
{
    // Update debouncer states
    for (byte i=0; i < sizeof(ardubus_digital_in_pins); i++)
    {
        if (ardubus_digital_in_bouncers[i].update())
        {
            // State changed
            Serial.print(F("CD")); // CD<index_byte><state_byte>
            Serial.write(i);
            Serial.println(ardubus_digital_in_bouncers[i].read());
        }
    }
    ardubus_digital_in_last_debounce_time = millis();
}

inline void ardubus_digital_in_update()
{
    if ((millis() - ardubus_digital_in_last_debounce_time) > ARDUBUS_DIGITAL_IN_DEBOUNCE_UPDATE_TIME)
    {
        ardubus_digital_in_update_bouncers();
    }
}

inline void ardubus_digital_in_report()
{
    for (byte i=0; i < sizeof(ardubus_digital_in_pins); i++)
    {
        Serial.print(F("RD")); // RD<index_byte><state_byte><time_long_as_hex>
        Serial.write(i);
        Serial.print(ardubus_digital_in_bouncers[i].read());
        ardubus_print_ulong_as_8hex(ardubus_digital_in_bouncers[i].duration());
        Serial.println(F(""));
    }
}

inline void ardubus_digital_in_process_command(char *incoming_command)
{
    // This is a no-op (but defined so that all submodules have same API)
}


#endif
// *********** END OF CODE **********
