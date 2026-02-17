"""
DS3231 Real-Time Clock I2C driver
"""

from config import Config


class DS3231:
    """I2C driver for DS3231 precision RTC module"""

    REGISTER_BASE = 0
    REGISTER_SIZE = 7

    def __init__(self, i2c, address=Config.DS3231_ADDR):
        self.i2c = i2c
        self.addr = address

    def _dec_to_bcd(self, value):
        """Convert decimal to Binary-Coded Decimal

        Args:
            value: Decimal number (0-99)

        Returns:
            int: BCD encoded value
        """
        return (value // 10 * 16) + (value % 10)

    def _bcd_to_dec(self, value):
        """Convert Binary-Coded Decimal to decimal

        Args:
            value: BCD encoded value

        Returns:
            int: Decimal number
        """
        return (value // 16 * 10) + (value % 16)

    def get_time(self):
        """Read current time from RTC

        Returns:
            tuple: (year, month, day, hour, minute, second, weekday, yearday) or None
        """
        try:
            data = self.i2c.readfrom_mem(self.addr, self.REGISTER_BASE, self.REGISTER_SIZE)

            seconds = self._bcd_to_dec(data[0])
            minutes = self._bcd_to_dec(data[1])
            hours = self._bcd_to_dec(data[2])
            weekday = self._bcd_to_dec(data[3])
            day = self._bcd_to_dec(data[4])
            month = self._bcd_to_dec(data[5] & 0x1F)
            year = self._bcd_to_dec(data[6]) + 2000

            return (year, month, day, hours, minutes, seconds, weekday - 1, 0)
        except Exception:
            return None

    def set_time(self, time_tuple):
        """Write time to RTC

        Args:
            time_tuple: (year, month, day, hour, minute, second, weekday, yearday)
        """
        try:
            data = bytearray(self.REGISTER_SIZE)
            data[0] = self._dec_to_bcd(time_tuple[5])
            data[1] = self._dec_to_bcd(time_tuple[4])
            data[2] = self._dec_to_bcd(time_tuple[3])
            data[3] = self._dec_to_bcd(time_tuple[6] + 1)
            data[4] = self._dec_to_bcd(time_tuple[2])
            data[5] = self._dec_to_bcd(time_tuple[1])
            data[6] = self._dec_to_bcd(time_tuple[0] - 2000)

            self.i2c.writeto_mem(self.addr, self.REGISTER_BASE, data)
        except Exception:
            pass
