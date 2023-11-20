for config in settings/opt/1bpc_*.json; do
    echo $config
    python write_energy.py CHIP9 --config $config --lfsr
    python write_energy.py CHIP9 --config $config --cb
done
