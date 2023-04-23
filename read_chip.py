"""Script to READ a chip"""
import argparse, time
from ember import EMBERDriver

# Get arguments
parser = argparse.ArgumentParser(description="READ a chip (16 levels across dynamic range).")
parser.add_argument("chipname", help="chip name for logging")
parser.add_argument("outfile", help="file to output to")
parser.add_argument("--config", type=str, default="settings/form.json", help="config file")
parser.add_argument("--start-addr", type=int, default=0, help="start address")
parser.add_argument("--end-addr", type=int, default=65536, help="end address")
parser.add_argument("--step-addr", type=int, default=1, help="address stride")
parser.add_argument("--print-at-end", type=bool, default=False, help="print as array at end")
parser.add_argument("--plot-at-end", type=bool, default=True, help="plot as image at end")
parser.add_argument("--continuous", action="store_true", help="run READ continuously")
parser.add_argument("--super", action="store_true", help="run super READ")
args = parser.parse_args()

# Initialize EMBER system and open outfile
with EMBERDriver(args.chipname, args.config) as ember, open(args.outfile, "a") as outfile:
  while True:
    # Do operation across cells
    reads = []
    for addr in range(args.start_addr, args.end_addr, args.step_addr):
      # Set address and read
      ember.set_addr(addr)
      read = ember.read() if not args.super else ember.superread()
      reads.append(read)

      # Print address and read value
      print("Address", addr)
      print("READ", read)

      # Write to outfile
      outfile.write(str(addr))
      outfile.write("\t")
      outfile.write(str(time.time()))
      outfile.write("\t")
      if isinstance(read, int):
        outfile.write(str(read))
      elif isinstance(read, list):
        outfile.write("\t".join([str(r) for r in read]))
      outfile.write("\n")

    # Print at end if requested
    if args.print_at_end:
      for read in reads:
        print(" ".join([str(r) for r in read]))

    # Plot at end if requested
    if args.plot_at_end:
      import numpy as np, matplotlib.pyplot as plt
      plt.imshow(np.array(reads))
      plt.colorbar()
      plt.clim(0,63 if args.super else (ember.settings["num_levels"] + 15) % 16)
      plt.show()

    # Break if not in continuous mode
    if not args.continuous:
      break
