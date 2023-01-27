# Import Python libraries
import json, time, warnings
from math import ceil, log2

# Import external libraries
import RPi.GPIO as GPIO
from spidev import SpiDev


# Warnings become errors
warnings.filterwarnings("error")


# Pin mappings
RRAM_BUSY_PIN = 24
MCLK_PAUSE_PIN = 25

# Register indices
REG_MISC = 16
REG_ADDR = 17
REG_WRITE = 18
REG_CMD = 22
REG_STATE = 23
REG_DIAG = 24
REG_READ = 25
REG_NONE = 30
REG_RAM = 31

# FSM opcodes
OP_TEST_PULSE = 0
OP_TEST_READ = 1
OP_TEST_CPULSE = 2
OP_CYCLE = 3
OP_READ = 4
OP_WRITE = 5
OP_REFRESH = 6

# Miscellaneous settings register fields
MISC_FIELDS = [
  ("post_read_setup_cycles", 6),
  ("step_write_setup_cycles", 6),
  ("step_read_setup_cycles", 6),
  ("write_to_init_read_setup_cycles", 6),
  ("read_to_init_write_setup_cycles", 6),
  ("idle_to_init_read_setup_cycles", 6),
  ("idle_to_init_write_setup_cycles", 6),

  ("all_dacs_on", 1),
  ("ignore_failures", 1),
  ("di_init_mask", 48),

  ("set_first", 1),

  ("pw_rst_cycle_exp", 3),
  ("pw_rst_cycle_mantissa", 5),
  ("wl_dac_rst_lvl_cycle", 8),
  ("sl_dac_rst_lvl_cycle", 5),

  ("pw_set_cycle_exp", 3),
  ("pw_set_cycle_mantissa", 5),
  ("wl_dac_set_lvl_cycle", 8),
  ("bl_dac_set_lvl_cycle", 5),

  ("num_levels", 4),
  ("use_ecc", 1),
  ("max_attempts", 8)
]

# Level settings register fields
PROG_FIELDS = [
  ("loop_order_rst", 3),
  ("pw_rst_step_exp", 3),
  ("pw_rst_step_mantissa", 5),
  ("pw_rst_stop_exp", 3),
  ("pw_rst_stop_mantissa", 5),
  ("pw_rst_start_exp", 3),
  ("pw_rst_start_mantissa", 5),
  ("wl_dac_rst_lvl_step", 8),
  ("wl_dac_rst_lvl_stop", 8),
  ("wl_dac_rst_lvl_start", 8),
  ("sl_dac_rst_lvl_step", 5),
  ("sl_dac_rst_lvl_stop", 5),
  ("sl_dac_rst_lvl_start", 5),

  ("loop_order_set", 3),
  ("pw_set_step_exp", 3),
  ("pw_set_step_mantissa", 5),
  ("pw_set_stop_exp", 3),
  ("pw_set_stop_mantissa", 5),
  ("pw_set_start_exp", 3),
  ("pw_set_start_mantissa", 5),
  ("wl_dac_set_lvl_step", 8),
  ("wl_dac_set_lvl_stop", 8),
  ("wl_dac_set_lvl_start", 8),
  ("bl_dac_set_lvl_step", 5),
  ("bl_dac_set_lvl_stop", 5),
  ("bl_dac_set_lvl_start", 5),
  
  ("adc_upper_write_ref_lvl", 6),
  ("adc_lower_write_ref_lvl", 6),
  ("adc_upper_read_ref_lvl", 6),
  ("adc_read_dac_lvl", 4),
  ("adc_clamp_ref_lvl", 6)
]


class EMBERException(Exception):
  """Exception produced by the EMBERDriver class"""
  def __init__(self, msg):
      super().__init__(msg)

