"""Script to FORM a chip"""
import argparse
from ember import EMBERDriver

# Get arguments
parser = argparse.ArgumentParser(description="FORM a chip.")
parser.add_argument("chipname", help="chip name for logging")
parser.add_argument("--config", type=str, default="settings/form.json", help="config file")
parser.add_argument("--start-addr", type=int, default=0, help="start address")
parser.add_argument("--end-addr", type=int, default=65536, help="end address")
parser.add_argument("--step-addr", type=int, default=1, help="address stride")
args = parser.parse_args()

# Initialize NI system and open outfile
with EMBERDriver(args.chipname, args.config) as ember:
  # Do READ operation across cells
  prereads = []
  for addr in range(args.start_addr, args.end_addr, args.step_addr):
    ember.set_addr(addr)
    prereads.append(ember.read())
  print("PREREAD:")
  for read in prereads:
    print("{0:048b}".format(read))

  # Do operation across cells
  for addr in range(args.start_addr, args.end_addr, args.step_addr):
    ember.set_addr(addr)
    ember.write(0xFFFFFFFFFFFF)
    print("Address", addr, "DONE")

  # Do READ operation across cells
  postreads = []
  for addr in range(args.start_addr, args.end_addr, args.step_addr):
    ember.set_addr(addr)
    postreads.append(ember.read())
  print("POSTREAD:")
  for read in postreads:
    print("{0:048b}".format(read))