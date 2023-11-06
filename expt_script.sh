for config in settings/opt/2bpc*_2.json; do
    echo $config
    python write_energy.py CHIP9 --config $config --lfsr
    python write_energy.py CHIP9 --config $config --cb
done