"""
app.py

PyGPSClient - Main tkinter application class.

- Loads configuration from json file (if available)
- Instantiates all frames, widgets, and protocol handlers.
- Starts and stops threaded dialog and protocol handler processes.
- Maintains current serial and RTK connection status.
- Reacts to various message events, processes navigation data
  placed on input message queue by serial, socket or file stream reader
  and assigns to appropriate NMEA, UBX or RTCM protocol handler.
- Maintains central dictionary of current key navigation data as
  `gnss_status`, for use by user-selectable widgets.

Global logging configuration is defined in __main__.py. To enable module
logging, this and other subsidiary modules can use:

```self.logger = logging.getLogger(__name__)```

To override individual module loglevel, use e.g.

```self.logger.setLevel(INFO)```

Created on 12 Sep 2020

:author: semuadmin
:copyright: 2020 SEMU Consulting
:license: BSD 3-Clause
"""

# pylint: disable=too-many-ancestors, no-member

import logging
from datetime import datetime, timedelta, timezone
from os import getenv, path
from pathlib import Path
from queue import Empty, Queue
from socket import AF_INET, AF_INET6
from threading import Thread
from tkinter import E, Frame, N, PhotoImage, S, TclError, Tk, Toplevel, W, font

from pygnssutils import GNSSMQTTClient, GNSSNTRIPClient, MQTTMessage
from pygnssutils.socket_server import ClientHandler, SocketServer
from pynmeagps import NMEAMessage
from pyrtcm import RTCMMessage
from pyspartn import SPARTNMessage, date2timetag
from pyubx2 import NMEA_PROTOCOL, POLL, RTCM3_PROTOCOL, UBX_PROTOCOL, UBXMessage
from serial import SerialException, SerialTimeoutException

from pygpsclient._version import __version__ as VERSION
from pygpsclient.dialog_state import dialog_state
from pygpsclient.file_handler import FileHandler
from pygpsclient.globals import (
    CFG,
    CLASS,
    CONFIGFILE,
    CONNECTED,
    CONNECTED_NTRIP,
    CONNECTED_SPARTNIP,
    CONNECTED_SPARTNLB,
    DEFAULT_PASSWORD,
    DEFAULT_REGION,
    DEFAULT_USER,
    DISCONNECTED,
    ERRCOL,
    FRAME,
    GNSS_EOF_EVENT,
    GNSS_ERR_EVENT,
    GNSS_EVENT,
    GNSS_TIMEOUT_EVENT,
    GUI_UPDATE_INTERVAL,
    ICON_APP128,
    INFOCOL,
    MQTT_PROTOCOL,
    NOPORTS,
    NTRIP_EVENT,
    OKCOL,
    SOCKSERVER_MAX_CLIENTS,
    SPARTN_BASEDATE_CURRENT,
    SPARTN_DEFAULT_KEY,
    SPARTN_EVENT,
    SPARTN_OUTPORT,
    SPARTN_PPSERVER_URL,
    SPARTN_PROTOCOL,
    THD,
)
from pygpsclient.gnss_status import GNSSStatus
from pygpsclient.helpers import check_latest
from pygpsclient.menu_bar import MenuBar
from pygpsclient.nmea_handler import NMEAHandler
from pygpsclient.rtcm3_handler import RTCM3Handler
from pygpsclient.stream_handler import StreamHandler
from pygpsclient.strings import (
    CONFIGERR,
    DLG,
    DLGSTOPRTK,
    DLGTNTRIP,
    ENDOFFILE,
    INACTIVE_TIMEOUT,
    INTROTXTNOPORTS,
    LOADCONFIGBAD,
    LOADCONFIGNONE,
    LOADCONFIGOK,
    NOTCONN,
    NOWDGSWARN,
    SAVECONFIGBAD,
    SAVECONFIGOK,
    TITLE,
    VERCHECK,
)
from pygpsclient.ubx_handler import UBXHandler
from pygpsclient.widget_state import (
    COL,
    COLSPAN,
    DEFAULT,
    HIDE,
    MAXCOLSPAN,
    MAXROWSPAN,
    MENU,
    ROW,
    ROWSPAN,
    SHOW,
    STICKY,
    VISIBLE,
    WDGCHART,
    WDGCONSOLE,
    widget_state,
)


