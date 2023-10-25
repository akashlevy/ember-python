"""Script to perform write energy measurement on a chip"""
import argparse
import json
import time
import numpy as np
from ember import EMBERDriver
from fluke8808a import Fluke8808A

# Get arguments
parser = argparse.ArgumentParser(description="Write energy measurement.")
parser.add_argument("chipname", help="chip name for logging")
parser.add_argument("--config", type=str, default="settings/1bpc.json", help="config file")
parser.add_argument("--start-addr", type=int, default=0, help="start address")
parser.add_argument("--end-addr", type=int, default=65536, help="end address")
parser.add_argument("--step-addr", type=int, default=1, help="address stride")
args = parser.parse_args()

# Initialize EMBER system and open outfile
with Fluke8808A("/dev/ttyUSB3") as vdd, \
    Fluke8808A("/dev/ttyUSB0") as vddio:

    # Test measurement
    print("Test measurements...")
    print([vddio.measure(), vdd.measure()])
    print([vddio.measure(), vdd.measure()])

    # Increment maximum attempts
    for att in [1, 2, 4, 8] + list(range(16, 256, 32)):
        with EMBERDriver(args.chipname, args.config) as ember:
            # Put into fast mode
            ember.fast_mode()

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
            np.savetxt(f"opt/data/preread/preread_{args.config.split('/')[-1][:-5]}_{real_att}.csv", np.array(reads), fmt='%s', delimiter=',')

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
            np.savetxt(f"opt/data/dt/dt_{args.config.split('/')[-1][:-5]}_{real_att}.csv", np.array([dt]), fmt='%s', delimiter=',')
            with open(f"opt/data/diag/diag_{args.config.split('/')[-1][:-5]}_{real_att}.json", "w") as diagjsonfile:
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
            np.savetxt(f"opt/data/postread/postread_{args.config.split('/')[-1][:-5]}_{real_att}.csv", np.array(reads), fmt='%s', delimiter=',')

            # Energy measurement for LFSR
            for i, (vname, vdev) in enumerate(zip(["vdd", "vddio"], [vdd, vddio])):
                # Measure energy when writing from LFSR
                ember.set_addr(args.start_addr+i, args.end_addr-1, args.step_addr)
                ember.write(0, use_multi_addrs=True, lfsr=True, loop_mode=True, check63=True)
                time.sleep(1)
                
                # Try to measure
                measurements = []
                for i in range(10):
                    measurements.append(vdev.measure())
                    time.sleep(1)
                
                # Measurements
                print("Measurements:", measurements)
                np.savetxt(f"opt/data/power/{vname}_lfsr_power_{args.config.split('/')[-1][:-5]}_{real_att}.csv", np.array(measurements), fmt='%s', delimiter=',')
                
                # Abort
                ember.abort()
                ember.fast_mode()
