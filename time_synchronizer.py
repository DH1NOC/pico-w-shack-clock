"""
Time source synchronization coordinator with priority management
"""

import time
import machine
from config import Config
from time_utils import TimeUtilities


class TimeSynchronizer:
    """Coordinate time synchronization from GPS, NTP, and RTC sources"""
    
    def __init__(self, gps, ntp, rtc, display):
        self.gps = gps
        self.ntp = ntp
        self.rtc = rtc
        self.display = display
        
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
        if self._try_gps_sync():
            return
        
        if self._try_ntp_sync():
            return
        
        self._fallback_to_rtc()
        
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
            
        if not self._should_sync_gps():
            return True
            
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
        
    def _fallback_to_rtc(self):
        """Use RTC as fallback when no other source is available"""
        no_gps = not self.gps or not self.gps.has_fix
        if no_gps:
            self.current_source = Config.TIME_SOURCE_RTC
            
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
