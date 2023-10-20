"""Script to perform write energy measurement on a chip"""
import argparse
import json
import time
import numpy as np
from ember import EMBERDriver
from fluke8808a import Fluke8808A
from keithley2600 import Keithley2600

# Get arguments
parser = argparse.ArgumentParser(description="Write energy measurement.")
parser.add_argument("chipname", help="chip name for logging")
parser.add_argument("--config", type=str, default="settings/1bpc.json", help="config file")
parser.add_argument("--start-addr", type=int, default=0, help="start address")
parser.add_argument("--end-addr", type=int, default=65536, help="end address")
parser.add_argument("--step-addr", type=int, default=1, help="address stride")
args = parser.parse_args()

# Initialize EMBER system and open outfile
with EMBERDriver(args.chipname, args.config) as ember: # , \
    # Fluke8808A("/dev/ttyUSB3") as vdd_and_dac, \
    # Fluke8808A("/dev/ttyUSB0") as vsa:
    # # Set up Keithley SMUs
    # k = Keithley2600("ASRL/dev/ttyUSB2::INSTR")
    # vddio = k.smua
    # vddio_dac = k.smub

    # # Test measurement
    # print("Test measurements...")
    # print([vdd_and_dac.measure(), vsa.measure(), vddio.measure.i(), vddio_dac.measure.i(), vddio.measure.v(), vddio_dac.measure.v()])
    # print([vdd_and_dac.measure(), vsa.measure(), vddio.measure.i(), vddio_dac.measure.i(), vddio.measure.v(), vddio_dac.measure.v()])
    # vddio_voltage = vddio.measure.v()
    # vddio_dac_voltage = vddio_dac.measure.v()

    # Set fast mode
    ember.fast_mode()

    # Increment maximum attempts
    for att in [1, 2, 4, 8] + list(range(16, 256, 32)):
        # Set maximum attempts
        real_att = (att & 31) << (att >> 5)
        ember.settings["max_attempts"] = 240

        # Initialize with LFSR offset by 1
        ember.set_addr(args.start_addr+args.step_addr, args.end_addr-1, args.step_addr)
        ember.write(0, use_multi_addrs=True, lfsr=True, check63=True)
        ember.wait_for_idle()

        # Pre-read
        print("Pre-read...")
        reads = []
        for addr in range(args.start_addr, args.end_addr, args.step_addr):
            # Set address and read
            ember.set_addr(addr)
            read = ember.read()
            reads.append(read)
            if addr % 1000 == 0:
                # Print address and read value
                print("Address", addr)
                print("READ", read)
        np.savetxt(f"opt2/data/preread_{args.config.split('/')[-1][:-5]}_{real_att}.csv", np.array(reads), fmt='%s', delimiter=',')

        # Set maximum attempts
        real_att = (att & 31) << (att >> 5)
        ember.settings["max_attempts"] = att

        # Measure latency and get diagnostics when writing checkerboard
        ember.set_addr(args.start_addr, args.end_addr-1, args.step_addr)
        ember.write(0, use_multi_addrs=True, lfsr=True, check63=True)
        t0 = time.time()
        ember.wait_for_idle()
        tf = time.time()
        dt = tf - t0
        print("dt =", dt)
        np.savetxt(f"opt2/data/dt_{args.config.split('/')[-1][:-5]}_{real_att}.csv", np.array([dt]), fmt='%s', delimiter=',')
        with open(f"opt2/data/diag_{args.config.split('/')[-1][:-5]}_{real_att}.json", "w") as diagjsonfile:
            json.dump(ember.get_diagnostics(), diagjsonfile)

        # Post-read (for BER)
        print("Post-read...")
        reads = []
        for addr in range(args.start_addr, args.end_addr, args.step_addr):
            # Set address and read
            ember.set_addr(addr)
            read = ember.read()
            reads.append(read)
            if addr % 1000 == 0:
                # Print address and read value
                print("Address", addr)
                print("READ", read)
        np.savetxt(f"opt2/data/postread_{args.config.split('/')[-1][:-5]}_{real_att}.csv", np.array(reads), fmt='%s', delimiter=',')

        # # Energy measurement
        # for i, (vname, vdev) in enumerate(zip(["vdd_and_dac", "vsa", "vddio", "vddio_dac"], [vdd_and_dac, vsa, vddio, vddio_dac])):
        #     # Measure energy when writing checkerboard
        #     ember.set_addr(args.start_addr, args.end_addr)
        #     ember.fast_mode()
        #     ember.write(0, use_multi_addrs=True, lfsr=True)
            
        #     # Try to measure
        #     if "vddio" in vname:
        #         measurement = vdev.measure.i()
        #     else:
        #         measurement = vdev.measure()
        #     if ember.gpio.read() & 0x20:
        #         print(f"{vname}: {measurement}")
        #         np.savetxt(f"opt2/data/{vname}_power_{args.config.split('/')[-1][:-5]}_{real_att}.csv", np.array([measurement]), fmt='%s', delimiter=',')
        #     else:
        #         print(f"FAILED TO CAPTURE ON {vname}")

        #     ember.wait_for_idle()
        #     ember.slow_mode()
