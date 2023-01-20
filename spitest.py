# Import spidev library
from spidev import SpiDev

# Create and configure SPI interface
spi = SpiDev()
spi.open(0,0)
spi.cshigh = True
spi.max_speed_hz = 4000

# Message to run a READ message by writing to the CMD register
msg = [0xd8] + [0x00]*19 + [0x04]

# Message to read from register 31 (should read out ASCII "RAM")
msg = [0x7c] + [0x00]*20

# Transfer message and print bytes received on mosi
print(spi.xfer(msg))

# Close SPI interface
spi.close()