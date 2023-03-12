"""Script to perform read energy measurement on a chip"""
import argparse
from ember import EMBERDriver

# Get arguments
parser = argparse.ArgumentParser(description="Perform checkerboard read energy measurement. Prerequisites: {1,2,3,4}bpc checkerboard are programmed in addresses {200-248, 300-348, 400-448, 500-548}.")
parser.add_argument("chipname", help="chip name for logging")
parser.add_argument("--config", type=str, default="settings/form.json", help="config file")
parser.add_argument("--bpc", type=int, default=1, help="bits per cell")
args = parser.parse_args()

# Initialize EMBER system and open outfile
with EMBERDriver(args.chipname, args.config) as ember:
  # Send read energy command for specified number of bits per cell
  ember.read_energy(args.bpc)

  # TODO: collect and report read power measurements here!
