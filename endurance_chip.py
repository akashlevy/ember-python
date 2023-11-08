"""Script to perform endurance measurement on a chip"""
import argparse
import json
import time
import numpy as np
from ember import EMBERDriver
from fluke8808a import Fluke8808A

# Get arguments
parser = argparse.ArgumentParser(description="Endurance measurement.")
parser.add_argument("chipname", help="chip name for logging")
parser.add_argument("outfile", help="file to output to")
parser.add_argument("--config", type=str, default="settings/1bpc.json", help="config file")
parser.add_argument("--start-addr", type=int, default=0, help="start address")
parser.add_argument("--end-addr", type=int, default=65536, help="end address")
parser.add_argument("--step-addr", type=int, default=1, help="address stride")
parser.add_argument("--max-attempts", type=int, default=16, help="address stride")
parser.add_argument("--cb", action="store_true", help="use checkerboard data pattern")
parser.add_argument("--lfsr", action="store_true", help="use LFSR data pattern")
parser.add_argument("--checktime", type=float, default=3, help="time interval to check")
args = parser.parse_args()

# Initialize EMBER system and output file
with EMBERDriver(args.chipname, args.config) as ember, open(args.outfile, "a") as outfile:
  # Use fast mode
  ember.fast_mode()

  # Set address
  ember.set_addr(args.start_addr, args.end_addr-1, args.step_addr)

  # Set max attempts
  ember.settings["max_attempts"] = args.max_attempts

  # Write
  ember.write(0, native=True, cb=args.cb, lfsr=args.lfsr, loop_mode=True, use_multi_addrs=True)
  t0 = time.time()

  # Intermittent diagnostic check
  while True:
    try:
      time.sleep(args.checktime)
      t = time.time() - t0
      ember.pause_mclk() # automatically goes to slow mode
      diag = ember.get_diagnostics()
      print(f"{t}\t{diag['successes']}\t{diag['failures']}\t{diag['reads']}\t{diag['sets']}\t{diag['resets']}\t{diag['cycles']}\t{diag['read_bits']}\t{diag['set_bits']}\t{diag['reset_bits']}\n")
      outfile.write(f"{t}\t{diag['successes']}\t{diag['failures']}\t{diag['reads']}\t{diag['sets']}\t{diag['resets']}\t{diag['cycles']}\t{diag['read_bits']}\t{diag['set_bits']}\t{diag['reset_bits']}\n")
      ember.fast_mode() # automatically unpauses mclk
    except KeyboardInterrupt:
      break