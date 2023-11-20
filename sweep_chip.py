"""Script to run a sweep on a chip"""
import argparse, time
from random import shuffle
from ember import EMBERDriver

# Get arguments
parser = argparse.ArgumentParser(description="Sweep a chip.")
parser.add_argument("chipname", help="chip name for logging")
parser.add_argument("outfile", help="file to output to")
parser.add_argument("--config", type=str, default="settings/form.json", help="config file")
parser.add_argument("--start-addr", type=int, default=0, help="start address")
parser.add_argument("--end-addr", type=int, default=65536, help="end address")
parser.add_argument("--step-addr", type=int, default=1, help="address stride")
parser.add_argument("--shuffle", action="store_true",help="shuffle addresses")
parser.add_argument("--reset", action="store_true",help="do RESET instead of SET")
args = parser.parse_args()

# Shuffled addressing
addrs = range(args.start_addr, args.end_addr, args.step_addr)
shuffled_addrs = list(range(args.start_addr, args.end_addr, args.step_addr))
shuffle(shuffled_addrs)
shuffled_addrs = {a : b for a, b in zip(addrs, shuffled_addrs)}

# Initialize EMBER system
with EMBERDriver(args.chipname, args.config) as ember, open(args.outfile, "a") as outfile:
  ember.fast_mode()
  addr = args.start_addr
  while addr < args.end_addr:
    for pw_exp, pw_mantissa in [(0,1)]: #,(0,2),(0,4),(0,8),(0,16)]:
      for vwl in list(range(0,256,8)) + [255]:
        for vbsl in range(32): #[31] if args.reset else list(range(0, 24, 1)):
          # Run experiment
          ember.set_addr(addr if not args.shuffle else shuffled_addrs[addr])
          preread = ember.superread()
          if args.reset:
            ember.reset_pulse(vwl, vbsl, pw_exp, pw_mantissa)
          else:
            ember.set_pulse(vwl, vbsl, pw_exp, pw_mantissa)
          ember.wait_for_idle()
          postread = ember.superread()

          # Write to outfile
          outfile.write(str(addr if not args.shuffle else shuffled_addrs[addr]))
          outfile.write("\t")
          outfile.write(str(time.time()))
          outfile.write("\t")
          outfile.write(str(vwl))
          outfile.write("\t")
          outfile.write(str(vbsl))
          outfile.write("\t")
          outfile.write(str(pw_mantissa << pw_exp))
          outfile.write("\t")
          outfile.write("\t".join([str(r) for r in preread]))
          outfile.write("\t")
          outfile.write("\t".join([str(r) for r in postread]))
          outfile.write("\n")

          # Increment address
          addr += args.step_addr
