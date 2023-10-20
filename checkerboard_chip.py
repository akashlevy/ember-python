"""Script to WRITE/READ a checkerboard to chip"""
import argparse, time
from ember import EMBERDriver

# Get arguments
parser = argparse.ArgumentParser(description="Checkerboard a chip.")
parser.add_argument("chipname", help="chip name for logging")
parser.add_argument("outfile", help="file to output to")
parser.add_argument("--config", type=str, default="settings/1bpc_best_manual.json", help="config file")
parser.add_argument("--start-addr", type=int, default=0, help="start address")
parser.add_argument("--end-addr", type=int, default=65536, help="end address")
parser.add_argument("--step-addr", type=int, default=1, help="address stride")
parser.add_argument("--native", action="store_true", help="use native checkerboard programming")
parser.add_argument("--fast", action="store_true", help="write checkerboard using multi-address mode")
parser.add_argument("--superfast", action="store_true", help="write checkerboard at full clock speed")
parser.add_argument("--loop", action="store_true", help="loop back when done")
parser.add_argument("--debug", action="store_true", help="enable debugging")
args = parser.parse_args()

# Initialize EMBER system and open outfile
with EMBERDriver(args.chipname, args.config) as ember, open(args.outfile, "a") as outfile:
  # Native/fast mode
  if args.native:
    ember.set_addr(args.start_addr, args.end_addr-1, args.step_addr)
    if args.fast or args.superfast:
      # Do operation across cells in one command
      if args.superfast:
        ember.fast_mode()
      ember.write(0, use_multi_addrs=True, cb=True, loop_mode=args.loop, debug=args.debug)
      ember.wait_for_idle(debug=args.debug)
    else:
      # Do operation across cells
      for addr in range(args.start_addr, args.end_addr, args.step_addr):
        # Single address
        ember.set_addr(addr)
        ember.write(0, cb=True, debug=args.debug)

        # Read directly after write
        read = ember.read()

        # Print address and read value
        print("Address", addr)
        print("READ", read)

        # Write to outfile
        outfile.write(str(addr))
        outfile.write("\t")
        outfile.write(str(time.time()))
        outfile.write("\t")
        outfile.write("\t".join([str(r) for r in read]))
        outfile.write("\n")

  # Slow mode
  else:
    # Checkerboard WRITE across cells
    for addr in range(args.start_addr, args.end_addr, args.step_addr):
      # Set address and write
      ember.set_addr(addr)
      num_levels = 16 if ember.settings["num_levels"] == 0 else ember.settings["num_levels"]
      write_array = [(i + addr) % num_levels for i in range(48)]
      ember.write(write_array, debug=args.debug)

      # Read directly after write
      read = ember.read()

      # Print address and read value
      print("Address", addr)
      print("WROTE", write_array)
      print("READ", read)

      # Write to outfile
      outfile.write(str(addr))
      outfile.write("\t")
      outfile.write(str(time.time()))
      outfile.write("\t")
      outfile.write("\t".join([str(r) for r in read]))
      outfile.write("\n")

  # READ operation across cells
  for addr in range(args.start_addr, args.end_addr, args.step_addr):
    # Set address and read
    ember.set_addr(addr)
    read = ember.read()

    # Print address and read value
    print("Address", addr)
    print("READ", read)

    # Write to outfile
    outfile.write(str(addr))
    outfile.write("\t")
    outfile.write(str(time.time()))
    outfile.write("\t")
    outfile.write("\t".join([str(r) for r in read]))
    outfile.write("\n")
