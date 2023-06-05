"""Script to perform SET/RESET energy measurement on a chip while scrolling across addresses"""
import argparse
import time
from ember import EMBERDriver
from fluke8808a import Fluke8808A
from keithley2600 import Keithley2600
from keithley2420 import Keithley2420

# Get arguments
parser = argparse.ArgumentParser(description="Perform SET/RESET energy measurement while address scrolling.")
parser.add_argument("chipname", help="chip name for logging")
parser.add_argument("outfile", help="file to output to")
parser.add_argument("--config", type=str, default="settings/form.json", help="config file")
parser.add_argument("--start-addr", type=int, default=0, help="start address")
parser.add_argument("--end-addr", type=int, default=65536, help="end address")
parser.add_argument("--step-addr", type=int, default=1, help="address stride")
parser.add_argument("--reset", action="store_true",help="do RESET instead of SET")
args = parser.parse_args()

# Initialize EMBER system and open outfile
with EMBERDriver(args.chipname, args.config) as ember, \
     open(args.outfile, "a") as outfile, \
     Fluke8808A("/dev/ttyUSB0") as vdd, \
     Fluke8808A("/dev/ttyUSB1") as vdd_dac, \
     Keithley2420("/dev/ttyUSB2") as vsa:
  # Set up Keithley SMUs
  k = Keithley2600("ASRL/dev/ttyUSB3::INSTR")
  vddio = k.smua
  vddio_dac = k.smub

  # Set mask
  ember.settings["di_init_mask"] = 0

  # Set addresses to scroll across
  ember.set_addr(args.start_addr, args.end_addr-1, args.step_addr)

  # Start SET/RESET loop
  ember.set_pulse(use_multi_addrs=True)

  # Test measurement
  print([vdd.measure(), vdd_dac.measure(), vsa.measure(), vddio.measure.i(), vddio_dac.measure.i(), vddio.measure.v(), vddio_dac.measure.v()])

  # Sweep through range
  for pw_exp, pw_mantissa in [(7,31)]: # [(0,1),(0,2),(0,4),(0,8),(0,16),(1,16),(2,16),(3,16),(4,16),(5,16),(6,16),(7,16),(7,31)]:
    for vwl in list(range(0, 256, 2)):
      for vbsl in list(range(0, 32, 4)) + [31]:
        # Write current measurements to outfile
        ember.settings["wl_dac_set_lvl_cycle"] = vwl
        ember.settings["bl_dac_set_lvl_cycle"] = ember.settings["sl_dac_rst_lvl_cycle"] = vbsl
        ember.settings["pw_set_cycle_exp"] = ember.settings["pw_rst_cycle_exp"] = pw_exp
        ember.settings["pw_set_cycle_mantissa"] = ember.settings["pw_rst_cycle_mantissa"] = pw_mantissa
        ember.commit_settings()
        ember.fast_mode()
        outfile.write(str(time.time()))
        outfile.write("\t")
        outfile.write(str(vwl))
        outfile.write("\t")
        outfile.write(str(vbsl))
        outfile.write("\t")
        outfile.write(str(pw_mantissa << pw_exp))
        outfile.write("\t")
        outfile.write("\t".join([str(a) for a in [vdd.measure(), vdd_dac.measure(), vsa.measure(), vddio.measure.i(), vddio_dac.measure.i(), vddio.measure.v(), vddio_dac.measure.v()]]))
        outfile.write("\n")
        ember.slow_mode()
