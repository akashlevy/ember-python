"""Script to measure endurance of a chip"""
import argparse, time
from ember import EMBERDriver

# Get arguments
parser = argparse.ArgumentParser(description="CYCLE a chip.")
parser.add_argument("chipname", help="chip name for logging")
parser.add_argument("outfile", help="file to output to")
parser.add_argument("--config", type=str, default="settings/cycle.json", help="config file")
parser.add_argument("--start-addr", type=int, default=0, help="start address")
parser.add_argument("--end-addr", type=int, default=65536, help="end address")
parser.add_argument("--step-addr", type=int, default=1, help="address stride")
parser.add_argument("--no-read", action="store_true", help="do not intermittently READ")
args = parser.parse_args()

# Cycler
def cycler(ember, args):
  for i in range(16):
    ember.settings["di_init_mask"] = 1 << i
    ember.commit_settings()
    ember.set_addr(args.start_addr, args.end_addr, args.step_addr)
    ember.cycle(use_multi_addrs=True)

# Initialize EMBER system
with EMBERDriver(args.chipname, args.config) as ember, open(args.outfile, "a") as outfile:
  ncycles = 0
  while True:
    for i in range(1):
      cycler(ember, args)
      ncycles += ember.settings["max_attempts"]
      # print("CYCLES:", ncycles, "i:", i)
    
    ember.settings["di_init_mask"] = 65535
    prereads = []
    for addr in range(args.start_addr, args.end_addr, args.step_addr):
      ember.set_addr(addr)
      prereads.append(ember.superread())
    
    if not args.no_read:
      ember.settings["max_attempts"], max_attempts = 1, ember.settings["max_attempts"]
      ember.settings["set_first"] = 1 - ember.settings["set_first"]
      cycler(ember, args)
      ember.settings["set_first"] = 1 - ember.settings["set_first"]
      ember.settings["max_attempts"] = max_attempts
      ncycles += 1

    ember.settings["di_init_mask"] = 65535
    postreads = []
    for addr in range(args.start_addr, args.end_addr, args.step_addr):
      ember.set_addr(addr)
      postreads.append(ember.superread())
    
    print("CYCLES:", ncycles)
    print("EXAMPLE:", prereads[0][0], postreads[0][0])

    # Outfile
    for addr, preread, postread in zip(range(args.start_addr, args.end_addr, args.step_addr), prereads, postreads):
      for i, (pre, post) in enumerate(zip(preread, postread)):
        outfile.write(str(addr))
        outfile.write("\t")
        outfile.write(str(i))
        outfile.write("\t")
        outfile.write(str(ncycles))
        outfile.write("\t")
        outfile.write(str(pre))
        outfile.write("\t")
        outfile.write(str(post))
        outfile.write("\n")
    
