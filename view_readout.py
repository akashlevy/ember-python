"""Script to view a readout result"""
import argparse
import pandas as pd
import matplotlib.pyplot as plt

# Get arguments
parser = argparse.ArgumentParser(description="View readout results.")
parser.add_argument("filename", help="readout filename")
parser.add_argument("--start-addr", type=int, default=0, help="start address")
parser.add_argument("--end-addr", type=int, default=65536, help="end address")
parser.add_argument("--step-addr", type=int, default=1, help="address stride")
parser.add_argument("--bpc", type=int, default=1, help="bits per cell")
args = parser.parse_args()

# Load data
names = ["addr", "time"] + ["read_" + str(i) for i in range(48)]
data = pd.read_csv(args.filename, sep="\t", names=names)
data = data[data["addr"].isin(range(args.start_addr, args.end_addr, args.step_addr))]

# Show multi-bit result
matdata = data[data.columns[-48:]].values
im = plt.imshow(matdata, vmin=0, vmax=2**args.bpc-1)
cbar = plt.colorbar(im, fraction=0.04, pad=0.04)
plt.show()

# \.\d+\t0\t28\t1\t(\d+\t){48}