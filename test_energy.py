"""Test energy measurement"""
import time
from fluke8808a import Fluke8808A

# Initialize EMBER system and open outfile
with Fluke8808A("/dev/ttyUSB3") as vdd, \
    Fluke8808A("/dev/ttyUSB0") as vddio:

  # Test measurement
  print("Test measurements")
  while True:
    t = time.time()
    print(vdd.measure(), time.time()-t)
    t = time.time()
    print(vddio.measure(), time.time()-t)
    t = time.time()
    print()
