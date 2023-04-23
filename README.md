# EMBER Python
EMBER Python scripts for post-silicon validation and testing via SPI

## Procedures

[x] FORM
[x] ENDURANCE
[x] RETENTION
[ ] CHECKERBOARD
[ ] SET/RESET POWER

### FORM
- Switch voltage to 3.3V
- FORM
- DYNAMIC RESET
<!-- - Switch voltage to 2.5V -->

### ENDURANCE
- CYCLE 256 times
- Manual cycle with full range read in between
- Repeat

### RETENTION
- CYCLE 10000
- Run retention script

### CHECKERBOARD
- CYCLE 100x

### SET/RESET POWER
- CYCLE with only one of SET/RESET enabled on maximum PW (other on minimum PW, no VWL)
- Operate at minimum clock frequency (4kHz)
- Operate at endurance-measurement VWL and VBL/VSL

## EMBER Sister Repositories

- Digital: https://github.com/akashlevy/ember-digital
- Analog: https://code.stanford.edu/tsmc40r/emblem-analog (PRIVATE & TECHNOLOGY-SPECIFIC)
- Physical Design: https://code.stanford.edu/tsmc40r/emblem-pd (PRIVATE & TECHNOLOGY-SPECIFIC)
- PCB: https://github.com/akashlevy/ember-pcb
- FPGA (Genesys2) Project: https://github.com/akashlevy/ember-fpga
- PetaLinux Configuration: https://github.com/akashlevy/ember-petalinux-config
- Python SPI Environment: https://github.com/akashlevy/ember-python
