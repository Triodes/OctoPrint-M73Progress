# coding=utf-8
from __future__ import absolute_import, division

import logging

import octoprint.plugin
from octoprint.events import Events
from octoprint.printer import PrinterCallback


logger = logging.getLogger(__name__)

class TimeLeftChangedHander():
    def on_time_left_changed(self, time_left):
        pass


class ProgressMonitor(PrinterCallback):
    def __init__(self, *args, **kwargs):
        super(ProgressMonitor, self).__init__(*args, **kwargs)
        self.reset()

    def reset(self):
        self._time_left_s = None
        self._time_elapsed_s = None

        self._time_left_m_old = None
        self._time_left_m_current = None

        self._progress_old = None
        self._progress_current = None

    def on_printer_send_current_data(self, data):
        self._time_left_s = data["progress"]["printTimeLeft"]
        self._time_elapsed_s = data["progress"]["printTime"]

        if (self._time_left_s is not None):
            self._time_left_m_old = self._time_left_m_current
            self._time_left_m_current = int(self._time_left_s/60.0)
            
            if (self._time_elapsed_s is not None):
                progress = float(self._time_elapsed_s)/float(self._time_elapsed_s + self._time_left_s)

                self._progress_old = self._progress_current
                self._progress_current = int(progress*100.0)

        if (
            (self._time_left_m_current is not None and self._time_left_m_old != self._time_left_m_current) or
            (self._progress_current is not None and self._progress_old != self._progress_current)
        ):
            self._handler.on_time_left_changed(self._time_left_m_current, self._progress_current)

    def set_plugin(self, handler: TimeLeftChangedHander):
        self._handler = handler


class M73progressPlugin(
    octoprint.plugin.EventHandlerPlugin,
    octoprint.plugin.StartupPlugin,
    octoprint.plugin.RestartNeedingPlugin,
    TimeLeftChangedHander
):
    def on_after_startup(self):
        self._progress_monitor = ProgressMonitor()
        self._progress_monitor.set_plugin(self)
        self._printer.register_callback(self._progress_monitor)

    def on_event(self, event, payload):
        if event == Events.PRINT_STARTED or event == Events.PRINT_DONE:
            # Firmware manages progress bar when printing from SD card
            if payload.get("origin", "") == "sdcard":
                return

        if event == Events.PRINT_STARTED:
            self._progress_monitor.reset()
            self.on_time_left_changed(progress=0)
        elif event == Events.PRINT_DONE:
            self.on_time_left_changed(progress=100, time_left=0)

    def on_time_left_changed(self, time_left, progress):
        if time_left is None and progress is None: 
            return

        if time_left is None:
            gcode = "M73 P{:.0f}".format(progress)
        elif progress is None:
            gcode = "M73 R{:.0f}".format(time_left)
        else:
            gcode = "M73 P{:.0f} R{:.0f}".format(progress, time_left)
        
        self._printer.commands(gcode)
        self._logger.debug('Progress plugin sent gcode: %s', gcode)

    def get_update_information(self):
        return dict(
            m73progress=dict(
                displayName="M73 Progress Plugin",
                displayVersion=self._plugin_version,

                # version check: github repository
                type="github_release",
                user="Triodes",
                repo="OctoPrint-M73Progress",
                current=self._plugin_version,

                # update method: pip
                pip="https://github.com/Triodes/OctoPrint-M73Progress/archive/{target_version}.zip"
            )
        )


__plugin_name__ = "M73 Progress Plugin"
__plugin_pythoncompat__ = ">=2.7,<4"


def __plugin_load__():
    global __plugin_implementation__
    __plugin_implementation__ = M73progressPlugin()

    global __plugin_hooks__
    __plugin_hooks__ = {
        "octoprint.plugin.softwareupdate.check_config":
            __plugin_implementation__.get_update_information
    }
