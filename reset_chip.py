"""Script to RESET a chip"""
import argparse
from ember import EMBERDriver

# Get arguments
parser = argparse.ArgumentParser(description="RESET a chip.")
parser.add_argument("chipname", help="chip name for logging")
parser.add_argument("--config", type=str, default="settings/form.json", help="config file")
parser.add_argument("--start-addr", type=int, default=0, help="start address")
parser.add_argument("--end-addr", type=int, default=65536, help="end address")
parser.add_argument("--step-addr", type=int, default=1, help="address stride")
parser.add_argument("--debug", action="store_true", help="enable debugging")
args = parser.parse_args()

# Initialize EMBER system
with EMBERDriver(args.chipname, args.config) as ember:
  # Do READ operation across cells
  prereads = []
  for addr in range(args.start_addr, args.end_addr, args.step_addr):
    ember.set_addr(addr)
    prereads.append(ember.read())
  print("PREREAD:")
  for read in prereads:
    print(read)

  # Do operation across cells
  for addr in range(args.start_addr, args.end_addr, args.step_addr):
    ember.set_addr(addr)
    ember.write(0, debug=args.debug)
    print("Address", addr, "DONE:", ember.read())

  # Do READ operation across cells
  postreads = []
  for addr in range(args.start_addr, args.end_addr, args.step_addr):
    ember.set_addr(addr)
    postreads.append(ember.read())
  print("POSTREAD:")
  for read in postreads:
    print(read)
