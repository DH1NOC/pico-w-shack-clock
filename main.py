import machine
import time
import json
import network
import usocket
import ustruct
from machine import I2C, Pin
from pico_i2c_lcd import I2cLcd

# --- KONFIGURATION ---
I2C_ADDR = 0x27        
DS3231_ADDR = 0x68     
I2C_NUM = 0
I2C_SDA = 0
I2C_SCL = 1
LCD_ROWS = 4
LCD_COLS = 20

WEEKDAYS = ["Mo", "Di", "Mi", "Do", "Fr", "Sa", "So"]

# --- DS3231 TREIBER ---
class DS3231:
    def __init__(self, i2c):
        self.i2c = i2c
        self.addr = DS3231_ADDR
    def _dec2bcd(self, val): return (val // 10 * 16) + (val % 10)
    def _bcd2dec(self, val): return (val // 16 * 10) + (val % 16)
    def get_time(self):
        try:
            data = self.i2c.readfrom_mem(self.addr, 0, 7)
            ss, mm, hh = self._bcd2dec(data[0]), self._bcd2dec(data[1]), self._bcd2dec(data[2])
            wday, mday, mon = self._bcd2dec(data[3]), self._bcd2dec(data[4]), self._bcd2dec(data[5] & 0x1F)
            year = self._bcd2dec(data[6]) + 2000
            return (year, mon, mday, hh, mm, ss, wday - 1, 0)
        except: return None
    def set_time(self, t):
        try:
            data = bytearray(7)
            data[0], data[1], data[2] = self._dec2bcd(t[5]), self._dec2bcd(t[4]), self._dec2bcd(t[3])
            data[3], data[4], data[5] = self._dec2bcd(t[6] + 1), self._dec2bcd(t[2]), self._dec2bcd(t[1])
            data[6] = self._dec2bcd(t[0] - 2000)
            self.i2c.writeto_mem(self.addr, 0, data)
        except: pass

# --- NTP CLIENT ---
def get_ntp_time_precision(host="pool.ntp.org"):
    NTP_DELTA = 2208988800
    NTP_QUERY = bytearray(48)
    NTP_QUERY[0] = 0x1B
    
    try:
        addr = usocket.getaddrinfo(host, 123)[0][-1]
        s = usocket.socket(usocket.AF_INET, usocket.SOCK_DGRAM)
        s.settimeout(1) 
        
        ticks_start = time.ticks_ms()
        s.sendto(NTP_QUERY, addr)
        msg = s.recv(48)
        ticks_end = time.ticks_ms()
        s.close()
        
        latency_ms = time.ticks_diff(ticks_end, ticks_start)
    except:
        return None, None, 0

    val = ustruct.unpack("!I", msg[40:44])[0]
    frac = ustruct.unpack("!I", msg[44:48])[0]
    
    t_seconds = val - NTP_DELTA
    t_ms = int((frac / 4294967296) * 1000)
    
    return t_seconds, t_ms, (latency_ms // 2)

# --- HELFER ---
def load_config():
    try:
        with open('config.json', 'r') as f: return json.load(f)
    except: return {"wifi": [], "ntp_server": "pool.ntp.org", "sync_interval_min": 60}

def connect_wifi_bg(config):
    """Verbindet im Hintergrund (Feuer & Vergessen)"""
    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)
    if wlan.isconnected(): return wlan
    try: wlan.config(pm=0xa11140)
    except: pass
    if len(config['wifi']) > 0:
        try:
            if not wlan.isconnected():
                wlan.connect(config['wifi'][0]['ssid'], config['wifi'][0]['password'])
        except: pass
    return wlan

def get_cet_time_and_dst(utc_time):
    year, month, mday, hour = utc_time[0], utc_time[1], utc_time[2], utc_time[3]
    
    def last_sunday(m, y):
        import time
        last_day_wday = time.gmtime(time.mktime((y, m, 31, 12, 0, 0, 0, 0)))[6]
        return 31 - ((last_day_wday + 1) % 7)

    dst_start = last_sunday(3, year)
    dst_end = last_sunday(10, year)

    is_dst = False
    if month > 3 and month < 10: is_dst = True
    elif month == 3:
        if mday > dst_start: is_dst = True
        elif mday == dst_start and hour >= 1: is_dst = True
    elif month == 10:
        if mday < dst_end: is_dst = True
        elif mday == dst_end and hour < 1: is_dst = True

    offset = 2 if is_dst else 1
    unixtime = time.mktime(utc_time) + (offset * 3600)
    return time.gmtime(unixtime), is_dst

# --- BOOT ANIMATION HELFER ---
def define_char(lcd, location, charmap):
    location &= 0x7
    lcd.hal_write_command(lcd.LCD_CGRAM | (location << 3))
    time.sleep_ms(1)
    for i in range(8):
        lcd.hal_write_data(charmap[i])
        time.sleep_ms(1)
    lcd.move_to(lcd.cursor_x, lcd.cursor_y)

def boot_animation(lcd):
    """Zeigt eine kurze Funkwellen-Animation (Abstrahlend)"""
    tower = bytearray([0x04, 0x0E, 0x0E, 0x04, 0x04, 0x04, 0x1F, 0x00])
    w_r1 = bytearray([0x00, 0x04, 0x02, 0x02, 0x02, 0x04, 0x00, 0x00])
    w_r2 = bytearray([0x00, 0x11, 0x08, 0x08, 0x08, 0x11, 0x00, 0x00])
    w_r3 = bytearray([0x00, 0x11, 0x0A, 0x04, 0x04, 0x0A, 0x11, 0x00])
    w_l1 = bytearray([0x00, 0x04, 0x08, 0x08, 0x08, 0x04, 0x00, 0x00])
    w_l2 = bytearray([0x00, 0x11, 0x22, 0x22, 0x22, 0x11, 0x00, 0x00])
    w_l3 = bytearray([0x00, 0x11, 0x0A, 0x04, 0x04, 0x0A, 0x11, 0x00])

    define_char(lcd, 0, tower)
    define_char(lcd, 1, w_r1)
    define_char(lcd, 2, w_r2)
    define_char(lcd, 3, w_r3)
    define_char(lcd, 4, w_l1)
    define_char(lcd, 5, w_l2)
    define_char(lcd, 6, w_l3)

    lcd.clear()
    lcd.move_to(5, 0); lcd.putstr("DARC CLOCK")
    lcd.move_to(3, 3); lcd.putstr("System Start...")
    
    center = 9
    lcd.move_to(center, 1); lcd.putchar(chr(0)) 
    time.sleep(0.5)
    
    lcd.move_to(center-1, 1); lcd.putchar(chr(4))
    lcd.move_to(center+1, 1); lcd.putchar(chr(1))
    time.sleep(0.3)

    lcd.move_to(center-2, 1); lcd.putchar(chr(5))
    lcd.move_to(center+2, 1); lcd.putchar(chr(2))
    time.sleep(0.3)
    
    lcd.move_to(center-3, 1); lcd.putchar(chr(6))
    lcd.move_to(center+3, 1); lcd.putchar(chr(3))
    
    time.sleep(1.5)
    lcd.clear()

# --- SETUP ---
i2c = I2C(I2C_NUM, sda=Pin(I2C_SDA), scl=Pin(I2C_SCL), freq=100000)

try:
    lcd = I2cLcd(i2c, I2C_ADDR, LCD_ROWS, LCD_COLS)
    boot_animation(lcd)
except: pass

rtc_mod = DS3231(i2c)
config = load_config()

# RTC Zeit lesen (Sofort verfügbar)
try:
    ds_t = rtc_mod.get_time()
    if ds_t: machine.RTC().datetime((ds_t[0], ds_t[1], ds_t[2], ds_t[6], ds_t[3], ds_t[4], ds_t[5], 0))
except: pass

# WLAN im Hintergrund anstoßen (Kein Warten!)
wlan = network.WLAN(network.STA_IF)
wlan.active(True)
if len(config['wifi']) > 0:
    try:
        wlan.config(pm=0xa11140) # Power Management aus
        # connect() ist bei Pico W non-blocking, wenn wir nicht auf Status warten
        wlan.connect(config['wifi'][0]['ssid'], config['wifi'][0]['password'])
    except: pass

lcd.clear()

# Variablen
last_sync_ts = -999999
sync_interval = config.get("sync_interval_min", 60) * 60
last_wifi_retry = time.time()
last_second_tick = time.gmtime()[5]

# --- LOOP ---
while True:
    current_t_utc = time.gmtime()
    current_sec = current_t_utc[5]

    if current_sec == last_second_tick:
        time.sleep_ms(10)
        continue
    
    last_second_tick = current_sec
    local_t, is_dst = get_cet_time_and_dst(current_t_utc)
    wday_str = WEEKDAYS[local_t[6]] if 0 <= local_t[6] <= 6 else "--"
    
    if is_dst: label_loc, label_utc = "MESZ:", "UTC: "
    else:      label_loc, label_utc = "MEZ: ", "UTC: "

    # Anzeige
    lcd.move_to(0, 0)
    lcd.putstr("{:s} {:02d}.{:02d}.{:04d}".format(wday_str, local_t[2], local_t[1], local_t[0]))
    lcd.move_to(16, 0); lcd.putstr("DARC")
    
    lcd.move_to(0, 1)
    lcd.putstr("{:s} {:02d}:{:02d}.{:02d}    ".format(label_loc, local_t[3], local_t[4], local_t[5]))
    
    lcd.move_to(0, 2)
    lcd.putstr("{:s} {:02d}:{:02d}       ".format(label_utc, current_t_utc[3], current_t_utc[4]))
    
    lcd.move_to(0, 3)
    if wlan.isconnected():
        src_str = "WLAN"
    else:
        src_str = "RTC "
    lcd.putstr("T-Sync over: {:s}  ".format(src_str))

    # Tasks
    now = time.time()
    
    # Retry wenn WLAN weg ist (alle 5 min)
    if not wlan.isconnected() and (now - last_wifi_retry) > 300:
        last_wifi_retry = now
        connect_wifi_bg(config)

    # NTP Sync (nur wenn verbunden)
    if wlan.isconnected():
        if (now - last_sync_ts) > sync_interval:
            try:
                lcd.move_to(19, 3); lcd.putstr("*")
                ntp_sec, ntp_ms, latency_comp = get_ntp_time_precision(config['ntp_server'])
                if ntp_sec is not None:
                    total_ms = ntp_ms + latency_comp
                    if total_ms >= 1000:
                        ntp_sec += 1
                        total_ms -= 1000
                    
                    if total_ms >= 500: sec_to_set = ntp_sec + 1
                    else:               sec_to_set = ntp_sec
                    
                    tm = time.gmtime(sec_to_set)
                    machine.RTC().datetime((tm[0], tm[1], tm[2], tm[6], tm[3], tm[4], tm[5], 0))
                    rtc_mod.set_time(tm)
                    last_sync_ts = time.time()
                lcd.move_to(19, 3); lcd.putstr(" ")
            except:
                lcd.move_to(19, 3); lcd.putstr("E")