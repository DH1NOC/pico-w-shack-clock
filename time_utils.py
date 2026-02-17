"""
Time conversion and timezone utilities for CET/CEST handling
"""

import time
import machine
from config import Config


class TimeUtilities:
    """Time conversion and timezone management"""

    MIN_WAIT_MS = 50

    @staticmethod
    def sync_rtc_precise(ntp_seconds, ntp_ms, latency_comp, ntp_tick_ref):
        """Synchronize RTC at next second boundary with latency compensation

        Args:
            ntp_seconds: Unix timestamp from NTP
            ntp_ms: Millisecond fraction
            latency_comp: Network latency in ms
            ntp_tick_ref: Tick reference when time was received

        Returns:
            tuple: Time tuple that was set in RTC
        """
        elapsed_ms = time.ticks_diff(time.ticks_ms(), ntp_tick_ref)
        total_ms = ntp_ms + latency_comp + elapsed_ms

        ntp_seconds += total_ms // 1000
        total_ms = total_ms % 1000

        wait_ms = 1000 - total_ms

        if wait_ms < TimeUtilities.MIN_WAIT_MS:
            wait_ms += 1000
            target_second = ntp_seconds + 1
        else:
            target_second = ntp_seconds

        time.sleep_ms(wait_ms - Config.RTC_SET_COMPENSATION_MS)

        time_tuple = time.gmtime(target_second)
        TimeUtilities._set_machine_rtc(time_tuple)

        return time_tuple

    @staticmethod
    def _set_machine_rtc(time_tuple):
        """Set Raspberry Pi Pico RTC"""
        machine.RTC().datetime((
            time_tuple[0], time_tuple[1], time_tuple[2], time_tuple[6],
            time_tuple[3], time_tuple[4], time_tuple[5], 0
        ))

    @staticmethod
    def get_cet_time_and_dst(utc_time):
        """Convert UTC to CET/CEST with automatic DST detection

        Args:
            utc_time: UTC time tuple

        Returns:
            tuple: (local_time_tuple, is_dst)
        """
        year = utc_time[0]
        month = utc_time[1]
        day = utc_time[2]
        hour = utc_time[3]

        dst_start = TimeUtilities._last_sunday_of_month(3, year)
        dst_end = TimeUtilities._last_sunday_of_month(10, year)

        is_dst = TimeUtilities._is_in_dst_period(month, day, hour, dst_start, dst_end)

        offset_hours = 2 if is_dst else 1
        unix_time = time.mktime(utc_time) + (offset_hours * 3600)
        local_time = time.gmtime(unix_time)

        return local_time, is_dst

    @staticmethod
    def _last_sunday_of_month(month, year):
        """Calculate day of month for last Sunday

        Args:
            month: Month number (1-12)
            year: Year

        Returns:
            int: Day of month (1-31)
        """
        last_day = time.gmtime(time.mktime((year, month, 31, 12, 0, 0, 0, 0)))
        last_weekday = last_day[6]
        return 31 - ((last_weekday + 1) % 7)

    @staticmethod
    def _is_in_dst_period(month, day, hour, dst_start_day, dst_end_day):
        """Check if date/time falls within DST period

        DST in Central Europe: Last Sunday March 02:00 - Last Sunday October 03:00

        Args:
            month: Month (1-12)
            day: Day of month
            hour: Hour (0-23)
            dst_start_day: Day of March when DST starts
            dst_end_day: Day of October when DST ends

        Returns:
            bool: True if in DST period
        """
        if month > 3 and month < 10:
            return True
        elif month == 3:
            if day > dst_start_day:
                return True
            elif day == dst_start_day and hour >= 1:
                return True
        elif month == 10:
            if day < dst_end_day:
                return True
            elif day == dst_end_day and hour < 1:
                return True

        return False
