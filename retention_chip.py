"""Collect data on retention across chip"""
import argparse
import time
import numpy as np
from ember import EMBERDriver

# Get arguments
parser = argparse.ArgumentParser(description="Program multiple levels to RRAM cells in a chip.")
parser.add_argument("chipname", help="chip name for logging")
parser.add_argument("outfile", help="file to put retention data in (default: no data)")
parser.add_argument("--config", type=str, default="settings/2bpc_best_manual.json", help="config file")
parser.add_argument("--ret-reads", type=int, default=60, help="how many retention reads to do")
parser.add_argument("--start-addr", type=int, default=0, help="start address")
parser.add_argument("--end-addr", type=int, default=65536, help="end address")
parser.add_argument("--step-addr", type=int, default=1, help="address stride")
parser.add_argument("--fast", action="store_true", help="use full clock speed")
args = parser.parse_args()

# Initialize EMBER system and output file
with EMBERDriver(args.chipname, args.config) as ember, open(args.outfile, "a") as readfile:
  # Initialize last read times
  first_read_times = {}

  # Initialize address
  addr = args.start_addr

  # Do operation across cells
  while True:
    for lower in range(0, 64):
      for upper in range(lower, 64):
        # Do width 0 only for 63
        if upper == lower and lower != 63:
          continue

        # Update write level
        ember.level_settings[1]["adc_lower_write_ref_lvl"] = ember.settings["level_settings"][1]["adc_lower_write_ref_lvl"] = lower
        ember.level_settings[1]["adc_upper_write_ref_lvl"] = ember.settings["level_settings"][1]["adc_upper_write_ref_lvl"] = upper

        # Set address
        ember.set_addr(addr)
        print("ADDR", addr, "between", lower, "and", upper)

        # Write and get diagnostics
        if args.fast:
          ember.fast_mode()
        ember.write([1]*48, check63=True, native=True)
        ember.wait_for_idle()
        ember.slow_mode()
        diag = ember.get_diagnostics()

        # Read
        print("Done programming! Now reading...")
        # Short-term reads (0, 0.1, 1 seconds)
        first_read_times[addr] = time.time()
        for j in range(args.ret_reads):
          read = ember.superread()
          readfile.write(f"{addr}\t{time.time()}\t")
          readfile.write(f"{lower}\t{upper}\t{upper-lower}\t")
          readfile.write(f"{diag['successes']}\t{diag['failures']}\t{diag['reads']}\t{diag['sets']}\t{diag['resets']}\t{diag['cycles']}\t{diag['read_bits']}\t{diag['set_bits']}\t{diag['reset_bits']}\t")
          readfile.write(f"{read}\n")

          # # Long-term reads
          # for j, raddr in enumerate(range(args.start_addr, addr, args.step_addr)):
          #   dt = time.time() - first_read_times[raddr]
          #   for st in [10, 100, 1000, 10000, 100000]:
          #     if (dt >= 0.8 * st) and (dt <= 1.2 * st):
          #       ember.set_addr(raddr)
          #       read = ember.superread()
          #       readfile.write(f"{raddr}\t{time.time()}\t{read}\n")

        # Update address and break if necessary
        addr = addr + args.step_addr
        if addr >= args.end_addr:
          break
      if addr >= args.end_addr:
        break
    if addr >= args.end_addr:
      break

  # Read continuously after all cells are programmed
  while True:
    try:
      for addr in range(args.start_addr, args.end_addr, args.step_addr):
        ember.set_addr(addr)
        read = ember.superread()
        readfile.write(f"{addr}\t{time.time()}\t{read}\n")
    except KeyboardInterrupt:
      break
