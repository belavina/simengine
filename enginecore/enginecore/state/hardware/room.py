"""Components controlling physical space of server racks"""
import time
import operator
from threading import Thread
import logging
import random

from circuits import Component

import enginecore.state.hardware.internal_state as in_state

# Import all hardware assets in order for them to be registered
# pylint: disable=unused-import
from enginecore.state.hardware.asset import Asset
from enginecore.state.hardware.ups_asset import UPS
from enginecore.state.hardware.pdu_asset import PDU
from enginecore.state.hardware.server_asset import Server, ServerWithBMC, PSU
from enginecore.state.hardware.static_asset import StaticAsset, Lamp
from enginecore.state.hardware.outlet_asset import Outlet

# pylint: enable=unused-import


class ServerRoom(Component):
    """Represents hardware environment (Room/ServerRack);
    Room manages ambient temperature by monitoring power outages (AC going down)
    and power restorations after blackouts.
    """

    def __init__(self):
        super(ServerRoom, self).__init__()

        # threads to track
        self._temp_warming_t = None
        self._temp_cooling_t = None
        self._voltage_fluct_t = None

        # set up default values on the first run (if not set by the user)
        if not in_state.StateManager.get_ambient_props():
            shared_attr = {"degrees": 1, "rate": 20, "start": 19, "end": 28}
            in_state.StateManager.set_ambient_props(
                {**shared_attr, **{"event": "down", "pause_at": 28}}
            )
            in_state.StateManager.set_ambient_props(
                {**shared_attr, **{"event": "up", "pause_at": 21}}
            )

        if not in_state.StateManager.get_voltage_props():
            in_state.StateManager.set_voltage_props(
                {
                    "mu": 120,
                    "sigma": 5,
                    "min": 117,
                    "max": 124,
                    "method": "uniform",
                    "rate": 6,
                    "enabled": True,
                }
            )

        # initialize server room environment
        in_state.StateManager.power_restore()

        self._init_thermal_threads()
        self._init_voltage_thread()

    @staticmethod
    def _keep_changing_temp(event, env, bound_op, temp_op):
        """Change room temperature until limit is reached or AC state changes
        
        Args:
            event(str): on up/down event
            env(callable): update while the environment is in certain condition
            bound_op(callable): operator; reached max/min
            temp_op(callable): calculate new temperature
        """

        # ambient props contains details like min/max temperature value;
        # increase/decrease steps etc.
        get_amb_props = lambda: in_state.StateManager.get_ambient_props()[0][event]
        amb_props = get_amb_props()

        while True:

            time.sleep(amb_props["rate"])

            # check if room environment matches the conditions
            # required for ambient update
            if not env():
                amb_props = get_amb_props()
                continue

            # get old & calculate new temperature values
            current_temp = in_state.StateManager.get_ambient()
            new_temp = temp_op(current_temp, amb_props["degrees"])
            needs_update = False

            msg_format = "Server Room: ambient %s° updated to %s°"

            # sets to max/min temperature value if ambient is about to reach it
            needs_update = bound_op(new_temp, amb_props["pauseAt"])
            if not needs_update and bound_op(current_temp, amb_props["pauseAt"]):
                new_temp = amb_props["pauseAt"]
                needs_update = True

            # update ambient
            if needs_update:
                logging.info(msg_format, current_temp, new_temp)
                in_state.StateManager.set_ambient(new_temp)

            amb_props = get_amb_props()

    @staticmethod
    def _keep_fluctuating_voltage():
        """Update input voltage every n seconds"""

        get_volt_props = lambda: in_state.StateManager.get_voltage_props()[0]
        volt_props = get_volt_props()

        while True:
            time.sleep(volt_props["rate"])

            if not volt_props["enabled"] or not in_state.StateManager.mains_status():
                volt_props = get_volt_props()
                continue

            if volt_props["method"] == "gauss":
                rand_v = random.gauss(volt_props["mu"], volt_props["sigma"])
            else:
                rand_v = random.uniform(volt_props["min"], volt_props["max"])

            in_state.StateManager.set_voltage(rand_v)
            volt_props = get_volt_props()

    def _launch_thermal_thread(self, name, th_kwargs):
        """Start up a thread that will be changing ambient depending on environment
        Args:
            name(str): target thread name
            th_kwargs(dict): parameters to be passed to _keep_changing_temp
        """

        thread = Thread(target=self._keep_changing_temp, kwargs=th_kwargs, name=name)

        thread.daemon = True
        thread.start()

        return thread

    def _init_voltage_thread(self):
        """Initialize voltage fluctuations threading"""

        if self._voltage_fluct_t and self._voltage_fluct_t.isAlive():
            logging.warning("Voltage thread is already running!")
            return

        self._voltage_fluct_t = Thread(
            target=self._keep_fluctuating_voltage, name="voltage_fluctuation"
        )

        self._voltage_fluct_t.daemon = True
        self._voltage_fluct_t.start()

    def _init_thermal_threads(self):
        """Initialize thermal threads associated with the server room environment"""

        self._temp_warming_t = self._launch_thermal_thread(
            "temp_warming",
            {
                "env": lambda: not in_state.StateManager.mains_status(),
                "temp_op": operator.add,
                "bound_op": operator.lt,
                "event": "down",
            },
        )
        self._temp_cooling_t = self._launch_thermal_thread(
            "temp_cooling",
            {
                "env": in_state.StateManager.mains_status,
                "temp_op": operator.sub,
                "bound_op": operator.gt,
                "event": "up",
            },
        )

    def __str__(self):

        wall_power_status = in_state.StateManager.mains_status()
        horizontal_line = "-" * 20

        th_warming_status = (
            "up" if self._temp_warming_t.isAlive() else "down",
            "enabled" if not wall_power_status else "disabled",
        )

        th_cooling_status = (
            "up" if self._temp_cooling_t.isAlive() else "down",
            "enabled" if wall_power_status else "disabled",
        )

        return "\n".join(
            (
                horizontal_line,
                "Server Room: ",
                horizontal_line,
                "  [The mains] " "on" if wall_power_status else "off",
                "  [AC]        " "on" if wall_power_status else "off",
                ":Ambient Threads:",
                "  [warming] " + "/".join(th_warming_status),
                "  [cooling] " + "/".join(th_cooling_status),
                # TODO: add voltage
            )
        )
