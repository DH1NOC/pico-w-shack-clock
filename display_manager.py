"""
LCD display management module
"""

import time
from config import Config
from qth_locator import QTHLocator


class DisplayManager:
    """Manage LCD display output and animations"""

    def __init__(self, lcd, callsign="DARC"):
        self.lcd = lcd
        self.callsign = callsign

    def _define_custom_char(self, location, charmap):
        """Define custom LCD character in CGRAM

        Args:
            location: Memory slot 0-7
            charmap: 8-byte pattern array
        """
        location &= 0x7
        self.lcd.hal_write_command(self.lcd.LCD_CGRAM | (location << 3))
        time.sleep_ms(1)

        for byte in charmap:
            self.lcd.hal_write_data(byte)
            time.sleep_ms(1)

        self.lcd.move_to(self.lcd.cursor_x, self.lcd.cursor_y)

    def show_boot_animation(self):
        """Display animated startup sequence with radio tower"""
        custom_chars = {
            'tower': bytearray([0x04, 0x0E, 0x0E, 0x04, 0x04, 0x04, 0x1F, 0x00]),
            'wave_r1': bytearray([0x00, 0x04, 0x02, 0x02, 0x02, 0x04, 0x00, 0x00]),
            'wave_r2': bytearray([0x00, 0x11, 0x08, 0x08, 0x08, 0x11, 0x00, 0x00]),
            'wave_r3': bytearray([0x00, 0x11, 0x0A, 0x04, 0x04, 0x0A, 0x11, 0x00]),
            'wave_l1': bytearray([0x00, 0x04, 0x08, 0x08, 0x08, 0x04, 0x00, 0x00]),
            'wave_l2': bytearray([0x00, 0x11, 0x22, 0x22, 0x22, 0x11, 0x00, 0x00]),
            'wave_l3': bytearray([0x00, 0x11, 0x0A, 0x04, 0x04, 0x0A, 0x11, 0x00])
        }

        self._define_custom_char(0, custom_chars['tower'])
        self._define_custom_char(1, custom_chars['wave_r1'])
        self._define_custom_char(2, custom_chars['wave_r2'])
        self._define_custom_char(3, custom_chars['wave_r3'])
        self._define_custom_char(4, custom_chars['wave_l1'])
        self._define_custom_char(5, custom_chars['wave_l2'])
        self._define_custom_char(6, custom_chars['wave_l3'])

        self.lcd.clear()
        self.lcd.move_to(4, 0)
        self.lcd.putstr("DH1NOC CLOCK")
        self.lcd.move_to(3, 3)
        self.lcd.putstr("System Start...")
        self.lcd.move_to(4, 2)
        self.lcd.putstr("Version  1.4")

        self._animate_radio_waves()
        time.sleep(1.5)
        self.lcd.clear()

    def _animate_radio_waves(self):
        """Animate radio wave propagation from tower"""
        center = 9

        self.lcd.move_to(center, 1)
        self.lcd.putchar(chr(0))
        time.sleep(0.5)

        self.lcd.move_to(center - 1, 1)
        self.lcd.putchar(chr(4))
        self.lcd.move_to(center + 1, 1)
        self.lcd.putchar(chr(1))
        time.sleep(0.3)

        self.lcd.move_to(center - 2, 1)
        self.lcd.putchar(chr(5))
        self.lcd.move_to(center + 2, 1)
        self.lcd.putchar(chr(2))
        time.sleep(0.3)

        self.lcd.move_to(center - 3, 1)
        self.lcd.putchar(chr(6))
        self.lcd.move_to(center + 3, 1)
        self.lcd.putchar(chr(3))

    def update_time_display(self, local_time, utc_time, is_dst, time_source, gps_status=None):
        """Update main clock display

        Args:
            local_time: Local CET/CEST time tuple
            utc_time: UTC time tuple
            is_dst: True if daylight saving time is active
            time_source: 'GPS', 'NTP', or 'RTC'
            gps_status: Optional GPS status dict
        """
        weekday = self._format_weekday(local_time[6])
        timezone_labels = self._get_timezone_labels(is_dst)

        self._display_date_line(local_time, weekday)
        self._display_local_time_line(local_time, timezone_labels['local'])
        self._display_utc_time_line(utc_time, timezone_labels['utc'])
        self._display_source_line(time_source, gps_status)

    def _format_weekday(self, weekday_index):
        """Get localized weekday abbreviation"""
        if 0 <= weekday_index <= 6:
            return Config.WEEKDAYS[weekday_index]
        return "--"

    def _get_timezone_labels(self, is_dst):
        """Get timezone labels based on DST status"""
        if is_dst:
            return {'local': 'MESZ:', 'utc': 'UTC: '}
        return {'local': 'MEZ: ', 'utc': 'UTC: '}

    def _display_date_line(self, local_time, weekday):
        """Display date and callsign on line 0"""
        self.lcd.move_to(0, 0)
        self.lcd.putstr("{:s} {:02d}.{:02d}.{:04d}".format(
            weekday, local_time[2], local_time[1], local_time[0]
        ))

        callsign_pos = Config.LCD_COLS - len(self.callsign)
        self.lcd.move_to(callsign_pos, 0)
        self.lcd.putstr(self.callsign)

    def _display_local_time_line(self, local_time, label):
        """Display local time on line 1"""
        self.lcd.move_to(0, 1)
        self.lcd.putstr("{:s} {:02d}:{:02d}.{:02d}    ".format(
            label, local_time[3], local_time[4], local_time[5]
        ))

    def _display_utc_time_line(self, utc_time, label):
        """Display UTC time on line 2"""
        self.lcd.move_to(0, 2)
        self.lcd.putstr("{:s} {:02d}:{:02d}       ".format(
            label, utc_time[3], utc_time[4]
        ))

    def _display_source_line(self, time_source, gps_status):
        """Display time source and GPS info on line 3"""
        self.lcd.move_to(0, 3)

        if time_source == Config.TIME_SOURCE_GPS and gps_status:
            self._display_gps_source(gps_status)
        elif time_source == Config.TIME_SOURCE_NTP:
            self.lcd.putstr("WLAN                ")
        else:
            self.lcd.putstr("RTC                 ")

    def _display_gps_source(self, gps_status):
        """Display GPS satellite count and QTH locator"""
        sats = gps_status.get('satellites', 0)
        lat = gps_status.get('latitude', 0.0)
        lon = gps_status.get('longitude', 0.0)

        locator = QTHLocator.calculate(lat, lon)
        left_part = "GPS S:{:02d}".format(sats)
        padding = Config.LCD_COLS - len(left_part) - len(locator)

        line = left_part + " " * padding + locator
        self.lcd.putstr(line)

    def show_sync_indicator(self, status):
        """Display sync status indicator in corner

        Args:
            status: ' ' (idle), '*' (syncing), 'E' (error)
        """
        self.lcd.move_to(19, 3)
        self.lcd.putstr(status)

    def show_gps_debug(self, gps_status, animation_counter=0):
        """Display GPS diagnostic information

        Args:
            gps_status: GPS status dict
            animation_counter: Frame counter for animations
        """
        if not gps_status:
            self._display_gps_not_initialized()
            return

        if gps_status.get('has_fix', False):
            self._display_gps_locked(gps_status)
        else:
            self._display_gps_searching(gps_status, animation_counter)

    def _display_gps_not_initialized(self):
        """Display GPS initialization error"""
        self.lcd.move_to(0, 0)
        self.lcd.putstr("GPS Debug Mode      ")
        self.lcd.move_to(0, 1)
        self.lcd.putstr("GPS not initialized ")
        self.lcd.move_to(0, 2)
        self.lcd.putstr("                    ")
        self.lcd.move_to(0, 3)
        self.lcd.putstr("                    ")

    def _display_gps_searching(self, gps_status, animation_counter):
        """Display GPS search status with animation"""
        anim_chars = ["|", "/", "-", "\\"]
        anim_char = anim_chars[animation_counter % 4]

        satellites = gps_status.get('satellites', 0)
        frame_count = gps_status.get('frame_count', 0)

        self.lcd.move_to(0, 0)
        self.lcd.putstr("GPS Suche...       " + anim_char)

        self.lcd.move_to(0, 1)
        self.lcd.putstr("Sats: {:02d}           ".format(satellites))

        self.lcd.move_to(0, 2)
        self.lcd.putstr("Warte auf Fix...    ")

        self.lcd.move_to(0, 3)
        self.lcd.putstr("Pakete: {:<8d}    ".format(frame_count))

    def _display_gps_locked(self, gps_status):
        """Display GPS lock status with position data"""
        satellites = gps_status.get('satellites', 0)
        latitude = gps_status.get('latitude', 0.0)
        longitude = gps_status.get('longitude', 0.0)
        altitude = gps_status.get('altitude', 0.0)
        frame_count = gps_status.get('frame_count', 0)

        self.lcd.move_to(0, 0)
        self.lcd.putstr("GPS LOCK: OK (3D)   ")

        self.lcd.move_to(0, 1)
        self.lcd.putstr("Sats: {:02d} QUAL:High ".format(satellites))

        self.lcd.move_to(0, 2)
        lat_str = "{:.3f}".format(latitude)
        lon_str = "{:.3f}".format(longitude)
        line = "La:{} Lo:{}".format(lat_str, lon_str)
        self.lcd.putstr((line + " " * 20)[:20])

        self.lcd.move_to(0, 3)
        alt_str = "{:.1f}m".format(altitude)
        frame_str = "F:{:d}".format(frame_count)
        padding = 20 - len(alt_str) - len(frame_str)
        if padding < 1:
            padding = 1
        line = alt_str + (" " * padding) + frame_str
        self.lcd.putstr(line[:20])
