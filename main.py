"""
DH1NOC Shack Clock - Precision NTP-synchronized clock for Raspberry Pi Pico W
Version: 2.0 (Clean Code Refactored)
Author: DH1NOC
Features: GPS (Priority 1), NTP (Priority 2), RTC Fallback (Priority 3)
"""

import time
import json
from config import Config
from hardware_manager import HardwareManager
from time_synchronizer import TimeSynchronizer
from wifi_manager import WifiManager
from time_utils import TimeUtilities


class ShackClock:
    """Main application controller for precision timekeeping"""

    DISPLAY_UPDATE_INTERVAL_MS = 1000
    DISPLAY_UPDATE_INTERVAL_DEBUG_MS = 200
    GPS_POLL_INTERVAL_MS = 10
    MAIN_LOOP_SLEEP_MS = 20

    def __init__(self):
        self.config = self._load_configuration()
        self.debug_mode = self.config.get('debug_mode', Config.DEBUG_MODE)
        self.animation_counter = 0
        self.last_second = -1

        self._initialize_hardware()
        self._initialize_network()
        self._initialize_time_sync()

        if self.hardware.display:
            self.hardware.display.lcd.clear()

    def _load_configuration(self):
        """Load configuration from config.json"""
        try:
            with open('config.json', 'r') as f:
                return json.load(f)
        except Exception:
            return self._get_default_config()

    def _get_default_config(self):
        """Provide default configuration if file is missing"""
        return {
            "wifi": [],
            "ntp_server": Config.DEFAULT_NTP_SERVER,
            "sync_interval_min": Config.DEFAULT_SYNC_INTERVAL_MIN,
            "gps_enabled": Config.GPS_ENABLED,
            "debug_mode": Config.DEBUG_MODE
        }

    def _initialize_hardware(self):
        """Initialize all hardware components"""
        self.hardware = HardwareManager(self.config)
        self.hardware.initialize_all()

    def _initialize_network(self):
        """Initialize WiFi connection"""
        self.wifi = WifiManager()
        wifi_networks = self.config.get('wifi', [])

        if len(wifi_networks) > 0:
            first_network = wifi_networks[0]
            self.wifi.connect(first_network['ssid'], first_network['password'])

    def _initialize_time_sync(self):
        """Initialize time synchronization coordinator"""
        self.time_sync = TimeSynchronizer(
            self.hardware.get_gps(),
            self.hardware.get_ntp(),
            self.hardware.get_rtc(),
            self.hardware.get_display(),
            self.wifi
        )

        sync_interval = self.config.get('sync_interval_min', Config.DEFAULT_SYNC_INTERVAL_MIN)
        self.time_sync.set_ntp_interval(sync_interval)
        self.time_sync.load_rtc_time()

    def _update_display(self):
        """Update display based on current mode"""
        if not self.hardware.display:
            return

        if self._is_debug_mode():
            self._show_debug_screen()
        else:
            self._show_normal_screen()

    def _is_debug_mode(self):
        """Check if debug mode is active"""
        return self.debug_mode == Config.DEBUG_MODE_GPS

    def _show_debug_screen(self):
        """Display GPS debug information"""
        gps = self.hardware.get_gps()
        gps_status = gps.get_status() if gps else None
        self.hardware.display.show_gps_debug(gps_status, self.animation_counter)
        self.animation_counter += 1

    def _show_normal_screen(self):
        """Display normal time screen"""
        utc_time = time.gmtime()
        local_time, is_dst = TimeUtilities.get_cet_time_and_dst(utc_time)

        gps = self.hardware.get_gps()
        gps_status = gps.get_status() if gps else None
        time_source = self.time_sync.get_current_source()

        self.hardware.display.update_time_display(
            local_time, utc_time, is_dst, time_source, gps_status
        )

    def run(self):
        """Main application loop with time synchronization and display updates"""
        update_interval = self._get_display_update_interval()
        last_display_update = 0

        while True:
            self._poll_gps()

            now_ms = time.ticks_ms()

            if self._is_debug_mode():
                last_display_update = self._run_debug_mode(now_ms, last_display_update, update_interval)
                continue

            self._run_normal_mode()
            time.sleep_ms(self.MAIN_LOOP_SLEEP_MS)

    def _get_display_update_interval(self):
        """Get display update interval based on mode"""
        if self._is_debug_mode():
            return self.DISPLAY_UPDATE_INTERVAL_DEBUG_MS
        return self.DISPLAY_UPDATE_INTERVAL_MS

    def _poll_gps(self):
        """Poll GPS UART to prevent buffer overflow"""
        gps = self.hardware.get_gps()
        if gps:
            gps.update()

    def _run_debug_mode(self, now_ms, last_update, interval):
        """Run debug mode loop iteration

        Returns:
            int: Updated last_display_update timestamp
        """
        if time.ticks_diff(now_ms, last_update) >= interval:
            self._update_display()
            last_update = now_ms

        time.sleep_ms(self.GPS_POLL_INTERVAL_MS)
        return last_update

    def _run_normal_mode(self):
        """Run normal mode loop iteration"""
        current_second = time.gmtime()[5]

        if current_second != self.last_second:
            self.last_second = current_second
            self._update_display()
            self._maintain_network()
            self._synchronize_time()

    def _maintain_network(self):
        """Maintain WiFi connection"""
        wifi_networks = self.config.get('wifi', [])
        self.wifi.retry_if_needed(wifi_networks)

    def _synchronize_time(self):
        """Execute time synchronization"""
        self.time_sync.synchronize()


def main():
    """Application entry point"""
    clock = ShackClock()
    clock.run()


if __name__ == "__main__":
    main()