"""Script to set VDDIO when using Keithley as source"""
import argparse
from keithley2600 import Keithley2600

# Get arguments
parser = argparse.ArgumentParser(description="Set VDDIO using Keithley.")
parser.add_argument("vddio", type=float, help="VDDIO value in volts")
args = parser.parse_args()

# Connect to Keithley 2612A and configure
k = Keithley2600("ASRL/dev/ttyUSB3::INSTR")
k.smua.source.levelv = k.smub.source.levelv = args.vddio # sets SMU A and B source level to vddio
k.smua.source.output = k.smub.source.output = k.smua.OUTPUT_ON # turn on SMU A and B
va, vb = k.smua.measure.v(), k.smub.measure.v() # measures voltage at SMU A and B
print("Voltage set to:", va, vb) # print measured voltage
