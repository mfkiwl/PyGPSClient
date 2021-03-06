"""
PyGPSClient Globals

Collection of global constants and helper methods

Created on 14 Sep 2020

@author: semuadmin
"""
# pylint: disable=invalid-name, line-too-long

import os
from math import sin, cos, pi
from serial import PARITY_NONE, PARITY_EVEN, PARITY_ODD, PARITY_MARK, PARITY_SPACE
from pynmea2 import types

DIRNAME = os.path.dirname(__file__)
ICON_APP = os.path.join(DIRNAME, "resources/iconmonstr-location-27-32.png")
ICON_CONN = os.path.join(DIRNAME, "resources/iconmonstr-link-8-24.png")
ICON_DISCONN = os.path.join(DIRNAME, "resources/iconmonstr-link-10-24.png")
ICON_POS = os.path.join(DIRNAME, "resources/iconmonstr-location-1-24.png")
ICON_SEND = os.path.join(DIRNAME, "resources/iconmonstr-arrow-12-24.png")
ICON_EXIT = os.path.join(DIRNAME, "resources/iconmonstr-door-6-24.png")
ICON_PENDING = os.path.join(DIRNAME, "resources/iconmonstr-time-6-24.png")
ICON_CONFIRMED = os.path.join(DIRNAME, "resources/iconmonstr-check-mark-8-24.png")
ICON_WARNING = os.path.join(DIRNAME, "resources/iconmonstr-warning-1-24.png")
ICON_UBXCONFIG = os.path.join(DIRNAME, "resources/iconmonstr-gear-2-24.png")
ICON_LOGREAD = os.path.join(DIRNAME, "resources/iconmonstr-note-37-24.png")
IMG_WORLD = os.path.join(DIRNAME, "resources/world.png")
BTN_CONNECT = "\u25b6"  # text on "Connected" button
BTN_DISCONNECT = "\u2587"  # text on "Disconnected" button

GITHUB_URL = "https://github.com/semuconsulting/PyGPSClient"
XML_HDR = '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
GPX_NS = " ".join(
    (
        'xmlns="http://www.topografix.com/GPX/1/1"',
        'creator="PyGPSClient" version="1.1"',
        'xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"',
        'xsi:schemaLocation="http://www.topografix.com/GPX/1/1',
        'http://www.topografix.com/GPX/1/1/gpx.xsd"',
    )
)
MAPURL = "https://www.mapquestapi.com/staticmap/v5/map?key={}&locations={},{}&zoom={}&defaultMarker=marker-sm-616161-ff4444&shape=radius:{}|weight:1|fill:ccffff50|border:88888850|{},{}&size={},{}"
MAP_UPDATE_INTERVAL = (
    60  # how frequently the mapquest api is called to update the web map
)
SAT_EXPIRY = 10  # how long passed satellites are kept in the sky and graph views
MAX_SNR = 60  # upper limit of graphview snr axis
DEVICE_ACCURACY = 2.5  # nominal GPS device accuracy (CEP) in meters
HDOP_RATIO = 20  # arbitrary calibration of accuracy against HDOP
KNOWNGPS = ("GPS", "gps", "GNSS", "gnss", "Garmin", "garmin", "U-Blox", "u-blox")
BAUDRATES = (115200, 57600, 38400, 19200, 9600, 4800)
PARITIES = {
    "Even": PARITY_EVEN,
    "Odd": PARITY_ODD,
    "Mark": PARITY_MARK,
    "Space": PARITY_SPACE,
    "None": PARITY_NONE,
}
# serial port timeout; lower is better for app response
# but you may lose packets on high latency connections
SERIAL_TIMEOUT = 0.2
MQAPIKEY = "mqapikey"
UBXPRESETS = "ubxpresets"
MAXLOGLINES = 10000  # maximum number of 'lines' per datalog file
NMEA_PROTOCOL = 0
UBX_PROTOCOL = 1
MIXED_PROTOCOL = 2
DISCONNECTED = 0
CONNECTED = 1
CONNECTED_FILE = 2
NOPORTS = 3
WIDGETU1 = (250, 250)
WIDGETU2 = (350, 250)
WIDGETU3 = (950, 350)
BGCOL = "gray24"  # default widget background color
FGCOL = "white"  # default widget foreground color
ENTCOL = "azure"  # default data entry field background color
READONLY = "readonly"
ADVOFF = "\u25bc"
ADVON = "\u25b2"
ERROR = "ERR!"
DDD = "DD.D"
DMM = "DM.M"
DMS = "D.M.S"
UMM = "Metric m/s"
UMK = "Metric kmph"
UI = "Imperial mph"
UIK = "Imperial knots"

