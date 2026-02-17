"""
GPS client for NEO-6M module with NMEA sentence parsing
"""

import time
from machine import UART, Pin
from config import Config


class GPSClient:
    """NEO-6M GPS receiver client for time and position data"""

    NMEA_BUFFER_SIZE = 255
    FIX_TIMEOUT_MS = 10000

    def __init__(self, uart_id=Config.GPS_UART_ID, 
                 tx_pin=Config.GPS_TX_PIN, 
                 rx_pin=Config.GPS_RX_PIN,
                 baudrate=Config.GPS_BAUD):
        """Initialize GPS UART connection"""
        self.uart = UART(
            uart_id,
            baudrate=baudrate,
            tx=Pin(tx_pin),
            rx=Pin(rx_pin),
            timeout=100
        )

        self.buffer = b""
        self.has_fix = False
        self.satellites = 0
        self.latitude = 0.0
        self.longitude = 0.0
        self.altitude = 0.0
        self.utc_time = None
        self.utc_time_tick = 0
        self.raw_frame_count = 0
        self.last_fix_time = 0

    def _parse_coordinate(self, value, direction):
        """Convert NMEA coordinate (DDMM.MMMM) to decimal degrees

        Args:
            value: NMEA coordinate string
            direction: 'N', 'S', 'E', or 'W'

        Returns:
            float: Decimal degrees
        """
        if not value or value == "":
            return 0.0

        try:
            dot_pos = value.find('.')
            if dot_pos == -1:
                return 0.0

            degrees = float(value[:dot_pos-2])
            minutes = float(value[dot_pos-2:])
            result = degrees + (minutes / 60.0)

            if direction in ['S', 'W']:
                result *= -1

            return result
        except Exception:
            return 0.0

    def _parse_time(self, time_str, date_str):
        """Parse NMEA time and date strings to time tuple

        Args:
            time_str: HHMMSS.SSS format
            date_str: DDMMYY format

        Returns:
            tuple: (year, month, day, hour, minute, second, weekday, yearday) or None
        """
        try:
            if len(time_str) < 6:
                return None

            hours = int(time_str[0:2])
            minutes = int(time_str[2:4])
            seconds = int(time_str[4:6])

            if len(date_str) == 6:
                day = int(date_str[0:2])
                month = int(date_str[2:4])
                year = 2000 + int(date_str[4:6])
            else:
                if self.utc_time:
                    year, month, day = self.utc_time[0], self.utc_time[1], self.utc_time[2]
                else:
                    year, month, day = 2000, 1, 1

            return (year, month, day, hours, minutes, seconds, 0, 0)
        except Exception:
            return None

    def _process_line(self, line):
        """Parse complete NMEA sentence"""
        try:
            line_str = line.decode('utf-8').strip()
            if not line_str.startswith('$'):
                return

            self.raw_frame_count += 1
            parts = line_str.split(',')

            if line_str.startswith('$GPRMC') or line_str.startswith('$GNRMC'):
                self._process_rmc_sentence(parts)
            elif line_str.startswith('$GPGGA') or line_str.startswith('$GNGGA'):
                self._process_gga_sentence(parts)

        except Exception:
            pass

    def _process_rmc_sentence(self, parts):
        """Process RMC sentence (time and position)"""
        if len(parts) > 2 and parts[2] == 'A':
            self.has_fix = True
            self.last_fix_time = time.ticks_ms()

            parsed_time = self._parse_time(parts[1], parts[9] if len(parts) > 9 else "")
            if parsed_time:
                self.utc_time = parsed_time
                self.utc_time_tick = time.ticks_ms()

            if len(parts) > 6:
                self.latitude = self._parse_coordinate(parts[3], parts[4])
                self.longitude = self._parse_coordinate(parts[5], parts[6])
        else:
            if time.ticks_diff(time.ticks_ms(), self.last_fix_time) > self.FIX_TIMEOUT_MS:
                self.has_fix = False

    def _process_gga_sentence(self, parts):
        """Process GGA sentence (satellites and altitude)"""
        if len(parts) > 9:
            try:
                self.satellites = int(parts[7]) if parts[7] else 0
                self.altitude = float(parts[9]) if parts[9] else 0.0
            except Exception:
                pass

    def update(self):
        """Process incoming UART data byte-by-byte

        Call frequently in main loop to prevent buffer overflow
        """
        while self.uart.any():
            try:
                char = self.uart.read(1)
                if char == b'\n':
                    self._process_line(self.buffer)
                    self.buffer = b""
                else:
                    self.buffer += char
                    if len(self.buffer) > self.NMEA_BUFFER_SIZE:
                        self.buffer = b""
            except Exception:
                self.buffer = b""

    def get_time(self):
        """Get current UTC time from GPS

        Returns:
            tuple: Time tuple or None if no fix
        """
        return self.utc_time if self.has_fix else None

    def get_time_with_timestamp(self):
        """Get UTC time with reception timestamp

        Returns:
            tuple: (time_tuple, tick_reference) or None
        """
        if self.has_fix and self.utc_time:
            return (self.utc_time, self.utc_time_tick)
        return None

    def get_status(self):
        """Get GPS status information

        Returns:
            dict: Complete GPS status
        """
        return {
            'has_fix': self.has_fix,
            'satellites': self.satellites,
            'latitude': self.latitude,
            'longitude': self.longitude,
            'altitude': self.altitude,
            'frame_count': self.raw_frame_count
        }