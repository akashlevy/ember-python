from spidev import SpiDev

spi = SpiDev()
spi.open(0,0)
spi.cshigh = True
spi.max_speed_hz = 4000
msg = [0xd8] + [0x00]*19 + [0x04]
msg = [0xc7] + [0x00]*20
print(spi.xfer(msg))
spi.close()
