import serial

class Fluke8808AException(Exception):
  """Exception produced by the Fluke8808A class"""
  def __init__(self, msg):
      super().__init__(msg)

class Fluke8808A(serial.Serial):
  """Fluke8808A driver class"""
  def __init__(self, port="/dev/tty.usbserial-A700CLX4", reset=False, debug=True):
    """Initialize and configure serial communications"""
    super().__init__(port)

    # Reset device
    if reset:
      self.reset()

    # Identify device
    self.id = self.identify(debug=debug)

    # Switch to DC current measurement mode
    self.mode("ADC")

  def reset(self):
    """Power-up reset device"""
    # Send command and decode response
    self._cmd("*RST", check_success=True)
  
  def identify(self, debug=False):
    """Identify device, ensure it has correct make/model/version, return device ID"""
    # Send command and decode response
    line = self._cmd("*IDN?")
    try:
      make, model, id, version = line.strip().split(", ")
      if debug:
        print(make, model, id, version)
    except ValueError as e:
      raise Fluke8808AException(f"Couldn't unpack line: {line}")
    
    # Check device make, model, version
    if make != "FLUKE":
      raise Fluke8808AException(f"Device make is not FLUKE: {make}")
    if model != "8808A":
      raise Fluke8808AException(f"Device model is not 8808A: {model}")
    if version != "1.1r D2.0":
      raise Fluke8808AException(f"Device versions are not 1.1r D2.0: {version}")
      
    # Return device ID (serial number)
    return int(id)
  
  def mode(self, mode="ADC"):
    """Set measurement mode"""
    self._cmd(mode, check_success=True)

  def measure(self):
    # Send command and decode response
    line = self._cmd("MEAS?")
    try:
      value, mode = line.strip().split()
    except ValueError as e:
      raise Fluke8808AException(f"Couldn't unpack line: {line}")
    
    # Make sure in DC current measurement mode
    if mode != "ADC":
      raise Fluke8808AException(f"Not in ADC mode: {mode}")
    
    # Return measured value
    return float(value)

  def _cmd(self, cmd, check_success=False):
    """Send command (with buffer flushes) and return response"""
    # Send command and receive response
    self.reset_input_buffer()
    self.write(bytes(f"{cmd}\r\n", "utf-8"))
    self.reset_output_buffer()
    line = self.readline()

    # Check success
    if check_success and line != b"=>\r\n":
      raise Fluke8808AException(f"Error: {line}")
    
    # Return response as string
    return line.decode()

# Simple measurement test
if __name__ == "__main__":
  with Fluke8808A() as fluke:
    print(fluke.measure())