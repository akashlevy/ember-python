"""Collect data on retention across chip"""
import argparse
import time
import numpy as np
from ember import EMBERDriver

# Get arguments
parser = argparse.ArgumentParser(description="Program multiple levels to RRAM cells in a chip.")
parser.add_argument("chipname", help="chip name for logging")
parser.add_argument("--config", type=str, default="settings/2bpc_best_manual.json", help="config file")
parser.add_argument("--retention-outfile", help="file to put retention data in (default: no data)")
parser.add_argument("--ret-reads", type=int, default=60, help="how many retention reads to do")
parser.add_argument("--start-addr", type=int, default=0, help="start address")
parser.add_argument("--end-addr", type=int, default=65536, help="end address")
parser.add_argument("--step-addr", type=int, default=1, help="address stride")
parser.add_argument("--fast", action="store_true", help="use full clock speed")
args = parser.parse_args()

# Initialize EMBER system
with EMBERDriver(args.chipname, args.config) as ember:
  # Read file
  if args.retention_outfile is not None:
    readfile = open(args.retention_outfile, "a")

  # Initialize last read times
  first_read_times = {}

  # Do operation across cells
  for i, addr in enumerate(range(args.start_addr, args.end_addr, args.step_addr)):
    # Set address
    ember.set_addr(addr)
    print("ADDR", addr, "between", addr % 64, "and", min(addr % 64 + 1, 63))

    # Update write level
    ember.level_settings[1]["adc_lower_write_ref_lvl"] = ember.settings["level_settings"][1]["adc_lower_write_ref_lvl"] = addr % 64
    ember.level_settings[1]["adc_upper_write_ref_lvl"] = ember.settings["level_settings"][1]["adc_upper_write_ref_lvl"] = min(addr % 64 + 1, 63)

    # Write
    if args.fast:
      ember.fast_mode()
    ember.write([1]*48, check63=True, native=True)
    ember.wait_for_idle()
    ember.slow_mode()

    # Read
    if args.retention_outfile is not None:
      print("Done programming! Now reading...")
      # Short-term reads (0, 0.1, 1 seconds)
      first_read_times[addr] = time.time()
      for j in range(args.ret_reads):
        read = ember.superread()
        readfile.write(f"{addr}\t{time.time()}\t{read}\n")

      # Long-term reads
      for j, raddr in enumerate(range(args.start_addr, addr, args.step_addr)):
        dt = time.time() - first_read_times[raddr]
        for st in [10, 100, 1000, 10000, 100000]:
          if (dt >= 0.8 * st) and (dt <= 1.2 * st):
            ember.set_addr(raddr)
            read = ember.superread()
            readfile.write(f"{raddr}\t{time.time()}\t{read}\n")

  # Read continuously after all cells are programmed
  if args.retention_outfile is not None:
    while True:
      try:
        for addr in range(args.start_addr, args.end_addr, args.step_addr):
          ember.set_addr(addr)
          read = ember.superread()
          readfile.write(f"{addr}\t{time.time()}\t{read}\n")
      except KeyboardInterrupt:
        break

  # Shutdown
  if args.retention_outfile is not None:
    readfile.close()