class EMBERDriver(object):
  """Class to interface with EMBER chip"""
  def __init__(self, chip, settings, test_conn=True, debug=True):
    """Initialize and configure SPI/GPIO interfaces"""
    # Load settings
    self.addr = 0
    self.chip = chip
    self.debug = debug
    if isinstance(settings, str):
      with open(settings) as settings_file:
        self.settings = json.load(settings_file)
      self.level_settings = self.settings["level_settings"]
    self.last_misc, self.last_prog = None, None

    # Create SPI device
    self.spi = SpiDev()
    self.spi.open(0, 0)
    self.spi.cshigh = True
    self.spi.max_speed_hz = self.settings["spi_freq"]
    self.spi.mode = 1

    # Test connection
    if test_conn:
      val = self.read_reg(31)
      if val == 0x52414D:
        print("SPI connection detected!")
      else:
        raise EMBERException("No SPI connection detected: %s" % val)

    # Commit settings
    self.commit_settings()

    # Initialize profiling
    self.prof = {"READs": 0, "SETs": 0, "RESETs": 0, "CELL_READs": 0, "CELL_SETs": 0, "CELL_RESETs": 0}

    # Initialize RRAM logging
    self.mlogfile = open(self.settings["master_log_file"].replace(".log", "." + str(int(time.time())) + ".log"), "a")
    self.plogfile = open(self.settings["prog_log_file"].replace(".log", "." + str(int(time.time())) + ".log"), "a")
    
    # Set up Raspberry Pi GPIO driver
    GPIO.setmode(GPIO.BCM)
    GPIO.setup(RRAM_BUSY_PIN, GPIO.IN)
    GPIO.setup(MCLK_PAUSE_PIN, GPIO.OUT)
      
  def __enter__(self):
    """Enter to use "with" construct in python"""
    return self
  
  def __exit__(self, *args, **kwargs):
    """Exit to use "with" construct in python"""
    self.close()
  
  def close(self):
    """Close all drivers"""
    self.spi.close()
    GPIO.cleanup()
    self.mlogfile.close()
    self.plogfile.close()

  #
  # HIGH LEVEL OPERATIONS
  #
  def read(self):
    """READ operation"""
    # Reset level settings
    self.settings["level_settings"] = self.level_settings
    self.commit_settings()

    # Execute READ command
    self.write_reg(REG_CMD, OP_READ)
    self.wait_for_idle()

    # Read values from READ registers
    num_levels = (self.settings["num_levels"] + 15) % 16 + 1 # when num_levels=0, interpret as num_levels=16
    data = []
    for i in range(ceil(log2(num_levels))):
      data.append(self.read_reg(REG_READ + i))

    # If 1bpc, return data as is, otherwise translate to array of numbers
    if num_levels == 2:
      return data[0]
    else:
      data = ["{0:048b}".format(d) for d in data] # convert to binary strings
      data = zip(*data) # transpose
      data = [int(''.join(d), base=2) for d in data] # convert from binary to array of ints
      return data

  def write(self, data):
    """Perform write-verify"""
    # Verify that data is int or valid int array and convert to int array
    num_levels = (self.settings["num_levels"] + 15) % 16 + 1 # when num_levels=0, interpret as num_levels=16
    assert(isinstance(data, int) or isinstance(data, list))
    if isinstance(data, int):
      assert(data >= 0 and data < 2**48)
      data = [int(d) for d in "{0:048b}".format(data)] # convert to array of bits
    assert(all([d < num_levels for d in data]))
    
    # NOTE: set_first, loop_order, and PW looping are not implemented in this function though they are in spec
    # Write levels one by one
    for i in range(num_levels):
      # Maximum number of SET/RESET loops to attempt
      for attempts in range(self.settings["max_attempts"]):
        # SET loop: returns True if done with attempt
        if self._write_set_loop(data, i, attempts):
          break
        
        # RESET loop: returns True if done with attempt
        if self._write_reset_loop(data, i, attempts):
          break

  def _write_set_loop(self, data, i, attempts):
    """Do SET loop for write-verify and return True if done with entire set process"""
    # Get settings for level i
    s = self.level_settings[i]

    # Start with mask based on which cells need to be targeted
    mask = int(''.join(['1' if d == i else '0' for d in data]), base=2)
    if mask == 0:
      return True # Done with level if no cells need to be targeted

    # Loop through pulse magnitude
    for vwl in range(s["wl_dac_set_lvl_start"], s["wl_dac_set_lvl_stop"]+1, s["wl_dac_set_lvl_step"]):
      for vbl in range(s["bl_dac_set_lvl_start"], s["bl_dac_set_lvl_stop"]+1, s["bl_dac_set_lvl_step"]):
        # Mask bits below threshold according to READ value
        mask &= (~self.single_read(i, "lower_write", mask) & 0xFFFFFFFFFFFF)
        
        # If fully masked, do not apply pulse
        if mask == 0:
          # If fully masked, at least one attempt complete, and no previous SET pulses on this attempt, then we are done with this level
          if (attempts > 0) and (vwl == s["wl_dac_set_lvl_start"]) and (vbl == s["bl_dac_set_lvl_start"]):
            return True # Done with level
          else:
            return False # Not done with level (but done with the SET loop)
        # If not fully masked, apply SET pulse to unmasked bits
        else:
          self.set_pulse(vwl, vbl, self.settings["pw_set_cycle_exp"], self.settings["pw_set_cycle_mantissa"], mask)

  def _write_reset_loop(self, data, i, attempts):
    # Get settings for level i
    s = self.level_settings[i]

    # Start with mask based on which cells need to be targeted
    mask = int(''.join(['1' if d == i else '0' for d in data]), base=2)
    if mask == 0:
      return True # Done with level if no cells need to be targeted

    # Loop through pulse magnitude
    for vwl in range(s["wl_dac_rst_lvl_start"], s["wl_dac_rst_lvl_stop"]+1, s["wl_dac_rst_lvl_step"]):
      for vsl in range(s["sl_dac_rst_lvl_start"], s["sl_dac_rst_lvl_stop"]+1, s["sl_dac_rst_lvl_step"]):
        # Mask bits according to READ value
        mask &= self.single_read(i, "upper_write", mask)

        # If fully masked, do not apply pulse
        if (mask == 0):
          # If fully masked, at least one attempt complete, and no previous RESET pulses on this attempt, then we are done
          if (attempts > 0) and (vwl == s["wl_dac_rst_lvl_start"]) and (vsl == s["sl_dac_rst_lvl_start"]):
            return True # Done with level
          else:
            return False # Not done with level (but done with the RESET loop)
        # If not fully masked, apply RESET pulse to unmasked bits
        else:
          self.reset_pulse(vwl, vsl, self.settings["pw_rst_cycle_exp"], self.settings["pw_rst_cycle_mantissa"], mask)

  def cycle(self):
    """CYCLE operation"""
    # Execute CYCLE command (alternating SET/RESETs)
    self.write_reg(REG_CMD, OP_CYCLE)
    self.wait_for_idle()

  #
  # MEDIUM LEVEL OPERATIONS
  #
  def set_pulse(self, vwl=None, vbl=None, pw_exp=None, pw_mantissa=None, mask=None):
    """Perform a SET operation."""
    # Get parameters
    self.settings["set_first"] = 1
    mask = self.settings["di_init_mask"] = self.settings["di_init_mask"] if mask is None else mask
    vwl = self.settings["wl_dac_set_lvl_cycle"] = self.settings["wl_dac_set_lvl_cycle"] if vwl is None else vwl
    vbl = self.settings["bl_dac_set_lvl_cycle"] = self.settings["bl_dac_set_lvl_cycle"] if vbl is None else vbl
    self.settings["pw_set_cycle_exp"] = self.settings["pw_set_cycle_exp"] if pw_exp is None else pw_exp
    self.settings["pw_set_cycle_mantissa"] = self.settings["pw_set_cycle_mantissa"] if pw_mantissa is None else pw_mantissa
    pw = self.settings["pw_set_cycle_mantissa"] << self.settings["pw_set_cycle_exp"]

    # Increment the number of SETs
    self.prof["SETs"] += 1
    self.prof["CELL_SETs"] += bin(mask).count("1")

    # Commit settings and pulse run test pulse (pulses VWL)
    self.commit_settings()
    self.write_reg(REG_CMD, OP_TEST_PULSE)
    self.wait_for_idle()

    # Log the pulse
    self.mlogfile.write("%s,%s,%s," % (self.chip, time.time(), self.addr))
    self.mlogfile.write("SET,%s,%s,%s,0,%s\n" % (mask, vwl, vbl, pw))

  def reset_pulse(self, vwl=None, vsl=None, pw_exp=None, pw_mantissa=None, mask=None):
    """Perform a RESET operation."""
    # Get parameters
    self.settings["set_first"] = 0
    mask = self.settings["di_init_mask"] = self.settings["di_init_mask"] if mask is None else mask
    vwl = self.settings["wl_dac_rst_lvl_cycle"] = self.settings["wl_dac_rst_lvl_cycle"] if vwl is None else vwl
    vsl = self.settings["sl_dac_rst_lvl_cycle"] = self.settings["sl_dac_rst_lvl_cycle"] if vsl is None else vsl
    self.settings["pw_rst_cycle_exp"] = self.settings["pw_rst_cycle_exp"] if pw_exp is None else pw_exp
    self.settings["pw_rst_cycle_mantissa"] = self.settings["pw_rst_cycle_mantissa"] if pw_mantissa is None else pw_mantissa
    pw = self.settings["pw_rst_cycle_mantissa"] << self.settings["pw_rst_cycle_exp"]

    # Increment the number of SETs
    self.prof["RESETs"] += 1
    self.prof["CELL_RESETs"] += bin(mask).count("1")

    # Commit settings and pulse run test pulse (pulses VWL)
    self.commit_settings()
    self.write_reg(REG_CMD, OP_TEST_PULSE)
    self.wait_for_idle()

    # Log the pulse
    self.mlogfile.write("%s,%s,%s," % (self.chip, time.time(), self.addr))
    self.mlogfile.write("RESET,%s,%s,0,%s,%s\n" % (mask, vwl, vsl, pw))

  def commit_settings(self):
    """Write all settings"""
    # Determine value of miscellaneous register
    misc = 0
    for field, width in MISC_FIELDS:
      try:
        assert(self.settings[field] >= 0 and self.settings[field] < 2**width)
      except AssertionError as e:
        print("Field, width, value:", field, width, self.settings[field])
        raise e
      misc <<= width
      misc |= self.settings[field]
    
    # Update miscellaneous register if there was a change from previous commit
    if self.last_misc != misc:
      self.write_reg(REG_MISC, misc)
    
    # Remember last miscellaneous register value
    self.last_misc = misc

    # Write to level setting registers
    num_levels = (self.settings["num_levels"] + 15) % 16 + 1 # when num_levels=0, interpret as num_levels=16
    assert(num_levels >= len(self.settings["level_settings"]))
    for rangei in range(num_levels):
      # Skip if level setting is unchanged from previous commit
      try:
        if self.settings["level_settings"][rangei] == self.last_prog[rangei]:
          continue
      except (TypeError, IndexError):
        pass

      # Determine value of programming register
      prog = 0
      for field, width in PROG_FIELDS:
        assert(self.settings["level_settings"][rangei][field] >= 0 and self.settings["level_settings"][rangei][field] < 2**width)
        prog <<= width
        prog |= self.settings["level_settings"][rangei][field]
      self.write_reg(rangei, prog)
    
    # Remember last set of level settings
    self.last_prog = self.settings["level_settings"]
    
  def set_addr(self, addr_start, addr_stop=None, addr_step=1):
    """Set address"""
    # Configure stop addr if not specified 
    if addr_stop is None:
      addr_stop = addr_start

    # Assert that addr sizes are valid
    assert(addr_start >= 0 and addr_start < 2**16)
    assert(addr_stop >= 0 and addr_stop < 2**16)
    assert(addr_step >= 0 and addr_step < 2**16)

    # Get register value to program
    val = (addr_step << 32) | (addr_stop << 16) | addr_start

    # Write to address register
    self.write_reg(REG_ADDR, val)

    # Update address field
    self.addr = addr_start

  def single_read(self, level=0, ref="upper_read", mask=None):
    """Test READ operation"""
    # Copy level settings from desired level
    self.settings["level_settings"][0] = self.level_settings[level]

    # Use READ operation
    if ref == "upper_read":
      self.settings["level_settings"][0]["adc_upper_read_ref_lvl"] = self.level_settings[level]["adc_upper_read_ref_lvl"]
    elif ref == "lower_read":
      if level == 0:
        self.settings["level_settings"][0]["adc_upper_read_ref_lvl"] = 0
      else:
        self.settings["level_settings"][0]["adc_upper_read_ref_lvl"] = self.level_settings[level-1]["adc_upper_read_ref_lvl"]
    elif ref == "upper_write":
      self.settings["level_settings"][0]["adc_upper_read_ref_lvl"] = self.level_settings[level]["adc_upper_write_ref_lvl"]
    elif ref == "lower_write":
      self.settings["level_settings"][0]["adc_upper_read_ref_lvl"] = self.level_settings[level]["adc_lower_write_ref_lvl"]
    else:
      raise EMBERException("Invalid read ref: %s" % ref)
    
    # Set mask appropriately
    mask = self.settings["di_init_mask"] = mask if mask is not None else self.settings["di_init_mask"]
    self.commit_settings()

    # Increment the number of READs
    self.prof["READs"] += 1
    self.prof["CELL_READs"] += bin(mask).count("1")

    # Execute test READ operation
    self.write_reg(REG_CMD, OP_TEST_READ)
    self.wait_for_idle()

    # Read value from READ register
    read = self.read_reg(REG_READ)

    # Log the pulse
    self.mlogfile.write("%s,%s,%s," % (self.chip, time.time(), self.addr))
    self.mlogfile.write("READ,%s,%s,%s,%s,\n" % (mask, level, self.settings["level_settings"][0]["adc_upper_read_ref_lvl"], read))

    # Return READ value
    return read

  #
  # LOW LEVEL OPERATIONS
  #
  def read_reg(self, reg):
    """Read val from register reg"""
    # Assert that reg is valid
    assert(reg >= 0 and reg < 32)

    # Message to read from register
    msg = reg << 162

    # Transfer message and collect miso values to read register
    val = int.from_bytes(self.spi.xfer(list(bytearray(msg.to_bytes(21, "big"))) + [0])[1:-1], "big")

    # Debug print out
    if self.debug:
      print("Read", val, "from reg", reg)

    # Return value
    return val

  def write_reg(self, reg, val):
    """Write val to register reg"""
    # Assert that reg is valid
    assert(reg >= 0 and reg < 32)

    # Assert that val is an int
    assert(isinstance(val, int))

    # Message to write to register
    msg = (1 << 167) | (reg << 162) | (val << 2)

    # Debug print out
    if self.debug:
      print("Write", val, "to reg", reg)

    # Transfer message to write register
    self.spi.xfer(list(bytearray(msg.to_bytes(21, "big"))) + [0])

  def wait_for_idle(self):
    """Wait until rram_busy signal is low, indicating that EMBER is idle"""
    while GPIO.input(RRAM_BUSY_PIN):
      # Write to dummy register to keep sclk going (TODO: transfer one byte instead)        
      self.write_reg(REG_NONE, 0)

  def pause_mclk(self, delay=0):
    """Pause main clock"""
    GPIO.output(MCLK_PAUSE_PIN, True)
    time.sleep(delay)

  def unpause_mclk(self, delay=0):
    """Unpause main clock"""
    GPIO.output(MCLK_PAUSE_PIN, False)
    time.sleep(delay)
    
#
# TOP-LEVEL EXAMPLE
#
if __name__ == "__main__":
  with EMBERDriver("CHIP1", "settings/config.json", test_conn=True) as ember:
    # Enable activity in chip
    ember.unpause_mclk()

    # Pre-read
    reads = []
    for addr in range(200, 248):
      ember.set_addr(addr)
      ember.read_reg(REG_ADDR)
      reads.append(ember.single_read(mask=0xffffffffffff))
    for num in reads:
      print("{0:048b}".format(num))

    # Form in checkerboard
    for addr in range(200, 248):
      ember.set_addr(addr)
      ember.read_reg(REG_ADDR)
      if addr % 2 == 0:
        ember.set_pulse(mask=0x555555555555)
        # ember.set_pulse(mask=0x4)
      else:
        ember.set_pulse(mask=0xaaaaaaaaaaaa)
        # ember.set_pulse(mask=0x2)

    # Read checkerboard and following cells
    reads = []
    for addr in range(200, 248):
      ember.set_addr(addr)
      ember.read_reg(REG_ADDR)
      reads.append(ember.single_read(mask=0xffffffffffff))
    for num in reads:
      print("{0:048b}".format(num))
