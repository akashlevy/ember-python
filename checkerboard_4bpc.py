"""Script to WRITE/READ a 4bpc checkerboard to chip"""
import argparse, time
from ember import EMBERDriver

# Get arguments
parser = argparse.ArgumentParser(description="READ a chip (16 levels across dynamic range).")
parser.add_argument("chipname", help="chip name for logging")
parser.add_argument("outfile", help="file to output to")
parser.add_argument("--config", type=str, default="settings/4bpc.json", help="config file")
parser.add_argument("--start-addr", type=int, default=0, help="start address")
parser.add_argument("--end-addr", type=int, default=65536, help="end address")
parser.add_argument("--step-addr", type=int, default=1, help="address stride")
args = parser.parse_args()

# Initialize EMBER system and open outfile
with EMBERDriver(args.chipname, args.config) as ember, open(args.outfile, "a") as outfile:
  # Checkerboard WRITE across cells
  for addr in range(args.start_addr, args.end_addr, args.step_addr):
    # Set address and write
    ember.set_addr(addr)
    ember.write([(i + addr) % 16 for i in range(48)])

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
