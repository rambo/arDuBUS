#!/usr/bin/env python
# The real deal, this will talk with an arduino and pass signals/method calls back and forth
from __future__ import with_statement
import os,sys

# Import our DBUS service module
import dbushelpers.service
import dbus
import binascii,time
import yaml

# We need to offset the pin numbers to CR and LF which are control characters to us (NOTE: this *must* be same as in ardubus.h)
# TODO: Use hex encoded values everywhere to avoid this
PIN_OFFSET=32 

class ardubus(dbushelpers.service.baseclass):
    def __init__(self, config, launcher_instance, **kwargs):
        super(ardubus, self).__init__(config, launcher_instance, **kwargs)
        self.object_name = kwargs['device_name']
        self.serial_device = kwargs['serial_device']
        self.serial_speed = kwargs['serial_speed']
        self.config_reloaded() # Triggers all config normalizations and mapping rebuilds
        self.initialize_serial()
        print "Board initialized as %s:%s with config %s" % (self.dbus_interface_name, self.dbus_object_path, repr(self.config))
        self.print_debug = False
        self.last_response_time = None
        self.dead_board_timeout = 15 # Seconds, if we have no messages for this many seconds suppose the board is dead

    def send_serial_command(self, command):
        command = command + "\n"
        for c in command:
            self.serial_port.write(c)
        self.serial_port.flush()
        # TODO Check for the ACK from board somehow (not exactly trivial when another thread is constantly reading the port for reports [though now the sketch acknowledges the command it parses in full so we could look into the history])
        #print 'DEBUG: sent command %s' % repr(command)
        return True
        
    def p2b(self, pin):
        """Convert pin number integer to a byte to be sent to the sketch"""
        return chr(pin+PIN_OFFSET)

    def normalize_pins(self, config_section):
        """Normalizes a pin config to dict with pin ans alias keys"""
        #print "normalize_pins: BEFORE %s" % config_section
        if type(config_section) == list:
            keys = range(len(config_section))
        if type(config_section) == dict:
            keys = config_section.keys
        for k in keys:
            item = config_section[k]
            if type(item) != dict:
                item = { 'pin': item }
            # Make sure this key exists
            if not item.has_key('alias'):
                item['alias'] = None
            config_section[k] = item
        #print "normalize_pins: AFTER %s" % config_section
        return config_section

    def normalize_config(self):
        supports_aliases = (
            'digital_in_pins',
            'digital_out_pins',
            'pca9535_inputs',
            'pulse_input_pins',
            'servo_pins',
            'digital_pwmout_pins',
        )
        for k in range(len(supports_aliases)):
            section = supports_aliases[k]
            if not self.config.has_key(k):
                continue
            self.config[k] = self.normalize_pins(self.config[k])
        # reminder to support output aliasing in the future, somehow...
        #if self.config.has_key('pca9535_outputs'):
        #    self.config['pca9535_outputs'] = self.normalize_pins(self.config['pca9535_outputs'])
        pass

    def rebuild_alias_maps(self):
        # Config key to method mapping
        supports_aliased_output = {
            'digital_out_pins': self.set_dio,
            'servo_pins': self.set_servo,
            'digital_pwmout_pins': self.set_pwm,
        }
        # In the format of aliases['alias'] = (index, method)
        self.aliases = {}
        for section in supports_aliased_output.keys():
            if not self.config.has_key(section):
                continue
            for idx in range(len(self.config[section])):
                alias = self.config[section][idx]['alias']
                if not alias:
                    continue
                if self.aliases.has_key(alias):
                    from exceptions import RuntimeError
                    raise RuntimeError("Duplicate alias %s on device %s in file %s" % (alias, self.object_name, self.config_file_path))
                self.aliases[alias] = (idx, supports_aliased_output[section])
        pass

    @dbus.service.method('fi.hacklab.ardubus', in_signature='sn') # "y" is the signature for a byte, n is 16bit signed integer
    def set_alias(self, alias, value):
        """Aliased output, supports only the simple ones where one value is enough"""
        idx = self.aliases[alias][0]
        callback = self.aliases[alias][1]
        callback(idx, value)

    def config_reloaded(self):
        """Recalculates all config mappings etc"""
        self.normalize_config()
        self.rebuild_alias_maps()

    @dbus.service.method('fi.hacklab.ardubus')
    def get_config(self):
        """Returns the config map, the remote end can do processing based on aliases and whatnot"""
        # TODO: the complex dictionary needs to be mapped to proper dbus objects in entirety 
        #return dbus.Dictionary(self.config)
        # alternatively we could encode it back to YAML and then re-parse on receiver
        return yaml.dump(self.config)

    def stop_serial(self):
        self.serial_alive = False
        self.receiver_thread.join()
        self.serial_port.close()

    @dbus.service.method('fi.hacklab.ardubus')
    def quit(self):
        """Closes the serial port and unloads from DBUS"""
        self.stop_serial()
        self.remove_from_connection()

    @dbus.service.method('fi.hacklab.ardubus')
    def hello(self):
        return "Hello,World! My name is " + self.object_name

    @dbus.service.method('fi.hacklab.ardubus', in_signature='yy') # "y" is the signature for a byte
    def set_pwm(self, pwm_index, cycle):
        if cycle in [ 13, 10]: #Offset values that map to CR or LF by one
            cycle += 1
        self.send_serial_command("P%s%s" % (self.p2b(pwm_index), chr(cycle)))

    @dbus.service.method('fi.hacklab.ardubus', in_signature='yyy') # "y" is the signature for a byte
    def set_aircore_position(self, board_index, motorno, cycle):
        correction = 0
        #print "correction=%d"%self.config['aircore_correction_values'][board_index][motorno]

        if (    self.config.has_key('aircore_correction_values')
            and self.config['aircore_correction_values'].has_key(board_index)
            and self.config['aircore_correction_values'][board_index].has_key(motorno)):
            correction = self.config['aircore_correction_values'][board_index][motorno]

        
        cycle=(cycle+correction) % 255
        if cycle in [ 13, 10]: #Offset values that map to CR or LF by one
            cycle += 1
        self.send_serial_command("A%s%s%s" % (self.p2b(board_index), self.p2b(motorno), chr(cycle)))

    @dbus.service.method('fi.hacklab.ardubus', in_signature='yyy') # "y" is the signature for a byte
    def set_jbol_pwm(self, jbol_index, ledno, cycle):
        try:
            ledno = self.config['pca9635RGBJBOL_maps'][int(jbol_index)][int(ledno)]
        except Exception,e:
            print "set_jbol_pwm: got exception %s" % e
            pass
            
        if cycle in [ 13, 10]: #Offset values that map to CR or LF by one
            cycle += 1
        self.send_serial_command("J%s%s%s" % (self.p2b(jbol_index), self.p2b(ledno), chr(cycle)))

    @dbus.service.method('fi.hacklab.ardubus', in_signature='yy') # "y" is the signature for a byte
    def set_servo(self, servo_index, value):
        if value > 180:
            value = 180 # Servo library accepts values from 0 to 180 (degrees)
        if value in [ 13, 10]: #Offset values that map to CR or LF by one
            value += 1
        self.send_serial_command("S%s%s" % (self.p2b(servo_index), chr(value)))

    @dbus.service.method('fi.hacklab.ardubus', in_signature='yn') # "y" is the signature for a byte, n is 16bit signed integer
    def set_servo_us(self, servo_index, value):
        self.send_serial_command("s%s%s" % (self.p2b(servo_index), "%04X" % int(value)))


    @dbus.service.method('fi.hacklab.ardubus', in_signature='yb') # "y" is the signature for a byte
    def set_595bit(self, bit_index, state):
        if state:
            self.send_serial_command("B%s1" % self.p2b(bit_index))
        else:
            self.send_serial_command("B%s0" % self.p2b(bit_index))

    @dbus.service.method('fi.hacklab.ardubus', in_signature='yy') # "y" is the signature for a byte
    def set_595byte(self, reg_index, state):
        self.send_serial_command("W%s%s" % (self.p2b(reg_index), binascii.hexlify(str(state)).upper()))

    @dbus.service.method('fi.hacklab.ardubus', in_signature='yb') # "y" is the signature for a byte
    def set_dio(self, digital_index, state):
        if state:
            self.send_serial_command("D%s1" % self.p2b(digital_index))
        else:
            self.send_serial_command("D%s0" % self.p2b(digital_index))

    @dbus.service.method('fi.hacklab.ardubus', in_signature='yb') # "y" is the signature for a byte
    def set_pca9535_bit(self, digital_index, state):
        if state:
            self.send_serial_command("E%s1" % self.p2b(digital_index))
        else:
            self.send_serial_command("E%s0" % self.p2b(digital_index))

    @dbus.service.method('fi.hacklab.ardubus', in_signature='yy') # "y" is the signature for a byte
    def set_pca9535_byte(self, reg_index, state):
        return False
        # TODO: implement
        # example from 595
        #self.send_serial_command("W%s%s" % (self.p2b(reg_index), binascii.hexlify(str(state)).upper()))

    @dbus.service.method('fi.hacklab.ardubus', in_signature='ys') # "y" is the signature for a byte ("s" for string)
    def set_i2cascii_data(self, reg_index, bytes):
        self.send_serial_command("w%s%s" % (self.p2b(reg_index), bytes))

    @dbus.service.signal('fi.hacklab.ardubus')
    def alias_change(self, alias, state, sender):
        """Aliased pin has changed state"""
        #print "SIGNALLING: %s changed to %d on %s" % (alias, state, sender)
        pass

    @dbus.service.signal('fi.hacklab.ardubus')
    def alias_report(self, alias, state, time, sender):
        """Aliased state report"""
        #print "SIGNALLING: %s changed to %d on %s" % (alias, state, sender)
        pass

    @dbus.service.signal('fi.hacklab.ardubus')
    def dio_change(self, p_index, state, sender):
        if (    self.config['digital_in_pins'][p_index].has_key('alias')
            and self.config['digital_in_pins'][p_index]['alias']):
            self.alias_change(self.config['digital_in_pins'][p_index]['alias'], state, sender)
        pass

    @dbus.service.signal('fi.hacklab.ardubus')
    def pca9535_change(self, p_index, state, sender):
        #print "SIGNALLING: Pin(index) %d changed to %d on %s" % (p_index, state, sender)
        if (    self.config['pca9535_inputs'][p_index].has_key('alias')
            and self.config['pca9535_inputs'][p_index]['alias']):
            self.alias_change(self.config['pca9535_inputs'][p_index]['alias'], state, sender)
        pass

    @dbus.service.signal('fi.hacklab.ardubus')
    def dio_report(self, p_index, state, time, sender):
        #print "SIGNALLING: Pin(index) %d has been %d for %dms on %s" % (p_index, state, time, sender)
        if self.config['digital_in_pins'][p_index]['alias']:
            self.alias_report(self.config['digital_in_pins'][p_index]['alias'], state, time, sender)
        pass

    @dbus.service.signal('fi.hacklab.ardubus')
    def pca9535_report(self, p_index, state, time, sender):
        #print "SIGNALLING: Pin(index) %d has been %d for %dms on %s" % (p_index, state, time, sender)
        pass

    @dbus.service.signal('fi.hacklab.ardubus')
    def aio_change(self, p_index, value, sender):
        #print "SIGNALLING: Analog-pin(index) %d changed to %d on %s" % (p_index, value, sender)
        pass

    @dbus.service.signal('fi.hacklab.ardubus')
    def aio_report(self, p_index, value, time, sender):
        #print "SIGNALLING: Analog-pin(index) %d has been %d for %dms on %s" % (p_index, value, time, sender)
        pass

    @dbus.service.signal('fi.hacklab.ardubus')
    def pulsein_change(self, p_index, value, sender):
        #print "SIGNALLING: servo-pin(index) %d changed to %d on %s" % (p_index, value, sender)
        # This might not work, the other aliased signals are booleans...
        if (    self.config['pulse_input_pins'][p_index].has_key('alias')
            and self.config['pulse_input_pins'][p_index]['alias']):
            self.alias_change(self.config['pulse_input_pins'][p_index]['alias'], value, sender)
        pass

    @dbus.service.signal('fi.hacklab.ardubus')
    def pulsein_report(self, p_index, value, sender):
        #print "SIGNALLING: servo-pin(index) %d changed to %d on %s" % (p_index, value, sender)
        pass


    @dbus.service.method('fi.hacklab.ardubus')
    def reset(self):
        self.serial_port.setDTR(False) # Reset the arduino by driving DTR for a moment (RS323 signals are active-low)
        time.sleep(0.050)
        self.serial_port.setDTR(True)

    def initialize_serial(self):
        import threading, serial
        print "initialize_serial called"
        self.input_buffer = ""
        self.serial_port = serial.Serial(self.serial_device, self.serial_speed, xonxoff=False, timeout=0.00001)
        self.receiver_thread = threading.Thread(target=self.serial_reader)
        self.receiver_thread.setDaemon(1)
        self.receiver_thread.start()
        print "%s serial thread started" % self.dbus_object_path


    def message_received(self, input_buffer):
        #print "message_received called with buffer %s" % repr(input_buffer)
        self.last_response_time = time.time()
        try:
            if (   len(self.input_buffer) >= 4
                and self.input_buffer[:4] == 'PONG'):
                return
            if (self.input_buffer[:2] == 'CD'):
                # State change
                self.dio_change(ord(input_buffer[2]), bool(int(input_buffer[3])), self.object_name)
                return
            if (self.input_buffer[:2] == 'CP'):
                # State change
                self.pca9535_change(ord(input_buffer[2]), bool(int(input_buffer[3])), self.object_name)
                return
            if (self.input_buffer[:2] == 'RD'):
                self.dio_report(ord(input_buffer[2]), bool(int(input_buffer[3])), int(input_buffer[4:12], 16), self.object_name)
                pass
            if (self.input_buffer[:2] == 'RP'):
                self.pca9535_report(ord(input_buffer[2]), bool(int(input_buffer[3])), int(input_buffer[4:12], 16), self.object_name)
                pass
            if (self.input_buffer[:2] == 'CA'):
                self.aio_change(ord(input_buffer[2]), int(input_buffer[3:7], 16), self.object_name)
                pass
            if (self.input_buffer[:2] == 'CS'):
                self.pulsein_change(ord(input_buffer[2]), int(input_buffer[3:7], 16), self.object_name)
                pass
            if (self.input_buffer[:2] == 'RS'):
                self.pulsein_report(ord(input_buffer[2]), int(input_buffer[3:7], 16), self.object_name)
                pass
            if (self.input_buffer[:2] == 'RA'):
                self.aio_report(ord(input_buffer[2]), int(input_buffer[3:7], 16), int(input_buffer[6:15], 16), self.object_name)
                pass
        except Exception,e:
            print "message_received: Got exception %s" % e
            # Ignore indexerrors, they just mean we could not parse the command
            pass


    def serial_reader(self):
        import string,binascii
        import serial # We need the exceptions from here
        self.serial_alive = True
        try:
            while self.serial_alive:
                # Check that the board is still talking to us regularly
                if self.last_response_time: # wait for at least one message first
                    if ((time.time() - self.last_response_time) > self.dead_board_timeout):
                        print " ** No messages received from %s for %d seconds ** " % (self.dbus_object_path, self.dead_board_timeout)
                        self.serial_alive = False
                        continue
                        # TODO: Raise a specific error ??
                 
                if not self.serial_port.inWaiting():
                    # Don't try to read if there is no data, instead sleep (yield) a bit
                    time.sleep(0)
                    continue
                data = self.serial_port.read(1)
                if len(data) == 0:
                    continue
                if self.print_debug:
                    # hex-encode unprintable characters
                    #if data not in string.letters.join(string.digits).join(string.punctuation).join("\r\n"):
                    #    sys.stdout.write("\\0x".join(binascii.hexlify(data)))
                    # OTOH repr was better afterall
                    if data not in "\r\n":
                        sys.stdout.write(repr(data))
                    else:
                        sys.stdout.write(data)
                # Put the data into inpit buffer and check for CRLF
                self.input_buffer += data
                # TODO: make the linebreak configurable
                # Trim prefix NULLs and linebreaks
                self.input_buffer = self.input_buffer.lstrip(chr(0x0) + "\r\n")
                #print "input_buffer=%s" % repr(self.input_buffer)
                if (    len(self.input_buffer) > 1
                    and self.input_buffer[-2:] == "\r\n"):
                    # Got a message, parse it (sans the CRLF) and empty the buffer
                    self.message_received(self.input_buffer[:-2])
                    self.input_buffer = ""

        except (IOError, serial.SerialException), e:
            print "Got exception %s" % e
            self.serial_alive = False
            # It seems we cannot really call this from here, how to detect the problem in main thread ??
            #self.launcher_instance.unload_device(self.object_name)

if __name__ == '__main__':
    print "Use ardbus_launcher.py"
    sys.exit(1)
