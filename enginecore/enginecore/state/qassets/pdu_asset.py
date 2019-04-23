"""Event handler for PDU;
PDU is a rather dumb device, its power state changes depending on the upstream power (parent)
Plus there's an SNMP agent running in the background
"""
# **due to circuit callback signature
# pylint: disable=W0613

import logging

from circuits import handler
import enginecore.state.qassets.state_managers as sm
from enginecore.state.qassets.asset import Asset
from enginecore.state.qassets.snmp_asset import SNMPSim

from enginecore.state.qassets.asset_definition import register_asset


@register_asset
class PDU(Asset, SNMPSim):
    """Provides reactive logic for PDU & manages snmp simulator instance
    Example:
        powers down when upstream power becomes unavailable 
        powers back up when upstream power is restored
    """

    channel = "engine-pdu"
    StateManagerCls = sm.PDUStateManager

    def __init__(self, asset_info):
        Asset.__init__(self, PDU.StateManagerCls(asset_info))
        SNMPSim.__init__(
            self, asset_info["key"], asset_info["host"], asset_info["port"]
        )

        self.state.update_agent(self._snmp_agent.pid)

        agent_info = self.state.agent
        if not agent_info[1]:
            logging.error(
                "Asset:[%s] - agent process (%s) failed to start!",
                self.state.key,
                agent_info[0],
            )
        else:
            logging.info(
                "Asset:[%s] - agent process (%s) is up & running",
                self.state.key,
                agent_info[0],
            )

    @handler("ParentAssetPowerDown")
    def on_parent_asset_power_down(self, event, *args, **kwargs):
        """Power off & stop snmp simulator instance when parent is down"""

        e_result = self.power_off()

        if e_result.new_state == e_result.old_state:
            event.success = False
        else:
            self._snmp_agent.stop_agent()

        return e_result

    @handler("ParentAssetPowerUp")
    def on_power_up_request_received(self, event, *args, **kwargs):
        """Power up PDU when upstream power source is restored """
        e_result = self.power_up()
        event.success = e_result.new_state != e_result.old_state

        return e_result
