"""
Hardware and application configuration constants
"""


class Config:
    """Central configuration for DH1NOC Shack Clock"""

    # I2C Bus Configuration
    I2C_ADDR = 0x27
    DS3231_ADDR = 0x68
    I2C_NUM = 0
    I2C_SDA_PIN = 0
    I2C_SCL_PIN = 1
    I2C_FREQ = 100000

    # LCD Display Configuration
    LCD_ROWS = 4
    LCD_COLS = 20

    # GPS Module Configuration (NEO-6M)
    GPS_UART_ID = 1
    GPS_TX_PIN = 4
    GPS_RX_PIN = 5
    GPS_BAUD = 9600
    GPS_ENABLED = True
    GPS_PRIORITY = 1

    # Localization
    WEEKDAYS = ["Mo", "Di", "Mi", "Do", "Fr", "Sa", "So"]

    # Network Configuration
    DEFAULT_NTP_SERVER = "pool.ntp.org"
    DEFAULT_SYNC_INTERVAL_MIN = 60
    WIFI_RETRY_INTERVAL_SEC = 300
    NTP_PRIORITY = 2

    # Timing Configuration
    NTP_SAMPLES = 3
    NTP_SAMPLE_DELAY_MS = 200
    RTC_SET_COMPENSATION_MS = 20
    RTC_PRIORITY = 3

    # Time Source Identifiers
    TIME_SOURCE_GPS = "GPS"
    TIME_SOURCE_NTP = "NTP"
    TIME_SOURCE_RTC = "RTC"

    # Debug Modes
    DEBUG_MODE = None
    DEBUG_MODE_GPS = "GPS"
    DEBUG_MODE_NTP = "NTP"
    DEBUG_MODE_WIFI = "WIFI"
