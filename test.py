with open('outfile.csv', 'w') as f:
    addr = 1
    while True:
        print(addr)
        f.write(str(addr) + "\n")
        if addr >= 65535:
            break
        addr = (addr + 2) % 65536