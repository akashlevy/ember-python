from keithley2600 import Keithley2600
k = Keithley2600('ASRL/dev/cu.usbserial-1130::INSTR')
k.smua.source.levelv = 2.5 # sets SMU A source level to 2.5V
i = k.smua.measure.i() # measures current at SMU A
print(i)