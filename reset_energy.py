"""Script to measure RESET energy on a chip"""
import argparse
from ember import EMBERDriver

# Get arguments
parser = argparse.ArgumentParser(description="Measure RESET energy on a chip.")
parser.add_argument("chipname", help="chip name for logging")
parser.add_argument("--config", type=str, default="settings/form.json", help="config file")
parser.add_argument("--start-addr", type=int, default=0, help="start address")
parser.add_argument("--end-addr", type=int, default=65536, help="end address")
parser.add_argument("--step-addr", type=int, default=1, help="address stride")
args = parser.parse_args()

# Initialize EMBER system
with EMBERDriver(args.chipname, args.config) as ember:
  ember.set_addr(args.start_addr, args.end_addr, args.step_addr)
  ember.settings["pw_set_cycle_exp"] = 0
  ember.settings["pw_set_cycle_mantissa"] = 0
  ember.settings["wl_dac_set_lvl_cycle"] = 0
  ember.settings["bl_dac_set_lvl_cycle"] = 0
  ember.commit_settings()
  ember.cycle(use_multi_addrs=True)
