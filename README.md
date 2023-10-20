# EMBER Python

EMBER Python scripts for post-silicon validation and testing via SPI

## Procedures

- Set up board
    - Ensure `vdd_fsm`, `vdd`, `vdd_dac`, `vsa` are all at 0.9V
    - Ensure `vddio` and `vddio_dac` are at 3.3V
    - Ensure 2.5V <= `vddio_fsm` <= 3.3V
    - Ensure `wl_source_pin` is connected to `vadj`
    - Ensure `byp` switch is ON and `man` switch is OFF
- FORM chip
    - `python form_chip.py CHIP_N --native --superfast`
    - Should take about 20 minutes
- (Optional) READ chip
    - `python read_chip.py CHIP_N form.csv`
    - Should take about 30 minutes
- RESET chip
    - `python reset_chip.py CHIP_N --native --superfast`
    - Should take about 10 minutes
- (Optional) READ chip
    - `python read_chip.py CHIP_N reset.csv`
    - Should take about 30 minutes

## EMBER Sister Repositories

- Digital: https://github.com/akashlevy/ember-digital
- Analog: https://code.stanford.edu/tsmc40r/emblem-analog (PRIVATE & TECHNOLOGY-SPECIFIC)
- Physical Design: https://code.stanford.edu/tsmc40r/emblem-pd (PRIVATE & TECHNOLOGY-SPECIFIC)
- PCB: https://github.com/akashlevy/ember-pcb
- FPGA (Genesys2) Project: https://github.com/akashlevy/ember-fpga
- PetaLinux Configuration: https://github.com/akashlevy/ember-petalinux-config
- Python SPI Environment: https://github.com/akashlevy/ember-python
