import time

class LcdApi:
    Implements_shift_left = True
    Implements_shift_right = True
    Implements_cursor_move_left = True
    Implements_cursor_move_right = True
    Implements_scroll_left = True
    Implements_scroll_right = True
    Implements_backlight = True
    Implements_custom_chars = True
    Implements_blink_cursor_on = True
    Implements_blink_cursor_off = True
    Implements_display_on = True
    Implements_display_off = True
    Implements_cursor_on = True
    Implements_cursor_off = True

    LCD_CLR = 0x01
    LCD_HOME = 0x02
    LCD_ENTRY_MODE = 0x04
    LCD_ENTRY_INC = 0x02
    LCD_ENTRY_SHIFT = 0x01
    LCD_ON_CTRL = 0x08
    LCD_ON_DISPLAY = 0x04
    LCD_ON_CURSOR = 0x02
    LCD_ON_BLINK = 0x01
    LCD_MOVE = 0x10
    LCD_MOVE_DISP = 0x08
    LCD_MOVE_RIGHT = 0x04
    LCD_FUNCTION = 0x20
    LCD_FUNCTION_8BIT = 0x10
    LCD_FUNCTION_2LINES = 0x08
    LCD_FUNCTION_10DOTS = 0x04
    LCD_FUNCTION_RESET = 0x30
    LCD_CGRAM = 0x40
    LCD_DDRAM = 0x80
    LCD_RS_CMD = 0
    LCD_RS_DATA = 1
    LCD_RW_WRITE = 0
    LCD_RW_READ = 1

    def __init__(self, num_lines, num_columns):
        self.num_lines = num_lines
        if num_lines > 4:
            self.num_lines = 4
        self.num_columns = num_columns
        if num_columns > 40:
            self.num_columns = 40
        self.cursor_x = 0
        self.cursor_y = 0
        self.implied_newline = False
        self.backlight = True
        self.display_off()
        self.backlight_on()
        self.clear()
        self.hal_write_command(self.LCD_ENTRY_MODE | self.LCD_ENTRY_INC)
        self.hide_cursor()
        self.display_on()

    def clear(self):
        self.hal_write_command(self.LCD_CLR)
        self.hal_write_command(self.LCD_HOME)
        self.cursor_x = 0
        self.cursor_y = 0

    def show_cursor(self):
        self.hal_write_command(self.LCD_ON_CTRL | self.LCD_ON_DISPLAY |
                               self.LCD_ON_CURSOR)

    def hide_cursor(self):
        self.hal_write_command(self.LCD_ON_CTRL | self.LCD_ON_DISPLAY)

    def blink_cursor_on(self):
        self.hal_write_command(self.LCD_ON_CTRL | self.LCD_ON_DISPLAY |
                               self.LCD_ON_CURSOR | self.LCD_ON_BLINK)

    def blink_cursor_off(self):
        self.hal_write_command(self.LCD_ON_CTRL | self.LCD_ON_DISPLAY |
                               self.LCD_ON_CURSOR)

    def display_on(self):
        self.hal_write_command(self.LCD_ON_CTRL | self.LCD_ON_DISPLAY)

    def display_off(self):
        self.hal_write_command(self.LCD_ON_CTRL)

    def backlight_on(self):
        self.backlight = True
        self.hal_backlight_on()

    def backlight_off(self):
        self.backlight = False
        self.hal_backlight_off()

    def move_to(self, cursor_x, cursor_y):
        self.cursor_x = cursor_x
        self.cursor_y = cursor_y
        addr = cursor_x & 0x3f
        if cursor_y & 1:
            addr += 0x40
        if cursor_y & 2:
            addr += 0x14
        self.hal_write_command(self.LCD_DDRAM | addr)

    def putchar(self, char):
        if char == '\n':
            if self.implied_newline:
                pass
            else:
                self.implied_newline = True
                self.cursor_x = 0
                self.cursor_y += 1
                if self.cursor_y >= self.num_lines:
                    self.cursor_y = 0
                self.move_to(self.cursor_x, self.cursor_y)
            return
        self.implied_newline = False
        self.hal_write_data(ord(char))
        self.cursor_x += 1
        if self.cursor_x >= self.num_columns:
            self.cursor_x = 0
            self.cursor_y += 1
            if self.cursor_y >= self.num_lines:
                self.cursor_y = 0
            self.move_to(self.cursor_x, self.cursor_y)

    def putstr(self, string):
        for char in string:
            self.putchar(char)

    def hal_backlight_on(self):
        pass

    def hal_backlight_off(self):
        pass

    def hal_write_command(self, cmd):
        pass

    def hal_write_data(self, data):
        pass