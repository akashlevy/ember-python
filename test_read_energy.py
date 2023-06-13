"""Test read energy measurement"""
import time
from fluke8808a import Fluke8808A
from keithley2600 import Keithley2600
from keithley2420 import Keithley2420

# Initialize EMBER system and open outfile
with Fluke8808A("/dev/ttyUSB0") as vdd, \
     Fluke8808A("/dev/ttyUSB1") as vdd_dac, \
     Keithley2420("/dev/ttyUSB2") as vsa:
  # Set up Keithley SMUs
  k = Keithley2600("ASRL/dev/ttyUSB3::INSTR")
  vddio = k.smua
  vddio_dac = k.smub

  # Test measurement
  print("Test measurements")
  while True:
    t = time.time()
    print(vdd.measure(), time.time()-t)
    t = time.time()
    print(vdd_dac.measure(), time.time()-t)
    t = time.time()
    print(vsa.measure(), time.time()-t)
    t = time.time()
    print(vddio.measure.i(), time.time()-t)
    t = time.time()
    print(vddio_dac.measure.i(), time.time()-t)
    t = time.time()
    print(vddio.measure.v(), time.time()-t)
    t = time.time()
    print(vddio_dac.measure.v(), time.time()-t)
    print()