# List of tags to highlight in console
TAGS = [
    ("DTM", "deepskyblue"),
    ("GBS", "pink"),
    ("GGA", "orange"),
    ("GSV", "yellow"),
    ("GLL", "orange"),
    ("TXT", "lightgrey"),
    ("GSA", "green2"),
    ("RMC", "orange"),
    ("VTG", "deepskyblue"),
    ("UBX", "lightblue1"),
    ("UBX00", "aquamarine2"),
    ("UBX03", "yellow"),
    ("UBX04", "cyan"),
    ("UBX05", "orange"),
    ("UBX06", "orange"),
    ("ZDA", "cyan"),
    ("GNS", "orange"),
    ("VLW", "deepskyblue"),
    ("GST", "mediumpurple2"),
    ("INF-ERROR", "red2"),
    ("INF-WARNING", "orange"),
    ("INF-NOTICE", "deepskyblue"),
    ("ACK-ACK", "green2"),
    ("ACK-NAK", "orange red"),
    ("CFG-MSG", "cyan"),
    ("xb5b", "lightblue1"),
    ("NAV-SOL", "green2"),
    ("NAV-POSLLH", "orange"),
    ("NAV-VELECEF", "deepskyblue"),
    ("NAV-VELNED", "deepskyblue"),
    ("NAV-SVINFO", "yellow"),
    ("NAV-TIMEUTC", "cyan"),
    ("NAV-STATUS", "green2"),
    ("NAV-PVT", "orange"),
    ("NAV-DOP", "mediumpurple2"),
    ("NAV-CLOCK", "cyan"),
    ("NAV-SBAS", "yellow"),
    ("NAV-SAT", "yellow"),
    ("NAV-POSECEF", "orange"),
    ("NAV-TIMEGLO", "cyan"),
    ("NAV-TIMEBDS", "cyan"),
    ("NAV-TIMEGAL", "cyan"),
    ("NAV-ORB", "yellow"),
    ("NAV-TIMELS", "cyan"),
    ("NAV-TIMEGPS", "cyan"),
    ("RXM", "skyblue1"),
    ("MON", "skyblue1"),
    ("LOG", "skyblue1"),
]


def deg2rad(deg: float) -> float:
    """
    Convert degrees to radians
    """

    if not isinstance(deg, (float, int)):
        return 0
    return deg * pi / 180


def cel2cart(elevation: float, azimuth: float) -> (float, float):
    """
    Convert celestial coordinates (degrees) to Cartesian coordinates
    """

    if not (isinstance(elevation, (float, int)) and isinstance(azimuth, (float, int))):
        return (0, 0)
    elevation = deg2rad(elevation)
    azimuth = deg2rad(azimuth)
    x = cos(azimuth) * cos(elevation)
    y = sin(azimuth) * cos(elevation)
    return (x, y)


def deg2dms(degrees: float, latlon: str) -> str:
    """
    Convert decimal degrees to degrees minutes seconds string
    """

    if not isinstance(degrees, (float, int)):
        return ""
    negative = degrees < 0
    degrees = abs(degrees)
    minutes, seconds = divmod(degrees * 3600, 60)
    degrees, minutes = divmod(minutes, 60)
    if negative:
        sfx = "S" if latlon == "lat" else "W"
    else:
        sfx = "N" if latlon == "lat" else "E"
    return (
        str(int(degrees))
        + "\u00b0"
        + str(int(minutes))
        + "\u2032"
        + str(round(seconds, 3))
        + "\u2033"
        + sfx
    )


