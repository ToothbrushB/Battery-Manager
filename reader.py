import smbus3

# https://stackoverflow.com/questions/41335921/how-to-read-from-multiplexer-with-python-i2c-tca9548a
class TCA9548A:
    def __init__(self, bus, address=0x70):
        self.bus = bus
        self.address = address

    def select_channel(self, channel):
        if channel < 0 or channel > 7:
            raise ValueError("Channel must be between 0 and 7")
        self.bus.write_byte(self.address, 1 << channel)

    def read_channel(self, channel):
        self.select_channel(channel)
        return self.bus.read_byte(self.address)
    

    
if __name__ == "__main__":
    bus = smbus3.SMBus(1)  # Use I2C bus 1
    root = TCA9548A(bus)

    for channel in range(8):
        try:
            data = multiplexer.read_channel(channel)
            print(f"Channel {channel}: {data}")
        except Exception as e:
            print(f"Error reading channel {channel}: {e}")