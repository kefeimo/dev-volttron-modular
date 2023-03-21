# -*- coding: utf-8 -*- {{{
# ===----------------------------------------------------------------------===
#
#                 Installable Component of Eclipse VOLTTRON
#
# ===----------------------------------------------------------------------===
#
# Copyright 2022 Battelle Memorial Institute
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may not
# use this file except in compliance with the License. You may obtain a copy
# of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.
#
# ===----------------------------------------------------------------------===

from pathlib import Path
from pprint import pformat
from typing import Callable, Dict

from volttron.client.messaging import (headers)
from volttron.client.vip.agent import Agent
from volttron.client.vip.agent.subsystems.rpc import RPC
from volttron.utils import (format_timestamp, get_aware_utc_now, load_config,
                            setup_logging, vip_main)

from dnp3_outstation.volttron_openadr_client import (
    VolttronOpenADRClient,
    OpenADRClientInterface,
    OpenADREvent,
    OpenADRReportName,
    OpenADRMeasurements,
    OpenADROpt,
)

from dnp3_outstation.constants import (REQUIRED_KEYS, VEN_NAME, VTN_URL, DEBUG,
                                       CERT, KEY, PASSPHRASE, VTN_FINGERPRINT,
                                       SHOW_FINGERPRINT, CA_FILE, VEN_ID,
                                       DISABLE_SIGNATURE, OPENADR_EVENT)

from openleadr.objects import Event

import logging
import asyncio
import sys
import gevent

from dnp3_python.dnp3station.outstation_new import MyOutStationNew
from pydnp3 import opendnp3
from volttron.client.vip.agent import Agent, Core, RPC

setup_logging()
_log = logging.getLogger(__name__)
__version__ = "1.0"


