for config in settings/opt/1bpc_*opt.json; do
    echo $config
    python write_energy.py CHIP1 --config $config --cb --start-addr 4096
    python write_energy.py CHIP1 --config $config --lfsr --start-addr 4096
done
