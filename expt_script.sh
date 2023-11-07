for config in settings/opt/*.json; do
    echo $config
    python write_energy.py CHIP9 --config $config --lfsr
    python write_energy.py CHIP9 --config $config --cb
done
