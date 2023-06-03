"""Script to measure SET energy on a chip"""
import argparse
from ember import EMBERDriver

# Get arguments
parser = argparse.ArgumentParser(description="Measure SET/RESET energy on a chip.")
parser.add_argument("chipname", help="chip name for logging")
parser.add_argument("--config", type=str, default="settings/enpulse.json", help="config file")
parser.add_argument("--start-addr", type=int, default=0, help="start address")
parser.add_argument("--end-addr", type=int, default=65536, help="end address")
parser.add_argument("--step-addr", type=int, default=1, help="address stride")
parser.add_argument("--reset", action="store_true", help="measure RESET instead of SET")
parser.add_argument("--min", action="store_true", help="measure in minimum energy mode")
args = parser.parse_args()

# Initialize EMBER system
with EMBERDriver(args.chipname, args.config) as ember:
  ember.set_addr(args.start_addr, args.end_addr, args.step_addr)
  action, bsl = ("rst", "sl") if args.reset else ("set", "bl")
  ember.settings[f"pw_{action}_cycle_exp"] = 7
  ember.settings[f"pw_{action}_cycle_mantissa"] = 31
  ember.settings[f"wl_dac_{action}_lvl_cycle"] = 255
  ember.settings[f"{bsl}_dac_{action}_lvl_cycle"] = 16 if args.min else 31
  ember.commit_settings()
  ember.cycle(use_multi_addrs=True)
