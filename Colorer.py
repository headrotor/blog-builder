

#!/usr/bin/env python
# encoding: utf-8

"""
Colorer.py: Logging Output Colorizer

This module provides functionality to add color to logging output in the terminal.
It achieves this by patching the `logging.StreamHandler.emit` method to inject
platform-specific color codes (Windows API calls or ANSI escape sequences).
"""

import logging
import platform
import sys # Added to get specific logging levels for clarity

# --- Constants for Windows Console Colors (from wincon.h and winbase.h) ---
# These are bit flags that can be combined to set foreground and background colors.
# Standard Handle Identifiers
STD_INPUT_HANDLE = -10
STD_OUTPUT_HANDLE = -11
STD_ERROR_HANDLE = -12

# Foreground Colors (text color)
FOREGROUND_BLACK     = 0x0000
FOREGROUND_BLUE      = 0x0001
FOREGROUND_GREEN     = 0x0002
FOREGROUND_CYAN      = 0x0003 # Blue | Green
FOREGROUND_RED       = 0x0004
FOREGROUND_MAGENTA   = 0x0005 # Blue | Red
FOREGROUND_YELLOW    = 0x0006 # Green | Red
FOREGROUND_GREY      = 0x0007 # Blue | Green | Red (standard white/grey)
FOREGROUND_INTENSITY = 0x0008 # text color is intensified (brighter).

# Background Colors
BACKGROUND_BLACK     = 0x0000
BACKGROUND_BLUE      = 0x0010
BACKGROUND_GREEN     = 0x0020
BACKGROUND_CYAN      = 0x0030
BACKGROUND_RED       = 0x0040
BACKGROUND_MAGENTA   = 0x0050
BACKGROUND_YELLOW    = 0x0060
BACKGROUND_GREY      = 0x0070
BACKGROUND_INTENSITY = 0x0080 # background color is intensified.

# Common Combinations
FOREGROUND_WHITE = FOREGROUND_BLUE | FOREGROUND_GREEN | FOREGROUND_RED # Standard white for normal text.


def add_coloring_to_emit_windows(original_emit_fn):
    """
    Decorator function to patch `logging.StreamHandler.emit` for Windows.
    It uses ctypes to call the Windows API to set console text attributes.
    """
    # Add necessary methods to the StreamHandler class for Windows API interaction.
    def _out_handle(self):
        """Returns the handle to the standard output."""
        import ctypes # Import here to avoid unnecessary import on non-Windows platforms.
        return ctypes.windll.kernel32.GetStdHandle(self.STD_OUTPUT_HANDLE)
    # Use property to make _out_handle accessible like an attribute.
    logging.StreamHandler.out_handle = property(_out_handle)

    def _set_color(self, code):
        """Sets the console text attribute (color) using Windows API."""
        import ctypes
        self.STD_OUTPUT_HANDLE = -11 # Define here or use module-level constant if not already set.
        hdl = ctypes.windll.kernel32.GetStdHandle(self.STD_OUTPUT_HANDLE)
        ctypes.windll.kernel32.SetConsoleTextAttribute(hdl, code)
    # Attach _set_color method to StreamHandler instances.
    setattr(logging.StreamHandler, '_set_color', _set_color)

    # This 'new' function replaces the original `emit` method.
    def new_emit_windows(self, record):
        """
        New emit method for Windows, applies color based on log level before calling
        the original emit function, then resets the color.
        """
        levelno = record.levelno # Get the numeric logging level.

        # Determine the console color code based on the logging level.
        if levelno >= logging.CRITICAL:
            color = BACKGROUND_YELLOW | FOREGROUND_RED | FOREGROUND_INTENSITY | BACKGROUND_INTENSITY
        elif levelno >= logging.ERROR:
            color = FOREGROUND_RED | FOREGROUND_INTENSITY
        elif levelno >= logging.WARNING:
            color = FOREGROUND_YELLOW | FOREGROUND_INTENSITY
        elif levelno >= logging.INFO:
            color = FOREGROUND_GREEN
        elif levelno >= logging.DEBUG:
            color = FOREGROUND_MAGENTA
        else:
            color = FOREGROUND_WHITE # Default white color.

        self._set_color(color) # Apply the color.

        ret = original_emit_fn(self, record) # Call the original emit function to do the actual logging.

        self._set_color(FOREGROUND_WHITE) # Reset color after emitting to avoid coloring subsequent output.
        return ret
    return new_emit_windows # Return the patched emit function.