class App(Frame):
    """
    Main PyGPSClient GUI Application Class.
    """

    def __init__(self, master, *args, **kwargs):  # pylint: disable=too-many-statements
        """
        Set up main application and add frames.

        :param tkinter.Tk master: reference to Tk root
        :param args: optional args
        :param kwargs: optional kwargs
        """

        self.__master = master
        self.logger = logging.getLogger(__name__)
        # self.logger.setLevel(logging.DEBUG)

        # user-defined serial port can be passed as environment variable
        # or command line keyword argument
        self._configfile = kwargs.pop("config", CONFIGFILE)
        user_port = kwargs.pop("userport", getenv("PYGPSCLIENT_USERPORT", ""))
        spartn_user_port = kwargs.pop(
            "spartnport", getenv("PYGPSCLIENT_SPARTNPORT", "")
        )
        mqapikey = kwargs.pop("mqapikey", getenv("MQAPIKEY", ""))
        mqttclientid = kwargs.pop("mqttclientid", getenv("MQTTCLIENTID", ""))
        mqttclientregion = kwargs.pop(
            "mqttclientregion", getenv("MQTTCLIENTREGION", DEFAULT_REGION)
        )
        mqttclientmode = int(
            kwargs.pop("mqttclientmode", getenv("MQTTCLIENTMODE", "0"))
        )
        spartnkey = kwargs.pop("spartnkey", getenv("MQTTKEY", SPARTN_DEFAULT_KEY))
        spartnbasedate = kwargs.pop("spartnbasedate", SPARTN_BASEDATE_CURRENT)
        ntripcaster_user = kwargs.pop(
            "ntripcasteruser", getenv("NTRIPCASTER_USER", DEFAULT_USER)
        )
        ntripcaster_password = kwargs.pop(
            "ntripcasterpassword", getenv("NTRIPCASTER_PASSWORD", DEFAULT_PASSWORD)
        )
        self.ubxsimulator = (
            kwargs.pop("ubxsimulator", getenv("UBXSIMULATOR", "0")) == "1"
        )

        Frame.__init__(self, self.__master, *args, **kwargs)

        self.__master.protocol("WM_DELETE_WINDOW", self.on_exit)
        self.__master.title(TITLE)
        self.__master.iconphoto(True, PhotoImage(file=ICON_APP128))
        self.gnss_status = GNSSStatus()  # holds latest GNSS readings
        self._last_gui_update = datetime.now()
        self._nowidgets = True

        # Instantiate protocol handler classes
        self.gnss_inqueue = Queue()  # messages from GNSS receiver
        self.gnss_outqueue = Queue()  # messages to GNSS receiver
        self.ntrip_inqueue = Queue()  # messages from NTRIP source
        self.spartn_inqueue = Queue()  # messages from SPARTN correction rcvr
        self.spartn_outqueue = Queue()  # messages to SPARTN correction rcvr
        self.socket_inqueue = Queue()  # message from socket
        self.socket_outqueue = Queue()  # message to socket
        self.file_handler = FileHandler(self)
        self.stream_handler = StreamHandler(self)
        self.spartn_stream_handler = StreamHandler(self)
        self.nmea_handler = NMEAHandler(self)
        self.ubx_handler = UBXHandler(self)
        self.rtcm_handler = RTCM3Handler(self)
        self.ntrip_handler = GNSSNTRIPClient(self)
        self.spartn_handler = GNSSMQTTClient(self)
        self._conn_status = DISCONNECTED
        self._rtk_conn_status = DISCONNECTED
        self._socket_thread = None
        self._socket_server = None
        self._colcount = 0
        self._rowcount = 0
        self._consoledata = []

        # Load configuration from file if it exists
        self._colortags = []
        self._ubxpresets = []
        self.saved_config = {}
        (_, config, configerr) = self.file_handler.load_config(self._configfile)
        if configerr == "":  # load succeeded
            self.saved_config = config
            # update configs needed to instantiate widgets and protocol handlers
            self.update_widgets()

        # temporarily override saved config with any command line arguments / env variables
        if user_port != "":
            self.saved_config["userport_s"] = user_port
        if spartn_user_port != "":
            self.saved_config["spartnport_s"] = spartn_user_port
        if mqapikey != "":
            self.saved_config["mqapikey_s"] = mqapikey
        if mqttclientid != "":
            self.saved_config["mqttclientid_s"] = mqttclientid
        if spartnkey != SPARTN_DEFAULT_KEY:
            self.saved_config["spartnkey_s"] = spartnkey
        if spartnbasedate != SPARTN_BASEDATE_CURRENT:
            self.saved_config["spartnbasedate_n"] = spartnkey
        if mqttclientregion != DEFAULT_REGION:
            self.saved_config["mqttclientregion_s"] = mqttclientregion
        if mqttclientmode != 0:
            self.saved_config["mqttclientmode_n"] = mqttclientmode
        if ntripcaster_user != DEFAULT_USER:
            self.saved_config["ntripcasteruser_s"] = ntripcaster_user
        if ntripcaster_password != DEFAULT_PASSWORD:
            self.saved_config["ntripcasterpassword_s"] = ntripcaster_password

        # update NTRIP and SPARTN client handlers with initial config
        self.update_NTRIP_handler()
        self.update_SPARTN_handler()

        self._body()
        self._do_layout()
        self._attach_events()

        # display config load status once status frame has been instantiated
        if configerr == "":
            if self._nowidgets:  # if all widgets have been disabled in config
                self.set_status(NOWDGSWARN.format(self._configfile), ERRCOL)
            else:
                self.set_status(LOADCONFIGOK.format(self._configfile), OKCOL)
        else:
            if "No such file or directory" in configerr:
                self.set_status(LOADCONFIGNONE.format(self._configfile), ERRCOL)
            else:
                self.set_status(
                    LOADCONFIGBAD.format(self._configfile, configerr), ERRCOL
                )

        # initialise widgets
        for value in widget_state.values():
            frm = getattr(self, value[FRAME])
            if hasattr(frm, "init_frame"):
                frm.init_frame()

        self.frm_banner.update_conn_status(DISCONNECTED)
        if self.frm_settings.frm_serial.status == NOPORTS:
            self.set_status(INTROTXTNOPORTS, ERRCOL)

        # Check for more recent version (if enabled)
        if self.saved_config.get("checkforupdate_b", False):
            self._check_update()

    def _body(self):
        """
        Set up frame and widgets.
        """

        self._set_default_fonts()
        self.menu = MenuBar(self)
        self.__master.config(menu=self.menu)

        # instantiate widgets
        for value in widget_state.values():
            setattr(
                self,
                value[FRAME],
                value[CLASS](self, borderwidth=2, relief="groove"),
            )

    def _do_layout(self):
        """
        Arrange widgets in main application frame, and set
        widget visibility and menu label (show/hide).
        """

        col = 0
        row = 1
        maxcol = 0
        maxrow = 0
        men = 0
        for name in widget_state:
            col, row, maxcol, maxrow, men = self._widget_grid(
                name, col, row, maxcol, maxrow, men
            )

        # ensure widgets expand to size of container (needed
        # when not using 'pack' grid management)
        # weight = 0 means fixed, non-expandable
        # weight > 0 means expandable
        for col in range(MAXCOLSPAN + 1):
            self.__master.grid_columnconfigure(col, weight=0)
        for row in range(MAXROWSPAN + 2):
            self.__master.grid_rowconfigure(row, weight=0)
        # print(f"{maxcol=} {maxrow=}")
        for col in range(maxcol):
            self.__master.grid_columnconfigure(col, weight=5)
        for row in range(1, maxrow + 1):
            self.__master.grid_rowconfigure(row, weight=5)

    def _widget_grid(
        self, name: str, col: int, row: int, maxcol: int, maxrow: int, men: int
    ) -> tuple:
        """
        Arrange widgets and update menu label (show/hide).

        Widgets with explicit COL settings will be placed in fixed
        positions; widgets with no COL setting will be arranged
        dynamically.

        :param str name: name of widget
        :param int col: col
        :param int row: row
        :param int maxcol: max cols
        :param int maxrow: max rows
        :param int men: menu position
        :return: max row & col
        :rtype: tuple
        """

        wdg = widget_state[name]
        dynamic = wdg.get(COL, None) is None
        frm = getattr(self, wdg[FRAME])
        if wdg[VISIBLE]:
            self.widget_enable_messages(name)
            fcol = wdg.get(COL, col)
            frow = wdg.get(ROW, row)
            colspan = wdg.get(COLSPAN, 1)
            rowspan = wdg.get(ROWSPAN, 1)
            if dynamic and fcol + colspan > MAXCOLSPAN:
                fcol = 0
                frow += 1
            frm.grid(
                column=fcol,
                row=frow,
                columnspan=colspan,
                rowspan=rowspan,
                padx=2,
                pady=2,
                sticky=wdg.get(STICKY, (N, S, W, E)),
            )
            lbl = HIDE
            if dynamic:
                col += colspan
                if col >= MAXCOLSPAN:
                    col = 0
                    row += rowspan
                maxcol = max(maxcol, fcol + colspan)
                maxrow = max(maxrow, frow)
        else:
            frm.grid_forget()
            lbl = SHOW

        # update menu label (show/hide)
        if wdg.get(MENU, True):
            self.menu.view_menu.entryconfig(men, label=f"{lbl} {name}")
            men += 1

        # force widget to rescale
        frm.event_generate("<Configure>")

        return col, row, maxcol, maxrow, men

    def widget_toggle(self, name: str):
        """
        Toggle widget visibility and enable or disable any
        UBX messages required by widget.

        :param str name: widget name
        """

        wdg = widget_state[name]
        wdg[VISIBLE] = not wdg[VISIBLE]
        self._do_layout()

    def widget_enable_messages(self, name: str):
        """
        Enable any NMEA, UBX or RTCM messages required by widget.

        :param str name: widget name
        """

        wdg = widget_state[name]
        frm = getattr(self, wdg[FRAME])
        if hasattr(frm, "enable_messages"):
            frm.enable_messages(wdg[VISIBLE])

    def widget_reset(self):
        """
        Reset widgets to default layout.
        """

        for _, wdg in widget_state.items():
            wdg[VISIBLE] = wdg.get(DEFAULT, False)
        self._do_layout()

    def reset_gnssstatus(self):
        """
        Reset gnss_status dict e.g. after reconnecting.
        """

        self.gnss_status = GNSSStatus()

    def _attach_events(self):
        """
        Bind events to main application.
        """

        self.__master.bind(GNSS_EVENT, self.on_gnss_read)
        self.__master.bind(GNSS_EOF_EVENT, self.on_gnss_eof)
        self.__master.bind(GNSS_TIMEOUT_EVENT, self.on_gnss_timeout)
        self.__master.bind(GNSS_ERR_EVENT, self.on_stream_error)
        self.__master.bind(NTRIP_EVENT, self.on_ntrip_read)
        self.__master.bind(SPARTN_EVENT, self.on_spartn_read)
        self.__master.bind_all("<Control-q>", self.on_exit)

    def _set_default_fonts(self):
        """
        Set default fonts for entire application.
        """
        # pylint: disable=attribute-defined-outside-init

        self.font_vsm = font.Font(size=8)
        self.font_sm = font.Font(size=10)
        self.font_md = font.Font(size=12)
        self.font_md2 = font.Font(size=14)
        self.font_lg = font.Font(size=18)

    def set_connection(self, message, color=OKCOL):
        """
        Sets connection description in status bar.

        :param str message: message to be displayed in connection label
        :param str color: rgb color string

        """

        self.frm_status.set_connection(message, color=color)

    def set_status(self, message, color=OKCOL):
        """
        Sets text of status bar.

        :param str message: message to be displayed in status label
        :param str color: rgb color string

        """

        color = INFOCOL if color == "blue" else color
        self.frm_status.set_status(message, color)

    def set_event(self, evt: str):
        """
        Generate event

        :param str evt: event type string
        """

        self.__master.event_generate(evt)

    def load_config(self):
        """
        Load configuration file menu option.
        """

        # Warn if Streaming, NTRIP or SPARTN clients are running
        if self.conn_status == DISCONNECTED and self.rtk_conn_status == DISCONNECTED:
            self.set_status("", OKCOL)
        else:
            self.set_status(DLGSTOPRTK, ERRCOL)
            return

        (filename, config, configerr) = self.file_handler.load_config(None)
        if configerr == "":  # load succeeded
            self.saved_config = config
            self.update_widgets()
            self.update_NTRIP_handler()
            self.update_SPARTN_handler()
            for frm in (
                self.frm_settings,
                self.frm_settings.frm_serial,
                self.frm_settings.frm_socketclient,
                self.frm_settings.frm_socketserver,
            ):
                frm.reset()
            self._do_layout()
            if self._nowidgets:
                self.set_status(NOWDGSWARN.format(filename), ERRCOL)
            else:
                self.set_status(LOADCONFIGOK.format(filename), OKCOL)
        elif configerr == "cancelled":  # user cancelled
            return
        else:  # config error
            self.set_status(LOADCONFIGBAD.format(filename), ERRCOL)

    def save_config(self):
        """
        Save configuration file menu option.

        Configuration is held in two places:
        - app.config - widget visibility and CLI parameters
        - frm_settings.config - current frame and protocol handler config
        """

        self.saved_config = {
            **self.widget_config,
            **self.frm_settings.config,
        }
        err = self.file_handler.save_config(self.saved_config, None)
        if err == "":
            self.set_status(SAVECONFIGOK, OKCOL)
        else:  # save failed
            self.set_status(SAVECONFIGBAD.format(err), ERRCOL)

    def update_widgets(self):
        """
        Update widget configuration (widget_state).

        If no widgets are set as "visible" in the config file, enable
        the status widget anyway to display a warning to this effect.
        """

        try:
            self._nowidgets = True
            for key, vals in widget_state.items():
                vis = self.saved_config.get(key, False)
                vals[VISIBLE] = vis
                if vis:
                    self._nowidgets = False
            for key, vals in widget_state.items():
                vis = self.saved_config.get(key, False)
                vals[VISIBLE] = vis
                if vis:
                    self._nowidgets = False
            if self._nowidgets:
                widget_state["Status"][VISIBLE] = "true"
        except KeyError as err:
            self.set_status(f"{CONFIGERR} - {err}", ERRCOL)

    def update_NTRIP_handler(self):
        """
        Initial configuration of NTRIP handler (pygnssutils.GNSSNTRIPClient).
        """

        try:
            ntripsettings = {}
            ntripsettings["server"] = self.saved_config.get("ntripclientserver_s", "")
            ntripsettings["port"] = self.saved_config.get("ntripclientport_n", 2101)
            ntripsettings["https"] = self.saved_config.get("ntripclienthttps_b", 0)
            ntripsettings["ipprot"] = (
                AF_INET6
                if self.saved_config.get("ntripclientprotocol_s") == "IPv6"
                else AF_INET
            )
            ntripsettings["flowinfo"] = self.saved_config.get(
                "ntripclientflowinfo_n", 0
            )
            ntripsettings["scopeid"] = self.saved_config.get("ntripclientscopeid_n", 0)
            ntripsettings["mountpoint"] = self.saved_config.get(
                "ntripclientmountpoint_s", ""
            )
            ntripsettings["sourcetable"] = []  # this is generated by the NTRIP caster
            ntripsettings["version"] = self.saved_config.get(
                "ntripclientversion_s", "2.0"
            )
            ntripsettings["datatype"] = self.saved_config.get(
                "ntripclientdatatype_s", "RTCM"
            )
            ntripsettings["ntripuser"] = self.saved_config.get(
                "ntripclientuser_s", DEFAULT_USER
            )
            ntripsettings["ntrippassword"] = self.saved_config.get(
                "ntripclientpassword_s", DEFAULT_PASSWORD
            )
            ntripsettings["ggainterval"] = self.saved_config.get(
                "ntripclientggainterval_n", -1
            )
            ntripsettings["ggamode"] = self.saved_config.get(
                "ntripclientggamode_b", 0
            )  # GGALIVE
            ntripsettings["reflat"] = self.saved_config.get("ntripclientreflat_f", 0.0)
            ntripsettings["reflon"] = self.saved_config.get("ntripclientreflon_f", 0.0)
            ntripsettings["refalt"] = self.saved_config.get("ntripclientrefalt_f", 0.0)
            ntripsettings["refsep"] = self.saved_config.get("ntripclientrefsep_f", 0.0)
            ntripsettings["spartndecode"] = self.saved_config.get("spartndecode_b", 0)
            ntripsettings["spartnkey"] = self.saved_config.get(
                "spartnkey_s", getenv("MQTTKEY", "")
            )
            if ntripsettings["spartnkey"] == "":
                ntripsettings["spartndecode"] = 0
            # if basedate is provided in config file, it must be an integer gnssTimetag
            ntripsettings["spartnbasedate"] = self.saved_config.get(
                "spartnbasedate_n", date2timetag(datetime.now(timezone.utc))
            )
            self.ntrip_handler.settings = ntripsettings

        except (KeyError, ValueError, TypeError, TclError) as err:
            self.set_status(f"Error processing config data: {err}", ERRCOL)

    def update_SPARTN_handler(self):
        """
        Initial configuration of SPARTN handler (pygnssutils.GNSSMQTTClient).
        """

        try:
            spartnsettings = {}
            spartnsettings["server"] = self.saved_config.get(
                "mqttclientserver_s", SPARTN_PPSERVER_URL
            )
            spartnsettings["port"] = self.saved_config.get(
                "mqttclientport_n", SPARTN_OUTPORT
            )
            spartnsettings["clientid"] = self.saved_config.get("mqttclientid_s", "")
            spartnsettings["region"] = self.saved_config.get(
                "mgttclientregion_s", DEFAULT_REGION
            )
            spartnsettings["mode"] = self.saved_config.get("mgttclientmode_n", 0)
            spartnsettings["topic_ip"] = self.saved_config.get("mgttclienttopicip_b", 1)
            spartnsettings["topic_mga"] = self.saved_config.get(
                "mgttclienttopicmga_b", 1
            )
            spartnsettings["topic_key"] = self.saved_config.get(
                "mgttclienttopickey_b", 1
            )
            spartnsettings["tlscrt"] = self.saved_config.get(
                "mgttclienttlscrt_s",
                path.join(Path.home(), "device-mqttclientid-pp-cert.crt"),
            )
            spartnsettings["tlskey"] = self.saved_config.get(
                "mgttclienttlskey_s",
                path.join(Path.home(), "device-mqttclientid-pp-key.pem"),
            )
            spartnsettings["output"] = self.spartn_inqueue
            spartnsettings["spartndecode"] = self.saved_config.get("spartndecode_b", 0)
            spartnsettings["spartnkey"] = self.saved_config.get(
                "spartnkey_s", getenv("MQTTKEY", SPARTN_DEFAULT_KEY)
            )
            if spartnsettings["spartnkey"] == "":
                spartnsettings["spartndecode"] = 0
            # if basedate is provided in config file, it must be an integer gnssTimetag
            basedate = self.saved_config.get(
                "spartnbasedate_n", SPARTN_BASEDATE_CURRENT
            )
            if basedate == SPARTN_BASEDATE_CURRENT:
                basedate = date2timetag(datetime.now(timezone.utc))
            spartnsettings["spartnbasedate"] = basedate
            self.spartn_handler.settings = spartnsettings
            self.logger.debug(f"{self.spartn_handler.settings=}")

        except (KeyError, ValueError, TypeError, TclError) as err:
            self.set_status(f"Error processing config data: {err}", ERRCOL)

    def start_dialog(self, dlg: str):
        """
        Start a threaded dialog task if the dialog is not already open.

        :param str dlg: name of dialog
        """

        if dialog_state[dlg][THD] is None:
            dialog_state[dlg][THD] = Thread(
                target=self._dialog_thread, args=(dlg,), daemon=False
            )
            dialog_state[dlg][THD].start()

    def _dialog_thread(self, dlg: str):
        """
        THREADED PROCESS

        Dialog thread.

        :param str dlg: name of dialog
        """

        config = self.saved_config if dialog_state[dlg][CFG] else {}
        cls = dialog_state[dlg][CLASS]
        dialog_state[dlg][DLG] = cls(self, saved_config=config)

    def stop_dialog(self, dlg: str):
        """
        Register dialog as closed.

        :param str dlg: name of dialog
        """

        dialog_state[dlg][THD] = None
        dialog_state[dlg][DLG] = None

    def dialog(self, dlg: str) -> Toplevel:
        """
        Get reference to dialog instance.

        :param str dlg: name of dialog
        :return: dialog instance
        :rtype: Toplevel
        """

        return dialog_state[dlg][DLG]

    def start_sockserver_thread(self):
        """
        Start socket server thread.
        """

        settings = self.frm_settings.config
        host = settings["sockhost_s"]
        port = int(settings["sockport_n"])
        ntripmode = int(settings["sockmode_b"])
        ntripuser = settings["ntripcasteruser_s"]
        ntrippassword = settings["ntripcasterpassword_s"]
        self._socket_thread = Thread(
            target=self._sockserver_thread,
            args=(
                ntripmode,
                host,
                port,
                ntripuser,
                ntrippassword,
                SOCKSERVER_MAX_CLIENTS,
                self.socket_outqueue,
            ),
            daemon=True,
        )
        self._socket_thread.start()
        self.frm_banner.update_transmit_status(0)

    def stop_sockserver_thread(self):
        """
        Stop socket server thread.
        """

        self.frm_banner.update_transmit_status(-1)
        if self._socket_server is not None:
            self._socket_server.shutdown()

    def _sockserver_thread(
        self,
        ntripmode: int,
        host: str,
        port: int,
        ntripuser: str,
        ntrippassword: str,
        maxclients: int,
        socketqueue: Queue,
    ):
        """
        THREADED
        Socket Server thread.

        :param int ntripmode: 0 = open socket server, 1 = NTRIP server
        :param str host: socket host name (0.0.0.0)
        :param int port: socket port (50010)
        :param int maxclients: max num of clients (5)
        :param Queue socketqueue: socket server read queue
        """

        try:
            with SocketServer(
                self,
                ntripmode,
                maxclients,
                socketqueue,
                (host, port),
                ClientHandler,
                ntripuser=ntripuser,
                ntrippassword=ntrippassword,
            ) as self._socket_server:
                self._socket_server.serve_forever()
        except OSError as err:
            self.set_status(f"Error starting socket server {err}", ERRCOL)

    def update_clients(self, clients: int):
        """
        Update number of connected clients in settings panel.

        :param int clients: no of connected clients
        """

        self.frm_settings.frm_socketserver.clients = clients

    def on_exit(self, *args, **kwargs):  # pylint: disable=unused-argument
        """
        Kill any running processes and quit application.
        """

        self.file_handler.close_logfile()
        self.file_handler.close_trackfile()
        self.stop_sockserver_thread()
        self.stream_handler.stop_read_thread()
        self.__master.destroy()

    def on_gnss_read(self, event):  # pylint: disable=unused-argument
        """
        EVENT TRIGGERED
        Action on <<gnss_read>> event - data available on GNSS queue.

        :param event event: read event
        """

        try:
            raw_data, parsed_data = self.gnss_inqueue.get(False)
            if raw_data is not None and parsed_data is not None:
                self.process_data(raw_data, parsed_data)
            # if socket server is running, output raw data to socket
            if self.frm_settings.frm_socketserver.socketserving:
                self.socket_outqueue.put(raw_data)
            self.gnss_inqueue.task_done()
        except Empty:
            pass

    def on_gnss_eof(self, event):  # pylint: disable=unused-argument
        """
        EVENT TRIGGERED
        Action on <<sgnss_eof>> event - end of file.

        :param event event: <<gnss_eof>> event
        """

        self.frm_settings.frm_socketserver.socketserving = (
            False  # turn off socket server
        )
        self._refresh_widgets()
        self.conn_status = DISCONNECTED
        self.set_status(ENDOFFILE, ERRCOL)

    def on_gnss_timeout(self, event):  # pylint: disable=unused-argument
        """
        EVENT TRIGGERED
        Action on <<sgnss_timeout>> event - stream inactivity timeout.

        :param event event: <<gnss_timeout>> event
        """

        self.frm_settings.frm_socketserver.socketserving = (
            False  # turn off socket server
        )
        self._refresh_widgets()
        self.conn_status = DISCONNECTED
        self.set_status(INACTIVE_TIMEOUT, ERRCOL)

    def on_stream_error(self, event):  # pylint: disable=unused-argument
        """
        EVENT TRIGGERED
        Action on "<<gnss_error>>" event - connection streaming error.

        :param event event: <<gnss_error>> event
        """

        self._refresh_widgets()
        self.conn_status = DISCONNECTED

    def on_ntrip_read(self, event):  # pylint: disable=unused-argument
        """
        EVENT TRIGGERED
        Action on <<ntrip_read>> event - data available on NTRIP queue.

        :param event event: read event
        """

        try:
            raw_data, parsed_data = self.ntrip_inqueue.get(False)
            if (
                raw_data is not None
                and parsed_data is not None
                and isinstance(raw_data, bytes)
            ):
                if self._rtk_conn_status == CONNECTED_NTRIP:
                    source = "NTRIP"
                else:
                    source = "OTHER"
                if isinstance(parsed_data, (RTCMMessage, SPARTNMessage)):
                    if self.conn_status == CONNECTED:
                        self.gnss_outqueue.put(raw_data)
                    self.process_data(raw_data, parsed_data, source + ">>")
                elif isinstance(parsed_data, NMEAMessage):
                    # i.e. NMEA GGA sentence sent to NTRIP server
                    self.process_data(raw_data, parsed_data, source + "<<")
            self.ntrip_inqueue.task_done()
        except Empty:
            pass
        except (SerialException, SerialTimeoutException) as err:
            self.set_status(f"Error sending to device {err}", ERRCOL)

    def on_spartn_read(self, event):  # pylint: disable=unused-argument
        """
        EVENT TRIGGERED
        Action on <<spartn_read>> event - data available on SPARTN queue.

        :param event event: read event
        """

        try:
            raw_data, parsed_data = self.spartn_inqueue.get(False)
            if raw_data is not None and parsed_data is not None:
                if self.conn_status == CONNECTED:
                    self.gnss_outqueue.put(raw_data)
                if self._rtk_conn_status == CONNECTED_SPARTNLB:
                    source = "LBAND"
                elif self._rtk_conn_status == CONNECTED_SPARTNIP:
                    source = "MQTT"
                else:
                    source = "OTHER"
                self.process_data(
                    raw_data,
                    parsed_data,
                    source + ">>",
                )
            self.spartn_inqueue.task_done()

        except Empty:
            pass
        except (SerialException, SerialTimeoutException) as err:
            self.set_status(f"Error sending to device {err}", ERRCOL)

    def update_ntrip_status(self, status: bool, msgt: tuple = None):
        """
        Update NTRIP configuration dialog connection status.

        :param bool status: connected to NTRIP server yes/no
        :param tuple msgt: tuple of (message, color)
        """

        if self.dialog(DLGTNTRIP) is not None:
            self.dialog(DLGTNTRIP).set_controls(status, msgt)

    def get_coordinates(self) -> dict:
        """
        Get current coordinates and fix data.

        :return: dict of coords and fix data
        :rtype: dict
        """

        return {
            "connection": self._conn_status,
            "lat": self.gnss_status.lat,
            "lon": self.gnss_status.lon,
            "alt": self.gnss_status.alt,
            "sep": self.gnss_status.sep,
            "sip": self.gnss_status.sip,
            "fix": self.gnss_status.fix,
            "hdop": self.gnss_status.hdop,
            "diffage": self.gnss_status.diff_age,
            "diffstation": self.gnss_status.diff_station,
        }

    def process_data(self, raw_data: bytes, parsed_data: object, marker: str = ""):
        """
        Update the various GUI widgets, GPX track and log file.

        :param bytes raw_data: raw message data
        :param object parsed data: NMEAMessage, UBXMessage or RTCMMessage
        :param str marker: string prepended to console entries e.g. "NTRIP>>"
        """

        # self.logger.debug(f"data received {parsed_data.identity}")
        settings = self.frm_settings.config
        msgprot = 0
        protfilter = settings["protocol_n"]
        if isinstance(parsed_data, NMEAMessage):
            msgprot = NMEA_PROTOCOL
        elif isinstance(parsed_data, UBXMessage):
            msgprot = UBX_PROTOCOL
        elif isinstance(parsed_data, RTCMMessage):
            msgprot = RTCM3_PROTOCOL
        elif isinstance(parsed_data, SPARTNMessage):
            msgprot = SPARTN_PROTOCOL
        elif isinstance(parsed_data, MQTTMessage):
            msgprot = MQTT_PROTOCOL
        elif isinstance(parsed_data, str):
            marker = "WARNING>>"

        if msgprot == UBX_PROTOCOL and msgprot & protfilter:
            self.ubx_handler.process_data(raw_data, parsed_data)
        elif msgprot == NMEA_PROTOCOL and msgprot & protfilter:
            self.nmea_handler.process_data(raw_data, parsed_data)
        elif msgprot == RTCM3_PROTOCOL and msgprot & protfilter:
            self.rtcm_handler.process_data(raw_data, parsed_data)
        elif msgprot == SPARTN_PROTOCOL and msgprot & protfilter:
            pass
        elif msgprot == MQTT_PROTOCOL:
            pass

        # update chart data if chart is visible
        if widget_state[WDGCHART][VISIBLE]:
            getattr(self, widget_state[WDGCHART][FRAME]).update_data(parsed_data)

        # update consoledata if console is visible and protocol not filtered
        if widget_state[WDGCONSOLE][VISIBLE] and (msgprot == 0 or msgprot & protfilter):
            self._consoledata.append((raw_data, parsed_data, marker))

        # periodically update widgets if visible
        if datetime.now() > self._last_gui_update + timedelta(
            seconds=GUI_UPDATE_INTERVAL
        ):
            self._refresh_widgets()
            self._last_gui_update = datetime.now()

        # update GPX track file if enabled
        if settings["recordtrack_b"]:
            self.file_handler.update_gpx_track()

        # update log file if enabled
        if settings["datalog_b"]:
            self.file_handler.write_logfile(raw_data, parsed_data)

    def _refresh_widgets(self):
        """
        Refresh visible widgets.
        """

        if widget_state[WDGCONSOLE][VISIBLE]:
            self.frm_console.update_console(self._consoledata)
            self._consoledata = []
        self.frm_banner.update_frame()
        for _, widget in widget_state.items():
            frm = getattr(self, widget[FRAME])
            if hasattr(frm, "update_frame") and widget[VISIBLE]:
                frm.update_frame()

    def _check_update(self):
        """
        Check for updated version.
        """

        latest = check_latest(TITLE)
        if latest not in (VERSION, "N/A"):
            self.set_status(f"{VERCHECK} {latest}", ERRCOL)

    def poll_version(self, protocol: str = "UBX"):
        """
        Poll hardware information message for device hardware & firmware version.

        :param str protocol: protocol (UBX)
        """

        if protocol == "NMEA":
            msg = NMEAMessage("P", "QTMVERNO", POLL)
        else:
            msg = UBXMessage("MON", "MON-VER", POLL)
        self.gnss_outqueue.put(msg.serialize())
        self.set_status(
            f"{msg.identity} POLL message sent",
        )

    @property
    def widget_config(self) -> dict:
        """
        Getter for widget configuration.

        :return: configuration
        :rtype: dict
        """

        return {key: vals[VISIBLE] for key, vals in widget_state.items()}

    @property
    def widgets(self) -> dict:
        """
        Getter for widget state.

        :return: widget state
        :rtype: dict
        """

        return widget_state

    @property
    def dialogs(self) -> dict:
        """
        Getter for dialog state.

        :return: dialog state
        :rtype: dict
        """

        return dialog_state

    @property
    def appmaster(self) -> Tk:
        """
        Getter for application master (Tk).

        :return: reference to master Tk instance
        :rtype: Tk
        """

        return self.__master

    @property
    def conn_status(self) -> int:
        """
        Getter for connection status.

        :return: connection status e.g. 1 = CONNECTED
        :rtype: int
        """

        return self._conn_status

    @conn_status.setter
    def conn_status(self, status: int):
        """
        Setter for connection status.

        :param int status: connection status e.g. 1 = CONNECTED
        """

        self._conn_status = status
        self.frm_banner.update_conn_status(status)
        self.frm_settings.enable_controls(status)
        if status == DISCONNECTED:
            self.set_connection(NOTCONN)

    @property
    def rtk_conn_status(self) -> int:
        """
        Getter for SPARTN connection status.

        :return: connection status
        :rtype: int
        """

        return self._rtk_conn_status

    @rtk_conn_status.setter
    def rtk_conn_status(self, status: int):
        """
        Setter for SPARTN connection status.

        :param int status: connection status
        """

        self._rtk_conn_status = status
        self.frm_banner.update_rtk_status(status)

    def svin_countdown(self, dur: int, valid: bool, active: bool):
        """
        Countdown survey-in duration for NTRIP caster mode.

        :param int dur: elapsed time
        :param bool valid: valid flag
        :param bool active: active flag
        """

        if self.frm_settings.frm_socketserver is not None:
            self.frm_settings.frm_socketserver.svin_countdown(dur, valid, active)
