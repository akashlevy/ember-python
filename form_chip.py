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
parser.add_argument("--native", action="store_true", help="no RESET-verify")
parser.add_argument("--fast", action="store_true", help="no RESET-verify")
parser.add_argument("--superfast", action="store_true", help="no RESET-verify at full clock speed")
parser.add_argument("--debug", action="store_true", help="enable debugging")
args = parser.parse_args()

# Initialize EMBER system
with EMBERDriver(args.chipname, args.config) as ember:
  # Native mode
  if args.native:
    ember.set_addr(args.start_addr, args.end_addr-1, args.step_addr)
    if args.fast or args.superfast:
      if args.superfast:
        ember.fast_mode()
      ember.write(0xFFFFFFFFFFFF, use_multi_addrs=True, debug=args.debug)
      ember.wait_for_idle(debug=args.debug)
      ember.slow_mode()
    else:
      # Do operation across cells
      for addr in range(args.start_addr, args.end_addr, args.step_addr):
        ember.set_addr(addr)
        ember.write(0xFFFFFFFFFFFF, debug=args.debug)
        print("Address", addr, "DONE:", ember.read())

  # Fast mode
  elif args.fast or args.superfast:
    ember.set_addr(args.start_addr, args.end_addr-1, args.step_addr)
    ember.set_pulse(use_multi_addrs=True)
    if args.superfast:
      ember.fast_mode()
    ember.wait_for_idle(debug=args.debug)
  # Slow mode
  else:
    # Do operation across cells
    for addr in range(args.start_addr, args.end_addr, args.step_addr):
      ember.set_addr(addr)
      ember.write(0xFFFFFFFFFFFF, native=args.native, debug=args.debug)
      print("Address", addr, "DONE:", ember.read())