# Define ANSI escape sequences as module-level constants for efficiency and readability.
ANSI_RESET = '\x1b[0m'
ANSI_CRITICAL_ERROR_COLOR = '\x1b[31;1m\033[7m' # Bright Red, Reverse Video
ANSI_WARNING_COLOR = '\x1b[31;1m' # Bright Red
ANSI_INFO_COLOR = '\033[32;1m' # Bright Green
ANSI_DEBUG_COLOR = '\033[33;1m' # Bright Yellow


def add_coloring_to_emit_ansi(original_emit_fn):
    """
    Decorator function to patch `logging.StreamHandler.emit` for ANSI-compatible terminals.
    It prepends and appends ANSI escape sequences to the log message.
    """
    # This 'new' function replaces the original `emit` method.
    def new_emit_ansi(self, record):
        """
        New emit method for ANSI terminals, prepends ANSI escape sequences to
        the log message to colorize it, then resets the color.
        """
        levelno = record.levelno # Get the numeric logging level.

        # Determine the ANSI color escape sequence based on the logging level.
        if levelno >= logging.CRITICAL:
            color = ANSI_CRITICAL_ERROR_COLOR
        elif levelno >= logging.ERROR:
            color = ANSI_CRITICAL_ERROR_COLOR
        elif levelno >= logging.WARNING:
            color = ANSI_WARNING_COLOR
        elif levelno >= logging.INFO:
            color = ANSI_INFO_COLOR
        elif levelno >= logging.DEBUG:
            color = ANSI_DEBUG_COLOR
        else:
            color = ANSI_RESET # Normal (reset attributes)

        # Prepend the color sequence and append the reset sequence to the message.
        # Ensure record.msg is string before concatenation.
        record.msg = color + str(record.msg) + ANSI_RESET

        ret = original_emit_fn(self, record) # Call the original emit function.
        return ret
    return new_emit_ansi # Return the patched emit function.

# --- Apply the appropriate coloring patch based on the operating system ---
if platform.system() == 'Windows':
    # On Windows, use ctypes for direct API calls.
    logging.StreamHandler.emit = add_coloring_to_emit_windows(logging.StreamHandler.emit)
else:
    # On non-Windows (Linux, macOS, etc.), assume ANSI escape code support.
    logging.StreamHandler.emit = add_coloring_to_emit_ansi(logging.StreamHandler.emit)

# The module is designed to be imported. Once imported, it patches the logging.StreamHandler.
# There's no need to call functions from this module directly after import in normal usage.


# #!/usr/bin/env python
# # encoding: utf-8
# import logging
# # now we patch Python code to add color support to logging.StreamHandler
# def add_coloring_to_emit_windows(fn):
#         # add methods we need to the class
#     def _out_handle(self):
#         import ctypes
#         return ctypes.windll.kernel32.GetStdHandle(self.STD_OUTPUT_HANDLE)
#     out_handle = property(_out_handle)

#     def _set_color(self, code):
#         import ctypes
#         # Constants from the Windows API
#         self.STD_OUTPUT_HANDLE = -11
#         hdl = ctypes.windll.kernel32.GetStdHandle(self.STD_OUTPUT_HANDLE)
#         ctypes.windll.kernel32.SetConsoleTextAttribute(hdl, code)

#     setattr(logging.StreamHandler, '_set_color', _set_color)

