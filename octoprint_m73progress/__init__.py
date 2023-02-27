# coding=utf-8
from __future__ import absolute_import, division

import logging

import octoprint.plugin
from octoprint.events import Events
from octoprint.printer import PrinterCallback


logger = logging.getLogger(__name__)

class TimeLeftChangedHander():
    def on_time_left_changed(self, time_left):
        return


class ProgressMonitor(PrinterCallback):
    def __init__(self, *args, **kwargs):
        super(ProgressMonitor, self).__init__(*args, **kwargs)
        self.reset()

    def reset(self):
        self._time_left_m_old = None
        self._time_left_m_current = None

    def on_printer_send_current_data(self, data):
        self._time_left_m_old = self.time_left_m_current
        self._time_left_m_current = int(data["progress"]["printTimeLeft"]/60)

        if (
            self._time_left_m_current is not None and 
            self._time_left_m_old is not None and 
            self._time_left_m_old != self.time_left_m_current
        ):
            self._handler.on_time_left_changed(self._time_left_m_current)

    def set_plugin(self, handler: TimeLeftChangedHander):
        self._handler = handler


class M73progressPlugin(
    octoprint.plugin.ProgressPlugin,
    octoprint.plugin.EventHandlerPlugin,
    octoprint.plugin.StartupPlugin,
    octoprint.plugin.RestartNeedingPlugin,
    TimeLeftChangedHander
):
    def on_after_startup(self):
        self._progress = ProgressMonitor()
        self._printer.register_callback(self._progress)

    def on_event(self, event, payload):
        if event == Events.PRINT_STARTED or event == Events.PRINT_DONE:
            # Firmware manages progress bar when printing from SD card
            if payload.get("origin", "") == "sdcard":
                return

        if event == Events.PRINT_STARTED:
            self._progress.reset()
            self._set_progress(progress=0)
        elif event == Events.PRINT_DONE:
            self._set_progress(progress=100, time_left=0)

    def on_print_progress(self, storage, path, progress):
        if not self._printer.is_printing():
            return

        # Firmware manages progress bar when printing from SD card
        if storage == "sdcard":
            return

        self._set_progress(progress=progress)

    def on_time_left_changed(self, time_left):
        self._set_progress(time_left=time_left)

    def _set_progress(self, progress=None, time_left=None):
        if time_left is None and progress is None: 
            return

        if time_left is None:
            gcode = "M73 P{:.0f}".format(progress)
        elif progress is None:
            gcode = "M73 R{:.0f}".format(time_left)
        else:
            gcode = "M73 P{:.0f} R{:.0f}".format(progress, time_left)

        self._printer.commands(gcode)

    # def get_update_information(self):
    #     return dict(
    #         m73progress=dict(
    #             displayName="M73 Progress Plugin",
    #             displayVersion=self._plugin_version,

    #             # version check: github repository
    #             type="github_release",
    #             user="cesarvandevelde",
    #             repo="OctoPrint-M73Progress",
    #             current=self._plugin_version,

    #             # update method: pip
    #             pip="https://github.com/cesarvandevelde/OctoPrint-M73Progress/archive/{target_version}.zip"
    #         )
    #     )


__plugin_name__ = "M73 Progress Plugin"
__plugin_pythoncompat__ = ">=2.7,<4"


def __plugin_load__():
    global __plugin_implementation__
    __plugin_implementation__ = M73progressPlugin()

    # global __plugin_hooks__
    # __plugin_hooks__ = {
    #     "octoprint.plugin.softwareupdate.check_config":
    #         __plugin_implementation__.get_update_information
    # }
