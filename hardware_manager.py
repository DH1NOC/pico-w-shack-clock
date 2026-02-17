"""
Hardware initialization and configuration manager
"""

from machine import I2C, Pin
from pico_i2c_lcd import I2cLcd
from config import Config
from ds3231 import DS3231
from gps_client import GPSClient
from ntp_client import NTPClient
from display_manager import DisplayManager


class HardwareManager:
    """Initialize and manage all hardware components"""
    
    def __init__(self, config_data):
        self.config = config_data
        self.i2c = None
        self.rtc = None
        self.display = None
        self.gps = None
        self.ntp = None
        
    def initialize_all(self):
        """Initialize all hardware components in correct order"""
        self._init_i2c()
        self._init_display()
        self._init_rtc()
        self._init_gps()
        self._init_ntp()
        
    def _init_i2c(self):
        """Initialize I2C bus"""
        self.i2c = I2C(
            Config.I2C_NUM,
            sda=Pin(Config.I2C_SDA_PIN),
            scl=Pin(Config.I2C_SCL_PIN),
            freq=Config.I2C_FREQ
        )
        
    def _init_display(self):
        """Initialize LCD display with boot animation"""
        try:
            lcd = I2cLcd(self.i2c, Config.I2C_ADDR, Config.LCD_ROWS, Config.LCD_COLS)
            callsign = self.config.get('callsign', 'DARC')
            self.display = DisplayManager(lcd, callsign)
            self.display.show_boot_animation()
        except Exception:
            self.display = None
            
    def _init_rtc(self):
        """Initialize DS3231 Real-Time Clock"""
        self.rtc = DS3231(self.i2c)
        
    def _init_gps(self):
        """Initialize GPS module if enabled"""
        if self.config.get('gps_enabled', Config.GPS_ENABLED):
            self.gps = GPSClient()
            
    def _init_ntp(self):
        """Initialize NTP client"""
        ntp_server = self.config.get('ntp_server', Config.DEFAULT_NTP_SERVER)
        self.ntp = NTPClient(ntp_server)
        
    def get_display(self):
        return self.display
    
    def get_rtc(self):
        return self.rtc
    
    def get_gps(self):
        return self.gps
    
    def get_ntp(self):
        return self.ntp
