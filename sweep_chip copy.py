"""Script to run a sweep on a chip"""
import argparse, time
from random import shuffle
from ember import EMBERDriver

# Get arguments
parser = argparse.ArgumentParser(description="Sweep a chip.")
parser.add_argument("chipname", help="chip name for logging")
parser.add_argument("outfile", help="file to output to")
parser.add_argument("--config", type=str, default="settings/form.json", help="config file")
parser.add_argument("--start-addr", type=int, default=0, help="start address")
parser.add_argument("--end-addr", type=int, default=65536, help="end address")
parser.add_argument("--step-addr", type=int, default=1, help="address stride")
parser.add_argument("--shuffle", action="store_true",help="shuffle addresses")
parser.add_argument("--reset", action="store_true",help="do RESET instead of SET")
args = parser.parse_args()

# Shuffled addressing
addrs = range(args.start_addr, args.end_addr, args.step_addr)
shuffled_addrs = list(range(args.start_addr, args.end_addr, args.step_addr))
shuffle(shuffled_addrs)
shuffled_addrs = {a : b for a, b in zip(addrs, shuffled_addrs)}

# Initialize EMBER system
with EMBERDriver(args.chipname, args.config, debug=False) as ember, open(args.outfile, "a") as outfile:
  ember.fast_mode()

  # # Force exactly one 
  # ember.settings["max_attempts"] = 1
  # ember.settings["level_settings"][0]["adc_upper_write_ref_lvl"] = ember.level_settings[0]["adc_upper_write_ref_lvl"] = 0
  # ember.settings["level_settings"][1]["adc_lower_write_ref_lvl"] = ember.level_settings[1]["adc_lower_write_ref_lvl"] = 63
  # ember.commit_settings()


  addr = args.start_addr
  while addr < args.end_addr:
    for pw_exp, pw_mantissa in [(1,31)]: #,(0,2),(0,4),(0,8),(0,16)]:
      for vwl in [255]: #list(range(0,168,8)):
        for vbsl in [31] if args.reset else list(range(0, 24, 1)):
          # ember.settings["level_settings"][0]["pw_rst_start_exp"] = ember.level_settings[0]["pw_rst_start_exp"] = pw_exp
          # ember.settings["level_settings"][0]["pw_rst_start_mantissa"] = ember.level_settings[0]["pw_rst_start_mantissa"] = pw_mantissa
          # ember.settings["level_settings"][0]["wl_dac_rst_lvl_start"] = ember.level_settings[0]["wl_dac_rst_lvl_start"] = vwl
          # ember.settings["level_settings"][0]["sl_dac_rst_lvl_start"] = ember.level_settings[0]["sl_dac_rst_lvl_start"] = vbsl

          # ember.settings["level_settings"][1]["pw_set_start_exp"] = ember.level_settings[1]["pw_set_start_exp"] = pw_exp
          # ember.settings["level_settings"][1]["pw_set_start_mantissa"] = ember.level_settings[1]["pw_set_start_mantissa"] = pw_mantissa
          # ember.settings["level_settings"][1]["wl_dac_set_lvl_start"] = ember.level_settings[1]["wl_dac_set_lvl_start"] = vwl
          # ember.settings["level_settings"][1]["bl_dac_set_lvl_start"] = ember.level_settings[1]["bl_dac_set_lvl_start"] = vbsl

          # ember.commit_settings()



          # Run experiment
          time.sleep(1)
          ember.set_addr(addr if not args.shuffle else shuffled_addrs[addr])
          time.sleep(1)
          print(addr if not args.shuffle else shuffled_addrs[addr])
          preread = ember.superread()
          time.sleep(1)
          print(preread)
          if args.reset:
            ember.reset_pulse(vwl, vbsl, pw_exp, pw_mantissa)
            # ember.write(0)
          else:
            ember.set_pulse(vwl, vbsl, pw_exp, pw_mantissa)
            # ember.write(0xFFFFFFFFFFFF)
          time.sleep(1)
          print(vwl, vbsl, pw_exp, pw_mantissa)
          postread = ember.superread()
          print(postread)

          # Write to outfile
          outfile.write(str(addr if not args.shuffle else shuffled_addrs[addr]))
          outfile.write("\t")
          outfile.write(str(time.time()))
          outfile.write("\t")
          outfile.write(str(vwl))
          outfile.write("\t")
          outfile.write(str(vbsl))
          outfile.write("\t")
          outfile.write(str(pw_mantissa << pw_exp))
          outfile.write("\t")
          outfile.write("\t".join([str(r) for r in preread]))
          outfile.write("\t")
          outfile.write("\t".join([str(r) for r in postread]))
          outfile.write("\n")

          # Increment address
          addr += args.step_addr
