"""
Time source synchronization coordinator with priority management
"""

import time
import machine
from config import Config
from time_utils import TimeUtilities


class TimeSynchronizer:
    """Coordinate time synchronization from GPS, NTP, and RTC sources"""

    def __init__(self, gps, ntp, rtc, display, wifi=None):
        self.gps = gps
        self.ntp = ntp
        self.rtc = rtc
        self.display = display
        self.wifi = wifi
        
        self.last_gps_sync = -999999
        self.last_ntp_sync = -999999
        self.gps_sync_interval = 60
        self.ntp_sync_interval = Config.DEFAULT_SYNC_INTERVAL_MIN * 60

        self.current_source = Config.TIME_SOURCE_RTC
        
    def set_ntp_interval(self, minutes):
        """Configure NTP sync interval"""
        self.ntp_sync_interval = minutes * 60
        
    def synchronize(self):
        """Attempt synchronization with priority: GPS > NTP > RTC"""
        # Try synchronization sources
        if not self._try_gps_sync():
            if not self._try_ntp_sync():
                self._check_and_fallback()
        
    def get_current_source(self):
        """Get active time source identifier"""
        return self.current_source
        
    def _try_gps_sync(self):
        """Try synchronizing with GPS (highest priority)"""
        if not self.gps:
            return False

        gps_data = self.gps.get_time_with_timestamp()
        if not gps_data:
            return False

        # GPS hat Fix - als aktive Quelle behandeln
        if self.gps.has_fix:
            self.current_source = Config.TIME_SOURCE_GPS

        if not self._should_sync_gps():
            return self.gps.has_fix

        gps_time, gps_tick_ref = gps_data

        if self._sync_system_time_from_gps(gps_time, gps_tick_ref):
            self.current_source = Config.TIME_SOURCE_GPS
            self.last_gps_sync = time.time()
            return True

        return False
        
    def _should_sync_gps(self):
        """Check if GPS sync interval has elapsed"""
        elapsed = time.time() - self.last_gps_sync
        return elapsed >= self.gps_sync_interval
        
    def _sync_system_time_from_gps(self, gps_time, gps_tick_ref):
        """Synchronize system RTC from GPS with latency compensation"""
        try:
            elapsed_ms = time.ticks_diff(time.ticks_ms(), gps_tick_ref)
            gps_unix = time.mktime(gps_time)
            current_unix = gps_unix + (elapsed_ms // 1000)
            current_ms = elapsed_ms % 1000
            
            wait_ms = 1000 - current_ms
            if wait_ms < 50:
                wait_ms += 1000
                target_unix = current_unix + 1
            else:
                target_unix = current_unix
                
            time.sleep_ms(wait_ms - 10)
            
            adjusted_time = time.gmtime(target_unix)
            self._set_system_rtc(adjusted_time)
            self.rtc.set_time(adjusted_time)
            
            return True
        except Exception:
            return False
            
    def _try_ntp_sync(self):
        """Try synchronizing with NTP (second priority)"""
        if self._gps_has_priority():
            return False

        if not self._should_sync_ntp():
            return False

        # Check WiFi connection before attempting NTP sync
        if self.wifi and not self.wifi.is_connected():
            return False

        try:
            self._show_sync_indicator("*")

            ntp_sec, ntp_ms, latency, tick_ref = self.ntp.get_precise_time()
            
            if ntp_sec is not None:
                time_tuple = TimeUtilities.sync_rtc_precise(ntp_sec, ntp_ms, latency, tick_ref)
                self.rtc.set_time(time_tuple)
                self.last_ntp_sync = time.time()
                self.current_source = Config.TIME_SOURCE_NTP
                self._show_sync_indicator(" ")
                return True
                
            self._show_sync_indicator(" ")
            return False
            
        except Exception:
            self._show_sync_indicator("E")
            return False
            
    def _gps_has_priority(self):
        """Check if GPS has active fix and overrides NTP"""
        return self.gps and self.gps.has_fix
        
    def _should_sync_ntp(self):
        """Check if NTP sync interval has elapsed"""
        elapsed = time.time() - self.last_ntp_sync
        return elapsed >= self.ntp_sync_interval

    def _check_and_fallback(self):
        """Intelligent fallback based on source availability and freshness"""
        # GPS ist aktuell aktiv, aber hat Fix verloren
        if self.current_source == Config.TIME_SOURCE_GPS:
            if not self.gps or not self.gps.has_fix:
                time_since_gps = time.time() - self.last_gps_sync
                if time_since_gps > 60:  # 60 Sekunden ohne GPS-Fix
                    # Versuche zu NTP zu wechseln, falls aktuell
                    if self._is_ntp_current():
                        self.current_source = Config.TIME_SOURCE_NTP
                    else:
                        self.current_source = Config.TIME_SOURCE_RTC

        # NTP ist aktuell aktiv, aber nicht mehr aktuell
        elif self.current_source == Config.TIME_SOURCE_NTP:
            if not self._is_ntp_current():
                self.current_source = Config.TIME_SOURCE_RTC

        # RTC ist aktiv - versuche Upgrade zu NTP falls verfügbar
        elif self.current_source == Config.TIME_SOURCE_RTC:
            if self._is_ntp_current():
                self.current_source = Config.TIME_SOURCE_NTP

    def _is_ntp_current(self):
        """Check if NTP sync is current (within interval)"""
        if self.last_ntp_sync < 0:
            return False
        time_since_ntp = time.time() - self.last_ntp_sync
        return time_since_ntp < self.ntp_sync_interval

    def _set_system_rtc(self, time_tuple):
        """Set Pico's system RTC"""
        machine.RTC().datetime((
            time_tuple[0], time_tuple[1], time_tuple[2], time_tuple[6],
            time_tuple[3], time_tuple[4], time_tuple[5], 0
        ))
        
    def _show_sync_indicator(self, indicator):
        """Display sync status on LCD"""
        if self.display:
            self.display.show_sync_indicator(indicator)
            
    def load_rtc_time(self):
        """Load initial time from hardware RTC at startup"""
        try:
            rtc_time = self.rtc.get_time()
            if rtc_time:
                self._set_system_rtc(rtc_time)
        except Exception:
            pass

    def _report_time_offsets(self):
        """Report RTC offset to GPS and NTP at every full minute (second 0)"""
        current_time = time.gmtime()
        current_second = current_time[5]

        # Only report at second 0 and avoid duplicate reports
        if current_second != 0:
            return

        if current_second == self.last_offset_report_second:
            return

        self.last_offset_report_second = current_second

        # Use single reference point for all calculations
        tick_ref = time.ticks_ms()
        rtc_unix = time.time()

        offsets = []

        # Calculate GPS offset if available
        if self.gps:
            gps_data = self.gps.get_time_with_timestamp()
            if gps_data:
                gps_time, gps_tick_ref = gps_data
                try:
                    # Calculate GPS time at our reference tick
                    gps_unix = time.mktime(gps_time)
                    elapsed_ms = time.ticks_diff(tick_ref, gps_tick_ref)
                    gps_unix_at_ref = gps_unix + (elapsed_ms / 1000.0)

                    # Calculate offset: RTC - GPS (positive means RTC is ahead)
                    total_offset_ms = (rtc_unix - gps_unix_at_ref) * 1000

                    fix_indicator = "FIX" if self.gps.has_fix else "NO_FIX"
                    offsets.append(f"GPS({fix_indicator}): {total_offset_ms:+.0f}ms")
                except Exception as e:
                    offsets.append(f"GPS: ERROR ({e})")

        # Calculate NTP offset if last sync was successful
        if self.last_ntp_sync > 0 and self.ntp:
            try:
                # Query NTP for current time
                ntp_sec, ntp_ms, latency, ntp_tick_ref = self.ntp.get_precise_time()

                if ntp_sec is not None:
                    # Calculate NTP time at our reference tick
                    elapsed_ms = time.ticks_diff(tick_ref, ntp_tick_ref)
                    ntp_unix_at_ref = ntp_sec + (ntp_ms / 1000.0) + (elapsed_ms / 1000.0)

                    # Calculate offset: RTC - NTP (positive means RTC is ahead)
                    total_offset_ms = (rtc_unix - ntp_unix_at_ref) * 1000

                    offsets.append(f"NTP: {total_offset_ms:+.0f}ms")
                else:
                    offsets.append("NTP: N/A")
            except Exception as e:
                offsets.append(f"NTP: ERROR ({e})")

        # Print to console
        if offsets:
            timestamp = "{:04d}-{:02d}-{:02d} {:02d}:{:02d}:{:02d}".format(
                current_time[0], current_time[1], current_time[2],
                current_time[3], current_time[4], current_time[5]
            )
            print(f"[{timestamp}] RTC Offsets: {', '.join(offsets)}")
        else:
            print(f"[{time.gmtime()[3]:02d}:{time.gmtime()[4]:02d}:{time.gmtime()[5]:02d}] No GPS or NTP data available for offset reporting")
