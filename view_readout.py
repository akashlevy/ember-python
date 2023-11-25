"""Script to view a readout result"""
import argparse
import pandas as pd
import matplotlib.pyplot as plt

# Get arguments
parser = argparse.ArgumentParser(description="View readout results.")
parser.add_argument("filename", help="readout filename")
parser.add_argument("--bpc", type=int, default=6, help="bits per cell")
args = parser.parse_args()

# Load data
data = pd.read_csv(args.filename, sep="\t")

# Show multi-bit result
matdata = data[data.columns[-48:]].values
im = plt.imshow(matdata[:256], vmin=0, vmax=2**args.bpc-1)
cbar = plt.colorbar(im, fraction=0.04, pad=0.04)
plt.show()

# \.\d+\t0\t28\t1\t(\d+\t){48}