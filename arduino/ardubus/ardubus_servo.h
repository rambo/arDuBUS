#ifndef ardubus_servo_h
#define ardubus_servo_h
#include <Arduino.h> 
#include <Servo.h>

// Enumerate the servo pins from the preprocessor
const byte ardubus_servo_output_pins[] = ARDUBUS_SERVO_OUTPUTS;
// Declare a Servo object for each
Servo ardubus_servos[sizeof(ardubus_servo_output_pins)] = Servo();

inline void ardubus_servo_setup()
{
    for (byte i=0; i < sizeof(ardubus_servo_output_pins); i++)
    {
        ardubus_servos[i].attach(ardubus_servo_output_pins[i]);
        ardubus_servos[i].write(90);
    }
}

inline void ardubus_servo_update()
{
    // This is a no-op (but defined so that all submodules have same API)
}

inline void ardubus_servo_report()
{
    /**
     * Not used yet anywhere, also: convert to output 4 hex int
    for (byte i=0; i < sizeof(ardubus_servo_output_pins); i++)
    {
        Serial.print(F("RS")); // RS<index_byte><value in hex>
        Serial.write(i);
        ardubus_print_byte_as_2hex(ardubus_servos[i].read());
        Serial.println(F(""));
        // TODO: Keep track of duration ??
    }
     */
}

inline void ardubus_servo_process_command(char *incoming_command)
{
    switch(incoming_command[0])
    {
        case 0x53: // ASCII "S" (P<indexbyte><value>) //Note that the indexbyte is index of the servos-array, not pin number
            ardubus_servos[incoming_command[1]-ARDUBUS_INDEX_OFFSET].write(incoming_command[2]);
            Serial.print(F("S"));
            Serial.print(incoming_command[1]);
            Serial.print(incoming_command[2]);
            return ardubus_ack();
            break;
        case 0x73: // ASCII "s" (P<indexbyte><int_as_hex) //Note that the indexbyte is index of the servos-array, not pin number
            int value = ardubus_hex2int(incoming_command[2], incoming_command[3], incoming_command[4], incoming_command[5]);
            ardubus_servos[incoming_command[1]-ARDUBUS_INDEX_OFFSET].write(value);
            Serial.print(F("S"));
            Serial.print(incoming_command[1]);
            Serial.print(incoming_command[2]);
            Serial.print(incoming_command[3]);
            Serial.print(incoming_command[4]);
            Serial.print(incoming_command[5]);
            return ardubus_ack();
            break;
    }
}

#endif
// *********** END OF CODE **********