#     def new(*args):
#         FOREGROUND_BLUE      = 0x0001 # text color contains blue.
#         FOREGROUND_GREEN     = 0x0002 # text color contains green.
#         FOREGROUND_RED       = 0x0004 # text color contains red.
#         FOREGROUND_INTENSITY = 0x0008 # text color is intensified.
#         FOREGROUND_WHITE     = FOREGROUND_BLUE|FOREGROUND_GREEN |FOREGROUND_RED
#        # winbase.h
#         STD_INPUT_HANDLE = -10
#         STD_OUTPUT_HANDLE = -11
#         STD_ERROR_HANDLE = -12

#         # wincon.h
#         FOREGROUND_BLACK     = 0x0000
#         FOREGROUND_BLUE      = 0x0001
#         FOREGROUND_GREEN     = 0x0002
#         FOREGROUND_CYAN      = 0x0003
#         FOREGROUND_RED       = 0x0004
#         FOREGROUND_MAGENTA   = 0x0005
#         FOREGROUND_YELLOW    = 0x0006
#         FOREGROUND_GREY      = 0x0007
#         FOREGROUND_INTENSITY = 0x0008 # foreground color is intensified.

#         BACKGROUND_BLACK     = 0x0000
#         BACKGROUND_BLUE      = 0x0010
#         BACKGROUND_GREEN     = 0x0020
#         BACKGROUND_CYAN      = 0x0030
#         BACKGROUND_RED       = 0x0040
#         BACKGROUND_MAGENTA   = 0x0050
#         BACKGROUND_YELLOW    = 0x0060
#         BACKGROUND_GREY      = 0x0070
#         BACKGROUND_INTENSITY = 0x0080 # background color is intensified.     

#         levelno = args[1].levelno
#         if(levelno>=50):
#             color = BACKGROUND_YELLOW | FOREGROUND_RED | FOREGROUND_INTENSITY | BACKGROUND_INTENSITY 
#         elif(levelno>=40):
#             color = FOREGROUND_RED | FOREGROUND_INTENSITY
#         elif(levelno>=30):
#             color = FOREGROUND_YELLOW | FOREGROUND_INTENSITY
#         elif(levelno>=20):
#             color = FOREGROUND_GREEN
#         elif(levelno>=10):
#             color = FOREGROUND_MAGENTA
#         else:
#             color =  FOREGROUND_WHITE
#         args[0]._set_color(color)

#         ret = fn(*args)
#         args[0]._set_color( FOREGROUND_WHITE )
#         #print "after"
#         return ret
#     return new

# def add_coloring_to_emit_ansi(fn):
#     # add methods we need to the class
#     def new(*args):
#         # ANSI: color and escape sequences:
#         # https://stackoverflow.com/questions/4842424/list-of-ansi-color-escape-sequences
#         levelno = args[1].levelno
#         if(levelno>=50): # CRITICAL
#             color = '\x1b[31;1m\033[7m' # bright red, reverse video
#         elif(levelno>=40): # ERROR
#             color = '\x1b[31;1m\033[7m' # bright red, reverse video
#         elif(levelno>=30): # WARNING
#             color = '\x1b[31;1m' # bright red
#         elif(levelno>=20): # INFO
#             color = '\033[32;1m' # bright green 
#         elif(levelno>=10): # DEBUG
#             color = '\033[33;1m' # bright yellow
#         else: # NOTSET
#             color = '\x1b[0m' # normal
#         args[1].msg = color + args[1].msg +  '\x1b[0m'  # normal
#         #print "after"
#         return fn(*args)
#     return new

# import platform
# if platform.system()=='Windows':
#     # Windows does not support ANSI escapes and we are using API calls to set the console color
#     logging.StreamHandler.emit = add_coloring_to_emit_windows(logging.StreamHandler.emit)
# else:
#     # all non-Windows platforms are supporting ANSI escapes so we use them
#     logging.StreamHandler.emit = add_coloring_to_emit_ansi(logging.StreamHandler.emit)
#     #log = logging.getLogger()
#     #log.addFilter(log_filter())
#     #//hdlr = logging.StreamHandler()
#     #//hdlr.setFormatter(formatter())