class Dnp3OutstationAgent(Agent):
    """This is class is a subclass of the Volttron Agent; it is an OpenADR VEN client and is a wrapper around OpenLEADR,
    an open-source implementation of OpenADR 2.0.b for both servers, VTN, and clients, VEN.
    This agent creates an instance of OpenLEADR's VEN client, which is used to communicated with a VTN.
    OpenADR (Automated Demand Response) is a standard for alerting and responding
    to the need to adjust electric power consumption in response to fluctuations in grid demand.
    OpenADR communications are conducted between Virtual Top Nodes (VTNs) and Virtual End Nodes (VENs).

    :param config_path: path to agent config
    """

    def __init__(self, config_path: str, **kwargs) -> None:
        # adding 'fake_ven_client' to support dependency injection and preventing call to super class for unit testing
        # self.ven_client: OpenADRClientInterface
        # if kwargs.get("fake_ven_client"):
        #     self.ven_client = kwargs["fake_ven_client"]
        # else:
        #     super(OpenADRVenAgent, self).__init__(enable_web=True, **kwargs)
        super().__init__(enable_web=True, **kwargs)

        self.default_config = self._parse_config(config_path)

        print(f"===================== # SubSystem/ConfigStore")
        print(f"===================== # config_path {config_path}")
        print(f"===================== # **kwargs {kwargs}")

        # dnp3 outstation config
        # "outstation_ip": "0.0.0.0",
        # "master_id": 2,
        # "outstation_id": 1,
        # "port": 20000,

        default_config: dict = {'outstation_ip': '0.0.0.0', 'port': 20000, 'master_id': 2, 'outstation_id': 1}
        # agent configuration using volttron config framework
        # get_volttron_cofig, set_volltron_config
        self._volttron_config: dict
        self._dnp3_outstation_config = default_config

        # TODO: get this part back or rearrange the config workflow logic
        config_when_installed = self._parse_config(config_path)
        # for dnp3 features
        # try:
        #     self.outstation_application = MyOutStationNew(**config_when_installed)
        #     _log.info(f"init dnp3 outstation with {config_when_installed}")
        #     self._volttron_config = config_when_installed
        # except Exception as e:
        #     _log.error(e)
        #     self.outstation_application = MyOutStationNew(**self.default_config)
        #     _log.info(f"init dnp3 outstation with {self.default_config}")

        self.outstation_application = MyOutStationNew(**default_config)

        # SubSystem/ConfigStore
        self.vip.config.set_default("config", self.default_config)
        self.vip.config.subscribe(
            self._config_callback_dummy,  # TODO: cleanup: used to be _configure_ven_client
            actions=["NEW", "UPDATE"],
            pattern="config",
        )  # TODO: understand what vip.config.subscribe does

    @property
    def dnp3_outstation_config(self):
        return self._dnp3_outstation_config

    @dnp3_outstation_config.setter
    def dnp3_outstation_config(self, config: dict):
        # TODO: add validation
        self._dnp3_outstation_config = config

    def _config_callback_dummy(self, config_name: str, action: str,
                               contents: Dict) -> None:
        pass

    @Core.receiver("onstart")
    def onstart(self, sender, **kwargs):
        """
        This is method is called once the Agent has successfully connected to the platform.
        This is a good place to setup subscriptions if they are not dynamic or
        do any other startup activities that require a connection to the message bus.
        Called after any configurations methods that are called at startup.
        Usually not needed if using the configuration store.
        """

        # for dnp3 outstation
        self.outstation_application.start()

        # Example publish to pubsub
        # self.vip.pubsub.publish('pubsub', "some/random/topic", message="HI!")
        #
        # # Example RPC call
        # # self.vip.rpc.call("some_agent", "some_method", arg1, arg2)
        # pass
        # self._create_subscriptions(self.setting2)

    def _configure_ven_client(self, config_name: str, action: str,
                              contents: Dict) -> None:
        """Initializes the agent's configuration, creates and starts VolttronOpenADRClient.

        :param config_name:
        :param action: the action
        :param contents: the configuration used to update the agent's configuration
        """
        config = self.default_config.copy()
        config.update(contents)

        _log.info(f"config_name: {config_name}, action: {action}")
        _log.info(f"Configuring VEN client with: \n {pformat(config)} ")

        # self.ven_client = VolttronOpenADRClient.build_client(config)

        # Add event handling capability to the client
        # if you want to add more handlers on a specific event, you must create a coroutine in this class
        # and then add it as the second input for 'self.ven_client.add_handler(<some event>, <coroutine>)'
        # self.ven_client.add_handler("on_event", self.handle_event)
        #
        # _log.info("Starting OpenADRVen agent...")
        # gevent.spawn_later(3, self._start_asyncio_loop)

    # def _start_asyncio_loop(self) -> None:
    #     loop = asyncio.get_event_loop()
    #     loop.create_task(self.ven_client.run())
    #     loop.run_forever()
    #
    # # ***************** Methods for Servicing VTN Requests ********************
    #
    # async def handle_event(self, event: Event) -> OpenADROpt:
    #     """Publish event to the Volttron message bus. This coroutine will be called when there is an event to be handled.
    #
    #     :param event: The event sent from a VTN
    #     :return: Message to VTN to opt in to the event.
    #     """
    #     openadr_event = OpenADREvent(event)
    #     try:
    #         _log.info(
    #             f"Received event. Processing event now...\n Event signal:\n {pformat(openadr_event.get_event_signals())}"
    #         )
    #     except IndexError as e:
    #         _log.debug(
    #             f"Event signals is empty. {e} \n Showing whole event: {pformat(openadr_event)}"
    #         )
    #         pass
    #
    #     self.publish_event(openadr_event)
    #
    #     return OpenADROpt.OPT_IN

    @RPC.export
    def add_report_capability(
            self,
            callback: Callable,
            report_name: OpenADRReportName,
            resource_id: str,
            measurement: OpenADRMeasurements,
    ) -> tuple:
        """Add a new reporting capability to the client.

        This method is remotely accessible by other agents through Volttron's feature Remote Procedure Call (RPC);
        for reference on RPC, see https://volttron.readthedocs.io/en/develop/platform-features/message-bus/vip/vip-json-rpc.html?highlight=remote%20procedure%20call

        :param callback: A callback or coroutine that will fetch the value for a specific report. This callback will be passed the report_id and the r_id of the requested value.
        :param report_name: An OpenADR name for this report
        :param resource_id: A specific name for this resource within this report.
        :param measurement: The quantity that is being measured
        :return: Returns a tuple consisting of a report_specifier_id (str) and an r_id (str) an identifier for OpenADR messages
        """
        report_specifier_id, r_id = self.ven_client.add_report(
            callback=callback,
            report_name=report_name,
            resource_id=resource_id,
            measurement=measurement,
        )
        _log.info(
            f"Output from add_report: report_specifier_id: {report_specifier_id}, r_id: {r_id}"
        )
        return report_specifier_id, r_id

    # ***************** VOLTTRON Pub/Sub Requests ********************
    def publish_event(self, event: OpenADREvent) -> None:
        """Publish an event to the Volttron message bus. When an event is created/updated, it is published to the VOLTTRON bus with a topic that includes 'openadr/event_update'.

        :param event: The Event received from the VTN
        """
        # OADR rule 6: If testEvent is present and != "false", handle the event as a test event.
        try:
            if event.isTestEvent():
                _log.debug("Suppressing publication of test event")
                return
        except KeyError as e:
            _log.debug(f"Key error: {e}")
            pass
        _log.debug(
            f"Publishing real/non-test event \n {pformat(event.parse_event())}"
        )
        self.vip.pubsub.publish(
            peer="pubsub",
            topic=
            f"{OPENADR_EVENT}/{event.get_event_id()}/{self.ven_client.get_ven_name()}",
            headers={headers.TIMESTAMP: format_timestamp(get_aware_utc_now())},
            message=event.parse_event(),
        )

        return

    # ***************** Helper methods ********************
    def _parse_config(self, config_path: str) -> Dict:
        """Parses the OpenADR agent's configuration file.

        :param config_path: The path to the configuration file
        :return: The configuration
        """
        # TODO: added capability to configuration based on tabular config vile (e.g., csv)
        try:
            config = load_config(config_path)
        except NameError as err:
            _log.exception(err)
            raise
        except Exception as err:
            _log.error("Error loading configuration: {}".format(err))
            config = {}

        print(f"============= def _parse_config config {config}")

        if not config:
            raise Exception("Configuration cannot be empty.")

        # req_keys_actual = {k: "" for k in REQUIRED_KEYS}
        # for required_key in REQUIRED_KEYS:
        #     key_actual = config.get(required_key)
        #     self._check_required_key(required_key, key_actual)
        #     req_keys_actual[required_key] = key_actual

        # optional configurations
        cert = config.get(CERT)
        if cert:
            cert = str(Path(cert).expanduser().resolve(strict=True))
        key = config.get(KEY)
        if key:
            key = str(Path(key).expanduser().resolve(strict=True))
        ca_file = config.get(CA_FILE)
        if ca_file:
            ca_file = str(Path(ca_file).expanduser().resolve(strict=True))
        debug = config.get(DEBUG)
        ven_name = config.get(VEN_NAME)
        vtn_url = config.get(VTN_URL)
        passphrase = config.get(PASSPHRASE)
        vtn_fingerprint = config.get(VTN_FINGERPRINT)
        show_fingerprint = bool(config.get(SHOW_FINGERPRINT, True))
        ven_id = config.get(VEN_ID)
        disable_signature = bool(config.get(DISABLE_SIGNATURE))

        return {
            VEN_NAME: ven_name,
            VTN_URL: vtn_url,
            DEBUG: debug,
            CERT: cert,
            KEY: key,
            PASSPHRASE: passphrase,
            VTN_FINGERPRINT: vtn_fingerprint,
            SHOW_FINGERPRINT: show_fingerprint,
            CA_FILE: ca_file,
            VEN_ID: ven_id,
            DISABLE_SIGNATURE: disable_signature,
        }

    def _check_required_key(self, required_key: str, key_actual: str) -> None:
        """Checks if the given key and its value are required by this agent

        :param required_key: the key that is being checked
        :param key_actual: the key value being checked
        :raises KeyError:
        """
        if required_key == VEN_NAME and not key_actual:
            raise KeyError(f"{VEN_NAME} is required.")
        elif required_key == VTN_URL and not key_actual:
            raise KeyError(
                f"{VTN_URL} is required. Ensure {VTN_URL} is given a URL to the VTN."
            )
        return

    @RPC.export
    def rpc_dummy(self) -> str:
        """
        For testing rpc call
        """
        return "This is a dummy rpc call"

    @RPC.export
    def outstation_reset(self, **kwargs):
        """update`self._volttron_config`, then init a new outstation.
        For post-configuration and immediately take effect.
        Note: will start a new outstation instance and the old database data will lose"""
        # self.dnp3_outstation_config(**kwargs)
        try:
            self.outstation_application.shutdown()
            outstation_app_new = MyOutStationNew(**self.dnp3_outstation_config)
            self.outstation_application = outstation_app_new
            self.outstation_application.start()
            _log.info(f"Outstation has restarted")
        except Exception as e:
            _log.error(e)

    @RPC.export
    def outstation_get_db(self) -> dict:
        """expose db"""
        return self.outstation_application.db_handler.db

    @RPC.export
    def outstation_get_config(self) -> dict:
        """expose get_config"""
        return self.outstation_application.get_config()

    @RPC.export
    def outstation_is_connected(self) -> bool:
        """expose is_connected, note: status, property"""
        return self.outstation_application.is_connected

    @RPC.export
    def outstation_apply_update_analog_input(self, val: float, index: int) -> dict:
        """public interface to update analog-input point value
        val: float
        index: int, point index
        """
        if not isinstance(val, float):
            raise f"val of type(val) should be float"
        self.outstation_application.apply_update(opendnp3.Analog(value=val), index)
        _log.debug(f"Updated outstation analog-input index: {index}, val: {val}")

        return self.outstation_application.db_handler.db

    @RPC.export
    def outstation_apply_update_analog_output(self, val: float, index: int) -> dict:
        """public interface to update analog-output point value
        val: float
        index: int, point index
        """

        if not isinstance(val, float):
            raise f"val of type(val) should be float"
        self.outstation_application.apply_update(opendnp3.AnalogOutputStatus(value=val), index)
        _log.debug(f"Updated outstation analog-output index: {index}, val: {val}")

        return self.outstation_application.db_handler.db

    @RPC.export
    def outstation_apply_update_binary_input(self, val: bool, index: int):
        """public interface to update binary-input point value
        val: bool
        index: int, point index
        """
        if not isinstance(val, bool):
            raise f"val of type(val) should be bool"
        self.outstation_application.apply_update(opendnp3.Binary(value=val), index)
        _log.debug(f"Updated outstation binary-input index: {index}, val: {val}")

        return self.outstation_application.db_handler.db

    @RPC.export
    def outstation_apply_update_binary_output(self, val: bool, index: int):
        """public interface to update binary-output point value
        val: bool
        index: int, point index
        """
        if not isinstance(val, bool):
            raise f"val of type(val) should be bool"
        self.outstation_application.apply_update(opendnp3.BinaryOutputStatus(value=val), index)
        _log.debug(f"Updated outstation binary-output index: {index}, val: {val}")

        return self.outstation_application.db_handler.db

    @RPC.export
    def outstation_update_config_with_restart(self,
                                              outstation_ip: str = None,
                                              port: int = None,
                                              master_id: int = None,
                                              outstation_id: int = None,
                                              **kwargs):
        config = self._dnp3_outstation_config.copy()
        print(f"============ config 1 {config}")
        for kwarg in [{"outstation_ip": outstation_ip},
                      {"port": port},
                      {"master_id": master_id}, {"outstation_id": outstation_id}]:
            print(f"======== kwarg {kwarg}")
            if list(kwarg.values())[0] is not None:
                config.update(kwarg)
        print(f"=========== port {port}")
        print(f"============ config 2{config}")
        self._dnp3_outstation_config = config
        # # {'outstation_ip': '0.0.0.0', 'port': 20000, 'master_id': 2, 'outstation_id': 1}
        self.outstation_reset()


def main():
    """Main method called to start the agent."""
    vip_main(Dnp3OutstationAgent)


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        pass
