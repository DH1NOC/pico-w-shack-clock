import utime
from machine import I2C
from lcd_api import LcdApi

# Modifizierter Treiber für Raspberry Pi Pico
# Behebt Probleme mit Soft-Reset und Timing bei HD44780 Displays

class I2cLcd(LcdApi):
    def __init__(self, i2c, i2c_addr, num_lines, num_columns):
        self.i2c = i2c
        self.i2c_addr = i2c_addr
        self.backlight = True # Standardmäßig an
        
        # 1. PCF8574 "säubern" (Alle Ausgänge auf 0)
        # Das verhindert, dass ein hängendes "Enable"-Signal stört
        try:
            self.i2c.writeto(self.i2c_addr, bytes([0]))
            utime.sleep_ms(20)
        except:
            pass

        # 2. Hard-Reset Sequenz für HD44780 (Nibble-Sync)
        # Wir machen das MANUELL, bevor wir LcdApi initialisieren
        # Sequenz: 0x03, 0x03, 0x03, 0x02
        self.custom_init_nibble(0x03)
        utime.sleep_ms(5)
        self.custom_init_nibble(0x03)
        utime.sleep_ms(1)
        self.custom_init_nibble(0x03)
        utime.sleep_ms(1)
        self.custom_init_nibble(0x02) # Umschalten auf 4-Bit
        utime.sleep_ms(1)

        # 3. Jetzt normale Initialisierung der Basisklasse
        super().__init__(num_lines, num_columns)
        
        # Display Settings
        self.hal_write_command(self.LCD_FUNCTION | self.LCD_FUNCTION_2LINES)
        self.hide_cursor()
        self.clear()

    # Hilfsfunktion nur für die Initialisierung
    def custom_init_nibble(self, nibble):
        byte = ((nibble >> 4) & 0x0f) << 4
        # Backlight Bit (3) setzen, Enable (2) toggeln
        # P3=Backlight, P2=Enable, P1=RW, P0=RS
        bl = 0x08 if self.backlight else 0x00
        
        data = byte | bl
        
        # Pulse Enable
        self.i2c.writeto(self.i2c_addr, bytes([data | 0x04]))
        utime.sleep_us(500) # Langes Timing
        self.i2c.writeto(self.i2c_addr, bytes([data]))
        utime.sleep_us(500)

    def hal_write_init_nibble(self, nibble):
        self.custom_init_nibble(nibble)

    def hal_backlight_on(self):
        self.i2c.writeto(self.i2c_addr, bytes([1 << 3]))

    def hal_backlight_off(self):
        self.i2c.writeto(self.i2c_addr, bytes([0]))

    def hal_write_command(self, cmd):
        byte = ((self.backlight << 3) | 0x04 | (cmd & 0xf0))
        self.i2c.writeto(self.i2c_addr, bytes([byte, byte & 0xfb]))
        utime.sleep_us(100) # Verlangsamung für Stabilität
        byte = ((self.backlight << 3) | 0x04 | ((cmd & 0x0f) << 4))
        self.i2c.writeto(self.i2c_addr, bytes([byte, byte & 0xfb]))
        utime.sleep_us(100) # Verlangsamung

    def hal_write_data(self, data):
        byte = (self.backlight << 3) | 0x05 | (data & 0xf0)
        self.i2c.writeto(self.i2c_addr, bytes([byte, byte & 0xfb]))
        utime.sleep_us(100) # Verlangsamung
        byte = (self.backlight << 3) | 0x05 | ((data & 0x0f) << 4)
        self.i2c.writeto(self.i2c_addr, bytes([byte, byte & 0xfb]))
        utime.sleep_us(100) # Verlangsamung