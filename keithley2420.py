import serial

class Keithley2420Exception(Exception):
  """Exception produced by the Keithley2420 class"""
  def __init__(self, msg):
      super().__init__(msg)

class Keithley2420(serial.Serial):
  """Keithley2420 driver class"""
  def __init__(self, port="/dev/tty.usbserial-A700CLX4", debug=True):
    """Initialize and configure serial communications"""
    super().__init__(port)

    # Identify device
    self.id = self.identify(debug=debug)

  def reset(self):
    """Power-up reset device"""
    # Send command and decode response
    self.cmd("*RST")
  
  def identify(self, debug=False):
    """Identify device, ensure it has correct make/model/version, return device ID"""
    # Send command and decode response
    line = self.cmd("*IDN?")
    try:
      make, model, id, version = line.strip().split(",")
      if debug:
        print(make, model, id, version)
    except ValueError as e:
      raise Keithley2420Exception(f"Couldn't unpack line: {repr(line)}")
    
    # Check device make, model, version
    if make != "KEITHLEY INSTRUMENTS INC.":
      raise Keithley2420Exception(f"Device make is not KEITHLEY INSTRUMENTS INC.: {make}")
    if model != "MODEL 2420":
      raise Keithley2420Exception(f"Device model is not MODEL 2420: {model}")
      
    # Return device ID (serial number)
    return int(id)

  def measure(self):
    """Collect measurement"""
    trigger = self.cmd(":MEAS:CURR?")
    return float(trigger.strip().split(",")[1])

  def cmd(self, cmd):
    """Send command (with buffer flushes) and return response"""
    # Send command and receive response
    self.reset_input_buffer()
    self.write(bytes(f"{cmd}\r\n", "utf-8"))
    self.reset_output_buffer()
    line = self.readline()

    # Return response as string
    return line.decode()

# Simple measurement test
if __name__ == "__main__":
  with Keithley2420("/dev/ttyUSB2") as keithley:
    print(keithley.measure())
    print(keithley.measure())
    print(keithley.measure())
    print(keithley.measure())
    print(keithley.measure())