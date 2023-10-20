# Import Python libraries
import copy, json, time, warnings
from math import ceil, log2

# Warnings become errors
warnings.filterwarnings("error")

# Raspberry Pi GPIO pin mappings
RRAM_BUSY_PIN = 7
MCLK_PAUSE_PIN = 25
CLKSEL_PIN = None

# FTDI device locator
FTDI_URL = "ftdi://ftdi:2232h/1"

# Register indices
REG_MISC = 16
REG_ADDR = 17
REG_WRITE = 18
REG_CMD = 22
REG_STATE = 23
REG_DIAG = 24
REG_READ = 25
REG_DIAG2 = 29
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
OP_READ_ENERGY = 7

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

class EMBERWriteFailure(EMBERException):
  """Exception produced by the EMBERDriver class on write failure"""
  def __init__(self, msg):
      super().__init__(msg)

class EMBERDriver(object):
  """Class to interface with EMBER chip"""
  def __init__(self, chip, settings, test_conn=True, debug=False):
    """Initialize and configure SPI/GPIO interfaces"""
    # Load settings
    self.addr = 0
    self.chip = chip
    self.debug = debug
    if isinstance(settings, str):
      with open(settings) as settings_file:
        self.settings = json.load(settings_file)
      self.di_init_mask = self.settings["di_init_mask"]
      self.level_settings = copy.deepcopy(self.settings["level_settings"])
    self.last_misc, self.last_prog = None, None

    # Setup SPI and GPIO
    if self.settings["spi_mode"] == "spidev":
      # Import spidev and Raspberry Pi GPIO drivers
      from spidev import SpiDev
      import RPi.GPIO as GPIO

      # Create SPI device
      self.spi = SpiDev()
      self.spi.open(0, 0)
      self.spi.max_speed_hz = self.settings["spi_freq"]
      self.spi.mode = 1

      # Set up Raspberry Pi GPIO driver
      GPIO.setmode(GPIO.BCM)
      GPIO.setup(RRAM_BUSY_PIN, GPIO.IN)
      GPIO.setup(MCLK_PAUSE_PIN, GPIO.OUT)
    elif self.settings["spi_mode"] == "ftdi":
      # Import pyftdi SPI driver
      from pyftdi.spi import SpiController

      # Create SPI device 
      spi = SpiController()
      spi.configure(FTDI_URL)
      self.spi = spi.get_port(cs=0, freq=self.settings["spi_freq"], mode=1)

      # Get GPIO port to manage extra pins, use pin 4 as GPO, pin 5 as GPI, pin 6 as GPO (pins 0-3 are SPI)
      self.gpio = spi.get_gpio()
      self.gpio.set_direction(0x70, 0x50)
    else:
      raise EMBERException("Invalid SPI backend driver: %s" % self.settings["spi_mode"])
    
    # Initialize GPIO pin states
    self.unpause_mclk() # unpause the mclk by default
    self.slow_mode() # start in slow mode (SPI)

    # Test connection
    if test_conn:
      val = self.read_reg(REG_RAM)
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

  def __enter__(self):
    """Enter to use "with" construct in python"""
    return self
  
  def __exit__(self, *args, **kwargs):
    """Exit to use "with" construct in python"""
    self.close()
  
  def close(self):
    """Close all drivers"""
    self.mlogfile.close()
    self.plogfile.close()
    if self.settings["spi_mode"] == "spidev":
      self.spi.close()
      GPIO.cleanup()

  #
  # HIGH LEVEL OPERATIONS
  #
  def superread(self, mask=None):
    """Full-range (64-level) READ operation using 4 READs"""
    # Backup settings
    settings_bak = copy.deepcopy(self.settings)

    # Reconfigure settings and READ 4x
    self.settings["num_levels"] = 9
    for i in range(8):
      # Set level settings
      self.settings["level_settings"] = []
      for j in range(9):
        self.settings["level_settings"].append(self.level_settings[0].copy())
        self.settings["level_settings"][-1]["adc_upper_read_ref_lvl"] = min(i*8 + j, 63)

      # READ and convert partial read to superread
      reader = self.read(mask)
      # print([a["adc_upper_read_ref_lvl"] for a in self.settings["level_settings"]])
      # print(reader)
      read = [r + i*8 for r in reader]
      if i == 0:
        superread = read
      else:
        for k, r in enumerate(superread):
          if r == i*8:
            superread[k] = read[k]

    # Reset settings
    self.settings = settings_bak

    # Return superread value
    return superread
    
  def read(self, mask=None, diag=False):
    """READ operation"""
    # Commit
    self.commit_settings()

    # Execute READ command
    self.write_reg(REG_CMD, OP_READ)
    self.wait_for_idle()

    # Read values from READ registers
    num_levels = (self.settings["num_levels"] + 15) % 16 + 1 # when num_levels=0, interpret as num_levels=16
    data = []
    for i in range(ceil(log2(num_levels))):
      data.append(self.read_reg(REG_READ + i))

    # Translate to array of numbers
    data = ["{0:048b}".format(d)[::-1] for d in data][::-1] # convert to binary strings
    data = zip(*data) # transpose
    data = [int(''.join(d), base=2) for d in data] # convert from binary to array of ints
    
    # Log the READ
    self.mlogfile.write("%s,%s,%s," % (self.chip, time.time(), self.addr))
    self.mlogfile.write("MLCREAD,%s,%s\n" % (mask, ",".join([str(d) for d in data])))

    # Get diagnostics if requested 
    if diag:
      d = self.get_diagnostics()
      print("Post-READ diagnostics:", d)

    # Return data
    return data[:self.settings["bitwidth"]]

  def write(self, data, ignore_minmax=True, native=True, use_multi_addrs=False, lfsr=False, cb=False, check63=False, debug=False, diag=False):
    """Perform write-verify"""
    # Commit
    self.commit_settings()

    # Verify that data is int or valid int array and convert to int array
    num_levels = (self.settings["num_levels"] + 15) % 16 + 1 # when num_levels=0, interpret as num_levels=16
    assert(isinstance(data, int) or isinstance(data, list))
    if isinstance(data, int):
      assert(data >= 0 and data < 2**48)
      data = [int(d) for d in "{0:048b}".format(data)[::-1]] # convert to array of bits
    assert(all([d < num_levels for d in data]))

    # Debug print data
    if debug:
      print("WRITING DATA:", data)
    
    # Native mode
    if native:
      # Rotate array
      data = ["{0:04b}".format(d)[::-1] for d in data][::-1] # convert to binary strings
      data = zip(*data)
      data = [int(''.join(d), base=2) for d in data] # convert from binary to array of ints
      assert(len(data) == 4)
      print(data)

      # Write data to be written
      for i, d in enumerate(data):
        self.write_reg(REG_WRITE + i, d)
      
      # Execute WRITE command
      self.write_reg(REG_CMD, OP_WRITE + 8*use_multi_addrs + 16*lfsr + 32*cb + 64*check63)
      if not use_multi_addrs:
        self.wait_for_idle()

      # Log the WRITE
      self.mlogfile.write("%s,%s,%s," % (self.chip, time.time(), self.addr))
      self.mlogfile.write("WRITE,%s,%s\n" % (self.settings["di_init_mask"], self.settings["max_attempts"]))
    # Non-native mode: implement write-verify using other commands
    else:
      # NOTE: set_first, loop_order, and PW looping are not implemented in this function though they are in spec
      # Write levels one by one
      for i in range(num_levels):
        # Maximum number of SET/RESET loops to attempt
        for attempts in range(self.settings["max_attempts"]):
          # SET loop: returns True if done with attempt
          if debug:
            print("SET LOOP", i, "ATTEMPT", attempts)
          if self._write_set_loop(data, i, attempts, ignore_minmax, debug):
            break
          
          # RESET loop: returns True if done with attempt
          if debug:
            print("RESET LOOP", i, "ATTEMPT", attempts)
          if self._write_reset_loop(data, i, attempts, ignore_minmax, debug):
            pass
            # break # END ON SET!!!

          # If loop completes, write failed
          if attempts == (self.settings["max_attempts"] - 1) and not self.settings["ignore_failures"]:
            raise EMBERWriteFailure("Write failed on address %s" % self.addr)

    # Get diagnostics if requested 
    if diag:
      d = self.get_diagnostics()
      print("Post-WRITE diagnostics:", d)
      return d

  def _write_set_loop(self, data, i, attempts, ignore_minmax=True, debug=False):
    """Do SET loop for write-verify and return True if done with entire set process"""
    # Get settings for level i
    s = self.level_settings[i]

    # Start with mask based on which cells need to be targeted
    mask = int(''.join(['1' if d == i else '0' for d in data])[::-1], base=2) & self.settings["di_init_mask"]
    if debug:
      print("MASK:", mask)
    if mask == 0:
      return True # Done with level if no cells at level need to be targeted

    # Loop through pulse magnitude (up to max_attempts times)
    for loop_attempts in range(self.settings["max_attempts"]):
      for vwl in range(s["wl_dac_set_lvl_start"], s["wl_dac_set_lvl_stop"]+1, s["wl_dac_set_lvl_step"]):
        for vbl in range(s["bl_dac_set_lvl_start"], s["bl_dac_set_lvl_stop"]+1, s["bl_dac_set_lvl_step"]):
          # Mask bits below threshold according to READ value
          mask &= ~self.single_read(i, "lower_write", mask, ignore_minmax)
          if debug:
            print("MASK:", mask)
          
          # If fully masked, do not apply pulse
          if mask == 0:
            # If fully masked, at least one attempt complete, and no previous SET pulses on this attempt, then we are done with this level
            if (attempts > 0) and (loop_attempts == 0) and (vwl == s["wl_dac_set_lvl_start"]) and (vbl == s["bl_dac_set_lvl_start"]):
              return True # Done with level
            else:
              return False # Not done with level (but done with the SET loop)
          # If not fully masked, apply SET pulse to unmasked bits
          else:
            self.set_pulse(vwl, vbl, self.settings["pw_set_cycle_exp"], self.settings["pw_set_cycle_mantissa"], mask)
      # self.cycle(mask)

    # If loop completes, write failed
    if not self.settings["ignore_failures"]:
      raise EMBERWriteFailure("Write failed during SET loop on address %s" % self.addr)

  def _write_reset_loop(self, data, i, attempts, ignore_minmax=True, debug=False):
    # Get settings for level i
    s = self.level_settings[i]

    # Start with mask based on which cells need to be targeted
    mask = int(''.join(['1' if d == i else '0' for d in data])[::-1], base=2) & self.settings["di_init_mask"]
    if debug:
      print("MASK:", mask)
    if mask == 0:
      return True # Done with level if no cells at level need to be targeted

    # Loop through pulse magnitude (up to max_attempts times)
    for loop_attempts in range(self.settings["max_attempts"]):
      for vwl in range(s["wl_dac_rst_lvl_start"], s["wl_dac_rst_lvl_stop"]+1, s["wl_dac_rst_lvl_step"]):
        for vsl in range(s["sl_dac_rst_lvl_start"], s["sl_dac_rst_lvl_stop"]+1, s["sl_dac_rst_lvl_step"]):
          # Mask bits according to READ value
          mask &= self.single_read(i, "upper_write", mask, ignore_minmax)
          if debug:
            print("MASK:", mask)

          # If fully masked, do not apply pulse
          if (mask == 0):
            # If fully masked, at least one attempt complete, and no previous RESET pulses on this attempt, then we are done
            if (attempts > 0) and (loop_attempts == 0) and (vwl == s["wl_dac_rst_lvl_start"]) and (vsl == s["sl_dac_rst_lvl_start"]):
              return True # Done with level
            else:
              return False # Not done with level (but done with the RESET loop)
          # If not fully masked, apply RESET pulse to unmasked bits
          else:
            self.reset_pulse(vwl, vsl, self.settings["pw_rst_cycle_exp"], self.settings["pw_rst_cycle_mantissa"], mask)
      self.cycle(mask)

    # If loop completes, write failed
    if not self.settings["ignore_failures"]:
      raise EMBERWriteFailure("Write failed during RESET loop on address %s" % self.addr)

  def cycle(self, mask=None, use_multi_addrs=False):
    """CYCLE operation"""
    # Set mask
    self.settings["di_init_mask"], old_mask = self.di_init_mask if mask is None else mask, self.settings["di_init_mask"]

    # Execute CYCLE command (alternating SET/RESETs)
    self.write_reg(REG_CMD, OP_CYCLE + 8*use_multi_addrs)
    self.wait_for_idle()

    # Log the CYCLE
    self.mlogfile.write("%s,%s,%s," % (self.chip, time.time(), self.addr))
    self.mlogfile.write("CYCLE,%s,%s\n" % (self.settings["di_init_mask"], self.settings["max_attempts"]))

    # Reset mask
    self.settings["di_init_mask"] = old_mask

  def read_energy(self, bpc=1):
    """Read energy measurement"""
    # Select address range for checkerboard
    self.set_addr(100 + bpc*100, 148 + bpc*100)

    # Set number of levels
    self.settings["num_levels"] = bpc
    self.commit_settings()

    # Send "read energy" command (which will loop forever, but make non-blocking)
    self.write_reg(REG_CMD, OP_READ_ENERGY)

  def get_diagnostics(self):
    """Get diagnostics from registers"""
    # Get diagnostics from two diagnostic registers
    diag = self.read_reg(REG_DIAG)
    diag2 = self.read_reg(REG_DIAG2)

    # Diagnostics dictionary
    d = {}

    # Extract diagnostics 1
    d["successes"] = diag & ((1 << 32) - 1)
    diag >>= 32
    d["failures"] = diag & ((1 << 32) - 1)
    diag >>= 32
    d["reads"] = diag & ((1 << 32) - 1)
    diag >>= 32
    d["sets"] = diag & ((1 << 32) - 1)
    diag >>= 32
    d["resets"] = diag & ((1 << 32) - 1)

    # Extract diagnostics 2
    d["cycles"] = diag2 & ((1 << 64) - 1)
    diag2 >>= 64
    d["read_bits"] = diag2 & ((1 << 32) - 1)
    diag2 >>= 32
    d["set_bits"] = diag2 & ((1 << 32) - 1)
    diag2 >>= 32
    d["reset_bits"] = diag2 & ((1 << 32) - 1)

    # Return diagnostics dictionary
    return d

  #
  # MEDIUM LEVEL OPERATIONS
  #
  def set_pulse(self, vwl=None, vbl=None, pw_exp=None, pw_mantissa=None, mask=None, use_multi_addrs=False):
    """Perform a SET operation."""
    # Backup settings
    settings_bak = copy.deepcopy(self.settings)

    # Get parameters
    self.settings["set_first"] = 1
    mask = self.settings["di_init_mask"] = self.di_init_mask if mask is None else mask
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
    self.write_reg(REG_CMD, OP_TEST_PULSE + 8*use_multi_addrs)
    if not use_multi_addrs:
      self.wait_for_idle()

    # Log the pulse
    self.mlogfile.write("%s,%s,%s," % (self.chip, time.time(), self.addr))
    self.mlogfile.write("SET,%s,%s,%s,0,%s\n" % (mask, vwl, vbl, pw))

    # Reset settings
    if not use_multi_addrs:
      self.settings = settings_bak

  def reset_pulse(self, vwl=None, vsl=None, pw_exp=None, pw_mantissa=None, mask=None, use_multi_addrs=False):
    """Perform a RESET operation."""
    # Backup settings
    settings_bak = copy.deepcopy(self.settings)

    # Get parameters
    self.settings["set_first"] = 0
    mask = self.settings["di_init_mask"] = self.di_init_mask if mask is None else mask
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
    self.write_reg(REG_CMD, OP_TEST_PULSE + 8*use_multi_addrs)
    if not use_multi_addrs:
      self.wait_for_idle()

    # Log the pulse
    self.mlogfile.write("%s,%s,%s," % (self.chip, time.time(), self.addr))
    self.mlogfile.write("RESET,%s,%s,0,%s,%s\n" % (mask, vwl, vsl, pw))

    # Reset settings
    if not use_multi_addrs:
      self.settings = settings_bak

  def commit_settings(self):
    """Write all settings"""
    # Determine value of miscellaneous register
    misc = 0
    for field, width in MISC_FIELDS:
      try:
        if field != "max_attempts":
          assert(self.settings[field] >= 0 and self.settings[field] < 2**width)
      except AssertionError as e:
        print("Field, width, value:", field, width, self.settings[field])
        raise e
      misc <<= width
      if field != "max_attempts":
        misc |= self.settings[field]
      else:
        misc |= min(255, self.settings[field])
    
    # Update miscellaneous register if there was a change from previous commit
    if self.last_misc != misc:
      self.write_reg(REG_MISC, misc)
    
    # Remember last miscellaneous register value
    self.last_misc = copy.deepcopy(misc)

    # Write to level setting registers
    num_levels = (self.settings["num_levels"] + 15) % 16 + 1 # when num_levels=0, interpret as num_levels=16
    assert(len(self.settings["level_settings"]) >= num_levels)
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
    self.last_prog = copy.deepcopy(self.settings["level_settings"])
    
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

  def single_read(self, level=0, ref="upper_read", mask=None, ignore_minmax=True):
    """Test READ operation"""
    # Backup settings
    settings_bak = copy.deepcopy(self.settings)

    # Copy level settings from desired level
    self.settings["level_settings"][0] = self.level_settings[level].copy()

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
    
    # Set mask and set_rst appropriately
    mask = self.settings["di_init_mask"] = mask if mask is not None else self.di_init_mask
    self.commit_settings()

    # Everything is always above 0
    if (self.settings["level_settings"][0]["adc_upper_read_ref_lvl"] == 0) and ignore_minmax:
      # Reset settings and return mask
      self.settings = settings_bak
      return mask
 
    # Everything is always below 63
    if (self.settings["level_settings"][0]["adc_upper_read_ref_lvl"] == 63) and ignore_minmax:
      # Reset settings and return 0
      self.settings = settings_bak
      return 0

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

    # Reset settings
    self.settings = settings_bak

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

    # Transfer message and collect miso values to read register using appropriate driver
    xfer = lambda m: int.from_bytes(self.spi.xfer(m)[1:-1], "big") if self.settings["spi_mode"] == "spidev" else int.from_bytes(self.spi.exchange(m, duplex=True)[1:], "big") >> 7
    val = xfer(list(bytearray(msg.to_bytes(21, "big"))) + [0])

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

    # Transfer message to write register using appropriate driver
    xfer = self.spi.xfer if self.settings["spi_mode"] == "spidev" else lambda m: self.spi.exchange(m, duplex=True)
    xfer(list(bytearray(msg.to_bytes(21, "big"))) + [0]*2)

  def wait_for_idle(self, debug=False):
    """Wait until rram_busy signal is low, indicating that EMBER is idle"""
    # Write to dummy register to keep sclk going
    if self.settings["spi_mode"] == "spidev":
      while GPIO.input(RRAM_BUSY_PIN):
        val = self.read_reg(REG_STATE)
        if debug:
          print("At address:", (val >> (5 + 5 + 1 + 1 + 1 + 5 + 1 + 6 + 48 + 4 + 1 + 6)) & ((1 << 16) - 1))
      while self.read_reg(REG_RAM) != 0x52414D:
        continue
    elif self.settings["spi_mode"] == "ftdi":
      while self.gpio.read() & 0x20:
        val = self.read_reg(REG_STATE)
        if debug:
          print("At address:", (val >> (5 + 5 + 1 + 1 + 1 + 5 + 1 + 6 + 48 + 4 + 1 + 6)) & ((1 << 16) - 1))
      while self.read_reg(REG_RAM) != 0x52414D:
        continue
    else:
      raise EMBERException("Invalid SPI backend driver: %s" % self.settings["spi_mode"])

  def pause_mclk(self):
    """Pause main clock"""
    if self.settings["spi_mode"] == "spidev":
      GPIO.output(MCLK_PAUSE_PIN, True)
    elif self.settings["spi_mode"] == "ftdi":
      self.gpio.write(0x10)
    else:
      raise EMBERException("Invalid SPI backend driver: %s" % self.settings["spi_mode"])

  def unpause_mclk(self):
    """Unpause main clock"""
    if self.settings["spi_mode"] == "spidev":
      GPIO.output(MCLK_PAUSE_PIN, False)
    elif self.settings["spi_mode"] == "ftdi":
      self.gpio.write(0x00)
    else:
      raise EMBERException("Invalid SPI backend driver: %s" % self.settings["spi_mode"])
    
  def fast_mode(self):
    """Select fast clock"""
    if self.settings["spi_mode"] == "spidev":
      GPIO.output(CLKSEL_PIN, False)
    elif self.settings["spi_mode"] == "ftdi":
      self.gpio.write(0x40)
    else:
      raise EMBERException("Invalid SPI backend driver: %s" % self.settings["spi_mode"])

  def slow_mode(self):
    """Select slow clock"""
    if self.settings["spi_mode"] == "spidev":
      GPIO.output(CLKSEL_PIN, False)
    elif self.settings["spi_mode"] == "ftdi":
      self.gpio.write(0x00)
    else:
      raise EMBERException("Invalid SPI backend driver: %s" % self.settings["spi_mode"])

#
# TOP-LEVEL EXAMPLE
#
if __name__ == "__main__":
  with EMBERDriver("CHIP1", "settings/config.json", test_conn=True) as ember:
    pass
