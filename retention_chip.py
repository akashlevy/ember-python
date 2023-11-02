"""Collect data on retention across chip"""
import argparse
import time
import pandas as pd
from random import shuffle
from ember import EMBERDriver

# Get arguments
parser = argparse.ArgumentParser(description="Program multiple levels to RRAM cells in a chip.")
parser.add_argument("chipname", help="chip name for logging")
parser.add_argument("outfile", help="file to put retention data in (default: no data)")
parser.add_argument("--config", type=str, default="settings/config.json", help="config file")
parser.add_argument("--ret-reads", type=int, default=60, help="how many retention reads to do")
parser.add_argument("--start-addr", type=int, default=0, help="start address")
parser.add_argument("--end-addr", type=int, default=65536, help="end address")
parser.add_argument("--step-addr", type=int, default=1, help="address stride")
parser.add_argument("--shuffle", action="store_true",help="shuffle addresses")
parser.add_argument("--fast", action="store_true", help="use full clock speed")
args = parser.parse_args()

# Load SET sweep data
setdata = pd.read_csv(f"data/sweep/setsweep33.csv.gz", delimiter="\t", names=["addr", "t", "vwl", "vbl", "pw"] + [f"gi[{i}]" for i in range(48)] + [f"gf[{i}]" for i in range(48)])
setdata = pd.concat([setdata[["addr","t","vwl","vbl","pw",f"gi[{i}]",f"gf[{i}]"]].rename(columns={f"gi[{i}]" : "gi", f"gf[{i}]" : "gf"}) for i in range(48)])

# Process SET sweep
gf2vblstart = {}
gmax = 0
d = setdata[(setdata["gi"].isin(range(1,20))) & (setdata["pw"] == 1) & (setdata["vwl"] == 0)][["vwl","vbl","pw","gi","gf"]]
for vbl, data in d.groupby("vbl"):
    gf = int(data.quantile(0.9999)["gf"])
    for g in range(gmax, gf):
        gf2vblstart[g] = vbl
    gmax = gf
gf2vblstart[63] = 20 # 28 # 30

# Shuffled addressing
addrs = range(args.start_addr, args.end_addr, args.step_addr)
shuffled_addrs = list(range(args.start_addr, args.end_addr, args.step_addr))
shuffle(shuffled_addrs)
shuffled_addrs = {a : b for a, b in zip(addrs, shuffled_addrs)}

# Initialize EMBER system and output file
with EMBERDriver(args.chipname, args.config) as ember, open(args.outfile, "a") as readfile:
  # Initialize last read times
  first_read_times = {}

  # Initialize address
  addr = args.start_addr

  # Set up fast mode
  if args.fast:
    ember.fast_mode()

  # Do operation across cells
  while True:
    for lower in range(0, 64):
      for upper in range(lower, 64):
        # Do width 0 only for 63
        if upper == lower and lower != 63:
          continue

        # Set address
        ember.set_addr(addr if not args.shuffle else shuffled_addrs[addr])
        print("ADDR", addr if not args.shuffle else shuffled_addrs[addr], "between", lower, "and", upper)

        # Update write settings
        ember.level_settings[1]["adc_lower_write_ref_lvl"] = ember.settings["level_settings"][1]["adc_lower_write_ref_lvl"] = lower
        ember.level_settings[1]["adc_upper_write_ref_lvl"] = ember.settings["level_settings"][1]["adc_upper_write_ref_lvl"] = upper
        ember.level_settings[1]["bl_dac_set_lvl_start"] = ember.settings["level_settings"][1]["bl_dac_set_lvl_start"] = (28 if upper == 63 else 0)
        ember.commit_settings()

        # Write and get diagnostics
        ember.write([1]*48, native=True)
        ember.wait_for_idle()
        diag = ember.get_diagnostics()

        # Read
        print("Done programming! Now reading...")
        # Short-term reads (0, 0.1, 1 seconds)
        first_read_times[addr if not args.shuffle else shuffled_addrs[addr]] = time.time()
        for j in range(args.ret_reads):
          read = ember.superread()
          readfile.write(f"{addr if not args.shuffle else shuffled_addrs[addr]}\t{time.time()}\t")
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
        readfile.write(f"{addr}\t{time.time()}\t0\t0\t0\t0\t0\t0\t0\t0\t0\t0\t0\t0\t{read}\n")
    except KeyboardInterrupt:
      break
