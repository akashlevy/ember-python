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
with EMBERDriver(args.chipname, args.config) as ember, \
    Fluke8808A("/dev/ttyUSB3") as vdd_and_dac, \
    Fluke8808A("/dev/ttyUSB0") as vsa:
    # Set up Keithley SMUs
    k = Keithley2600("ASRL/dev/ttyUSB2::INSTR")
    vddio = k.smua
    vddio_dac = k.smub

    # Test measurement
    print("Test measurements...")
    print([vdd_and_dac.measure(), vsa.measure(), vddio.measure.i(), vddio_dac.measure.i(), vddio.measure.v(), vddio_dac.measure.v()])
    print([vdd_and_dac.measure(), vsa.measure(), vddio.measure.i(), vddio_dac.measure.i(), vddio.measure.v(), vddio_dac.measure.v()])
    vddio_voltage = vddio.measure.v()
    vddio_dac_voltage = vddio_dac.measure.v()

    # Increment maximum attempts
    for att in range(16, 256, 32):
        # Set maximum attempts
        real_att = (att & 31) << (att >> 5)
        ember.settings["max_attempts"] = att
        ember.commit_settings()

        # Program alternating init
        for i in range(len(ember.level_settings)):
            for j in range(2):
                # Set addresses to scroll across
                ember.set_addr(args.start_addr + i*2 + j, args.end_addr-len(ember.level_settings)*2 + i*2 + j, len(ember.level_settings)*2)

                # Start from level i
                print(f"Setting level {i}")
                ember.write([i]*48, use_multi_addrs=True)
                ember.fast_mode()
                while ember.gpio.read() & 0x20:
                    pass
                ember.slow_mode()

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

        # Measure latency and get diagnostics when writing checkerboard
        ember.set_addr(args.start_addr, args.end_addr-1, args.step_addr)
        ember.write([i % len(ember.level_settings) for i in range(48)], use_multi_addrs=True)
        ember.fast_mode()
        t0 = time.time()
        m = 0
        while ember.gpio.read() & 0x20:
            m = m + 1
        tf = time.time()
        ember.slow_mode()
        dt = tf - t0
        print("m =", m, "dt =", dt)
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

        # Energy measurement
        for vname, vdev in zip(["vdd_and_dac", "vsa", "vddio", "vddio_dac"], [vdd_and_dac, vsa, vddio, vddio_dac]):
            # Program alternating init
            for i in range(len(ember.level_settings)):
                for j in range(2):
                    # Set addresses to scroll across
                    ember.set_addr(args.start_addr + i*2 + j, args.end_addr-len(ember.level_settings)*2 + i*2 + j, len(ember.level_settings)*2)

                    # Start from level i
                    print(f"Setting level {i}")
                    ember.write([i]*48, use_multi_addrs=True)
                    ember.fast_mode()
                    while ember.gpio.read() & 0x20:
                        pass
                    ember.slow_mode()

            # Measure energy when writing checkerboard
            ember.set_addr(args.start_addr, args.end_addr-1, args.step_addr*2)
            ember.write([i % len(ember.level_settings) for i in range(48)], use_multi_addrs=True)
            ember.fast_mode()

            # Try to measure
            if "vddio" in vname:
                measurement = vdev.measure.i()
            else:
                measurement = vdev.measure()
            if ember.gpio.read() & 0x20:
                print(f"{vname}: {measurement}")
                np.savetxt(f"opt2/data/{vname}_power_{args.config.split('/')[-1][:-5]}_{real_att}.csv", np.array([measurement]), fmt='%s', delimiter=',')
            else:
                print(f"FAILED TO CAPTURE ON {vname}")
            ember.slow_mode()
            ember.set_addr(args.start_addr, args.end_addr-1, args.step_addr)
            ember.fast_mode()
            while ember.gpio.read() & 0x20:
                pass
            ember.slow_mode()
