# Import Python libraries
import json

# Import spidev library
from spidev import SpiDev

# Import GPIO library
import RPi.GPIO as GPIO

# Pin mappings
RRAM_BUSY_PIN = 16
MCLK_PAUSE_PIN = 18

# Register indices
REG_MISC = 16
REG_ADDR = 17
REG_WRITE = 18
REG_CMD = 22
REG_STATE = 23
REG_DIAG = 24
REG_READ = 25

# FSM opcodes
OP_TEST_PULSE = 0
OP_TEST_READ = 1
OP_TEST_CPULSE = 2
OP_CYCLE = 3
OP_READ = 4
OP_WRITE = 5
OP_REFRESH = 6

class EMBERDriver(object):
  '''Class to interface with EMBER chip'''
  def __init__(self, settings, test_conn=True):
    '''Initialize and configure SPI/GPIO interfaces'''
    # Load and configure settings
    if isinstance(settings, str):
      settings = json.load(open(settings))
    self.configure(settings)

    # Create SPI device
    self.spi = SpiDev()
    self.spi.open(0, 0)
    self.spi.cshigh = True
    self.spi.max_speed_hz = settings["spi_freq"]
    self.spi.mode = 0b01

    # Test connection
    if test_conn:
      val = self.read_reg(31)
      if val == 0x52414D:
        print("SPI connection detected!")
      else:
        raise Exception("No SPI connection detected:", val)

    # Create GPIO driver
    GPIO.setmode(GPIO.BOARD)
    GPIO.setup(RRAM_BUSY_PIN, GPIO.IN)
    GPIO.setup(MCLK_PAUSE_PIN, GPIO.OUT)
      
  def close(self):
    '''Close all drivers'''
    self.spi.close()
    GPIO.cleanup()
  
  def __enter__(self):
    '''Enter to use 'with' construct in python'''
    return self
  
  def __exit__(self, *args, **kwargs):
    '''Exit to use 'with' construct in python'''
    self.close()

  #
  # HIGH LEVEL OPERATIONS
  #
  def configure(self, settings):
    '''Write all settings'''
    pass

  def set_addr(self, addr_start, addr_stop=None, addr_step=1):
    '''Set address'''
    # Configure stop addr if not specified 
    if addr_stop is None:
      addr_stop = addr_start

    # Assert that addrs are valid
    assert(addr_start >= 0 and addr_start < 2**16)
    assert(addr_stop >= 0 and addr_stop < 2**16)
    assert(addr_step >= 0 and addr_step < 2**16)

    # Get register value to program
    val = (addr_step << 32) | (addr_stop << 16) | addr_start

    # Write to address register
    self.write_reg(17, val)

  def test_read(self):
    '''Test READ operation'''
    self.write_reg(REG_CMD, OP_TEST_READ)
    return self.read_reg(REG_READ)

  #
  # MEDIUM LEVEL OPERATIONS
  #
  def read_diag(self):
    '''Read diagnostics register'''
    return self.read_reg(REG_STATE)

  def read_fsm_state(self):
    '''Read FSM state register when mclk is paused'''
    return self.read_reg(REG_STATE)

  '''Write to programming configuration register'''
  def write_prog_cfg_bits(self, rangei, prog):
    # TODO
    self.write_reg(rangei, prog)

  '''Write to miscellaneous configuration register'''
  def write_misc_cfg_bits(self, misc):
    # TODO
    self.write_reg(REG_MISC, misc)

  #
  # LOW LEVEL OPERATIONS
  #
  def read_reg(self, reg):
    '''Read val from register reg'''
    # Assert that reg is valid
    assert(reg >= 0 and reg < 32)

    # Message to read from register
    msg = reg << 162

    # Transfer message and print bytes received on mosi
    return int.from_bytes(self.spi.xfer(list(bytearray(msg.to_bytes(21, "big"))))[:-20], "big")

  def write_reg(self, reg, val):
    '''Write val to register reg'''
    # Assert that reg is valid
    assert(reg >= 0 and reg < 32)

    # Assert that val is an int
    assert(isinstance(val, int))

    # Message to read from register
    msg = (1 << 167) | (reg << 162) | (val << 2)

    # Transfer message and print bytes received on mosi
    self.spi.xfer(list(bytearray(msg.to_bytes(21, "big"))))

#
# TOP-LEVEL EXAMPLE
#
if __name__ == '__main__':
  with EMBERDriver("config.json") as ember:
    print("Received:", "{160:b}".format(ember.read_reg(31)))
