"""Script to set address register"""
import argparse
from ember import EMBERDriver

# Get arguments
parser = argparse.ArgumentParser(description="Set address register.")
parser.add_argument("chipname", help="chip name for logging")
parser.add_argument("--config", type=str, default="settings/form.json", help="config file")
parser.add_argument("--start-addr", type=int, default=0, help="start address")
parser.add_argument("--end-addr", type=int, default=65536, help="end address")
parser.add_argument("--step-addr", type=int, default=1, help="address stride")
args = parser.parse_args()

# Initialize EMBER system and open outfile
with EMBERDriver(args.chipname, args.config) as ember:
  # Set address and read
  ember.set_addr(args.start_addr, args.end_addr, args.step_addr)
