python form_chip.py CHIP_N --native --superfast
python read_chip.py CHIP_N form.csv
python reset_chip.py CHIP_N --native --superfast
python read_chip.py CHIP_N reset.csv

python sweep_chip.py CHIP_N setsweep33.csv --shuffle
python sweep_chip.py CHIP_N setsweep33.csv --shuffle
python sweep_chip.py CHIP_N resetsweep33.csv --shuffle --reset
python sweep_chip.py CHIP_N resetsweep33.csv --shuffle --reset

python retention_chip.py CHIP_N retention.csv --fast --shuffle --ret-reads 1

# Process read retention
