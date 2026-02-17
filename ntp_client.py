"""
NTP (Network Time Protocol) client for precise time synchronization
"""

import time
import usocket
import ustruct
from config import Config


class NTPClient:
    """High-precision NTP client with latency compensation"""

    NTP_EPOCH_DELTA = 2208988800
    NTP_PORT = 123
    NTP_TIMEOUT_SEC = 1
    NTP_VERSION = 3
    NTP_MODE_CLIENT = 3

    def __init__(self, server=Config.DEFAULT_NTP_SERVER):
        self.server = server

    def _query_ntp_server(self):
        """Execute single NTP query with round-trip measurement

        Returns:
            tuple: (seconds, milliseconds, latency_ms, tick_reference) or (None, None, 0, 0)
        """
        query = bytearray(48)
        query[0] = (self.NTP_VERSION << 3) | self.NTP_MODE_CLIENT

        try:
            addr = usocket.getaddrinfo(self.server, self.NTP_PORT)[0][-1]
            sock = usocket.socket(usocket.AF_INET, usocket.SOCK_DGRAM)
            sock.settimeout(self.NTP_TIMEOUT_SEC)

            tick_start = time.ticks_ms()
            sock.sendto(query, addr)
            response = sock.recv(48)
            tick_end = time.ticks_ms()
            sock.close()

            latency = time.ticks_diff(tick_end, tick_start) // 2

            seconds = self._extract_seconds(response)
            milliseconds = self._extract_milliseconds(response)

            return seconds, milliseconds, latency, tick_end

        except Exception:
            return None, None, 0, 0

    def _extract_seconds(self, response):
        """Extract seconds from NTP transmit timestamp"""
        seconds_raw = ustruct.unpack("!I", response[40:44])[0]
        return seconds_raw - self.NTP_EPOCH_DELTA

    def _extract_milliseconds(self, response):
        """Extract milliseconds from NTP transmit timestamp fraction"""
        fraction_raw = ustruct.unpack("!I", response[44:48])[0]
        return int((fraction_raw / 4294967296.0) * 1000)

    def get_precise_time(self, samples=Config.NTP_SAMPLES):
        """Query NTP server multiple times and return best result

        Args:
            samples: Number of queries to perform

        Returns:
            tuple: (seconds, milliseconds, latency, tick_reference) with lowest latency
        """
        results = []

        for _ in range(samples):
            result = self._query_ntp_server()
            if result[0] is not None:
                results.append(result)
            time.sleep_ms(Config.NTP_SAMPLE_DELAY_MS)

        if not results:
            return None, None, 0, 0

        results.sort(key=lambda x: x[2])
        return results[0]
