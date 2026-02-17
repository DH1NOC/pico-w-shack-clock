"""
WiFi connection management with automatic reconnection
"""

import time
import network
from config import Config


class WifiManager:
    """Manage WiFi connectivity with retry logic"""

    POWER_MANAGEMENT_OFF = 0xa11140

    def __init__(self):
        self.wlan = network.WLAN(network.STA_IF)
        self.wlan.active(True)
        self.last_retry = 0
        self._disable_power_management()

    def _disable_power_management(self):
        """Disable WiFi power management for stability"""
        try:
            self.wlan.config(pm=self.POWER_MANAGEMENT_OFF)
        except Exception:
            pass

    def connect(self, ssid, password):
        """Initiate WiFi connection (non-blocking)

        Args:
            ssid: Network SSID
            password: Network password
        """
        if not self.is_connected():
            try:
                self.wlan.connect(ssid, password)
            except Exception:
                pass

    def is_connected(self):
        """Check WiFi connection status

        Returns:
            bool: True if connected
        """
        return self.wlan.isconnected()

    def retry_if_needed(self, wifi_config):
        """Attempt reconnection if disconnected and interval elapsed

        Args:
            wifi_config: List of WiFi configuration dicts
        """
        if self._should_retry() and len(wifi_config) > 0:
            self.last_retry = time.time()
            self.connect(wifi_config[0]['ssid'], wifi_config[0]['password'])

    def _should_retry(self):
        """Check if retry interval has elapsed"""
        if self.is_connected():
            return False

        elapsed = time.time() - self.last_retry
        return elapsed > Config.WIFI_RETRY_INTERVAL_SEC