def deg2dmm(degrees: float, latlon: str) -> str:
    """
    Convert decimal degrees to degrees decimal minutes string
    """

    if not isinstance(degrees, (float, int)):
        return ""
    negative = degrees < 0
    degrees = abs(degrees)
    degrees, minutes = divmod(degrees * 60, 60)
    if negative:
        sfx = "S" if latlon == "lat" else "W"
    else:
        sfx = "N" if latlon == "lat" else "E"
    return str(int(degrees)) + "\u00b0" + str(round(minutes, 5)) + "\u2032" + sfx


def m2ft(meters: float) -> float:
    """
    Convert meters to feet
    """

    if not isinstance(meters, (float, int)):
        return 0
    return meters * 3.28084


def ft2m(feet: float) -> float:
    """
    Convert feet to meters
    """

    if not isinstance(feet, (float, int)):
        return 0
    return feet / 3.28084


def ms2kmph(ms: float) -> float:
    """
    Convert meters per second to kilometers per hour
    """

    if not isinstance(ms, (float, int)):
        return 0
    return ms * 3.6


def ms2mph(ms: float) -> float:
    """
    Convert meters per second to miles per hour
    """

    if not isinstance(ms, (float, int)):
        return 0
    return ms * 2.23693674


def ms2knots(ms: float) -> float:
    """
    Convert meters per second to knots
    """

    if not isinstance(ms, (float, int)):
        return 0
    return ms * 1.94384395


def kmph2ms(kmph: float) -> float:
    """
    Convert kilometers per hour to meters per second
    """

    if not isinstance(kmph, (float, int)):
        return 0
    return kmph * 0.2777778


def knots2ms(knots: float) -> float:
    """
    Convert knots to meters per second
    """

    if not isinstance(knots, (float, int)):
        return 0
    return knots * 0.5144447324


def pos2iso6709(lat: float, lon: float, alt: float, crs: str = "WGS_84") -> str:
    """
    convert decimal degrees and alt to iso6709 format
    """

    if not (
        isinstance(lat, (float, int))
        and isinstance(lon, (float, int))
        and isinstance(alt, (float, int))
    ):
        return ""
    lati = "-" if lat < 0 else "+"
    loni = "-" if lon < 0 else "+"
    alti = "-" if alt < 0 else "+"
    iso6709 = (
        lati
        + str(abs(lat))
        + loni
        + str(abs(lon))
        + alti
        + str(alt)
        + "CRS"
        + crs
        + "/"
    )
    return iso6709


def hsv2rgb(h: float, s: float, v: float) -> str:
    """
    Convert HSV values (in range 0-1) to RGB color string.
    """

    if s == 0.0:
        v = int(v * 255)
        return v, v, v
    i = int(h * 6.0)
    f = (h * 6.0) - i
    p = v * (1.0 - s)
    q = v * (1.0 - s * f)
    t = v * (1.0 - s * (1.0 - f))
    i %= 6
    if i == 0:
        r, g, b = v, t, p
    if i == 1:
        r, g, b = q, v, p
    if i == 2:
        r, g, b = p, v, t
    if i == 3:
        r, g, b = p, q, v
    if i == 4:
        r, g, b = t, p, v
    if i == 5:
        r, g, b = v, p, q

    rgb = int(r * 255), int(g * 255), int(b * 255)
    return "#%02x%02x%02x" % rgb


def snr2col(snr: int) -> str:
    """
    Convert satellite signal-to-noise ratio to a color
    high = green, low = red
    """

    return hsv2rgb(snr / (MAX_SNR * 2.5), 0.8, 0.8)


def nmea2latlon(data: types.talker) -> (float, float):
    """
    Convert parsed NMEA sentence to decimal lat, lon
    """

    if data.lat == "":
        lat = ""
    else:
        latdeg = float(data.lat[0:2])
        latmin = float(data.lat[2:])
        londeg = float(data.lon[0:3])
        lat = (latdeg + latmin / 60) * (-1 if data.lat_dir == "S" else 1)
    if data.lon == "":
        lon = ""
    else:
        lonmin = float(data.lon[3:])
        lon = (londeg + lonmin / 60) * (-1 if data.lon_dir == "W" else 1)
    return (lat, lon)
