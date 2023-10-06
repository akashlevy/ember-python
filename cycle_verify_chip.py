"""Script to cycle-verify a chip"""
import argparse
from ember import EMBERDriver

# Get arguments
parser = argparse.ArgumentParser(description="Cycle-verify a chip.")
parser.add_argument("chipname", help="chip name for logging")
parser.add_argument("--config", type=str, default="settings/deep_reset.json", help="config file")
parser.add_argument("--start-addr", type=int, default=0, help="start address")
parser.add_argument("--end-addr", type=int, default=65536, help="end address")
parser.add_argument("--step-addr", type=int, default=1, help="address stride")
parser.add_argument("--cycles", type=int, default=1, help="address stride")
parser.add_argument("--debug", action="store_true", help="enable debugging")
args = parser.parse_args()

# Initialize EMBER system
with EMBERDriver(args.chipname, args.config) as ember:
  ember.set_addr(args.start_addr, args.end_addr-1, args.step_addr)
  for i in range(args.cycles):
    print(f"Cycle {i} RESET-verify")
    ember.write(0x000000000000, use_multi_addrs=True, debug=args.debug)
    ember.fast_mode()
    ember.wait_for_idle(debug=args.debug)
    ember.slow_mode()
    print(f"Cycle {i} SET-verify")
    ember.write(0xFFFFFFFFFFFF, use_multi_addrs=True, debug=args.debug)
    ember.fast_mode()
    ember.wait_for_idle(debug=args.debug)
    ember.slow_mode()
