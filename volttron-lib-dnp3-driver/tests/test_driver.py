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
# }}}

"""Integration tests for volttron-lib-dnp3-driver"""

import gevent
import pytest
from volttron.client.known_identities import CONFIGURATION_STORE, PLATFORM_DRIVER
from volttron.utils import jsonapi
from volttrontesting.platformwrapper import PlatformWrapper


def test_scrape_all(publish_agent):
    # add DNP3 Driver to Platform Driver
    registry_config_string = """Point Name,Volttron Point Name,Units,Units Details,Writable,Starting Value,Type,Notes
        SampleLong1,SampleLong1,Enumeration,1 through 13,FALSE,50,int,Status indicator of service switch
        SampleWritableShort1,SampleWritableShort1,%,0.00 to 100.00 (20 default),TRUE,20,int,Minimum damper position during the standard mode
        SampleBool1,SampleBool1,On / Off,on/off,FALSE,TRUE,boolean,Status indidcator of cooling stage 1"""
    publish_agent.vip.rpc.call(CONFIGURATION_STORE,
                               "manage_store",
                               PLATFORM_DRIVER,
                               "dnp3.csv",
                               registry_config_string,
                               config_type="csv")

    driver_config = {
        "driver_config": {},
        "registry_config": "config://dpn3.csv",
        "interval": 5,
        "timezone": "US/Pacific",
        "heart_beat_point": "Heartbeat",
        "driver_type": "dnp3"
    }
    publish_agent.vip.rpc.call(CONFIGURATION_STORE,
                               "manage_store",
                               PLATFORM_DRIVER,
                               "devices/dnp3",
                               jsonapi.dumps(driver_config),
                               config_type='json')

    gevent.sleep(10)

    actual_scrape_all_results = publish_agent.vip.rpc.call(PLATFORM_DRIVER, "scrape_all",
                                                           "dnp3").get(timeout=10)
    expected_scrape_all_results = {
        'SampleLong1': 50,
        'SampleBool1': True,
        'SampleWritableShort1': 20
    }
    assert actual_scrape_all_results == expected_scrape_all_results


def test_get_point_set_point(publish_agent):
    # TODO: implement this for DNP3 driver
    actual_sampleWriteableShort1 = publish_agent.vip.rpc.call(
        PLATFORM_DRIVER, "get_point", "dnp3", "SampleWritableShort1").get(timeout=10)
    assert actual_sampleWriteableShort1 == 20

    #set_point
    actual_sampleWriteableShort1 = publish_agent.vip.rpc.call(PLATFORM_DRIVER, "set_point", "fake",
                                                              "SampleWritableShort1",
                                                              42).get(timeout=10)
    assert actual_sampleWriteableShort1 == 42
    actual_sampleWriteableShort1 = publish_agent.vip.rpc.call(
        PLATFORM_DRIVER, "get_point", "fake", "SampleWritableShort1").get(timeout=10)
    assert actual_sampleWriteableShort1 == 42


def test_fixture(publish_agent):
    print(publish_agent)
    rs = publish_agent.vip.rpc.call(CONFIGURATION_STORE,
                        "manage_list_stores",
                        ).get(10)
    print(f"========== rs {rs}")

    rs = publish_agent.vip.peerlist.list().get(10)
    print(f"========== rs {rs}")

    rs = publish_agent.vip.rpc.call(CONFIGURATION_STORE,
                                    "manage_list_configs",
                                    PLATFORM_DRIVER
                                    ).get(10)
    print(f"========== rs {rs}")


@pytest.fixture(scope="module")
def publish_agent(volttron_instance: PlatformWrapper):
    assert volttron_instance.is_running()
    vi = volttron_instance
    assert vi is not None
    assert vi.is_running()

    # install platform driver
    config = {
        "driver_scrape_interval": 0.05,
        "publish_breadth_first_all": "false",
        "publish_depth_first": "false",
        "publish_breadth_first": "false"
    }
    puid = vi.install_agent(agent_dir="volttron-platform-driver",
                            config_file=config,
                            start=False,
                            vip_identity=PLATFORM_DRIVER)
    assert puid is not None
    gevent.sleep(1)  # TODO use retry logic/flexible sleep
    assert vi.start_agent(puid)
    assert vi.is_agent_running(puid)

    # create the publish agent
    publish_agent = volttron_instance.build_agent()
    assert publish_agent.core.identity
    gevent.sleep(1)  # TODO use retry logic/flexible sleep

    capabilities = {"edit_config_store": {"identity": PLATFORM_DRIVER}}
    volttron_instance.add_capabilities(publish_agent.core.publickey, capabilities)

    # Add Fake Driver to Platform Driver
    registry_config_string = """Point Name,Volttron Point Name,Units,Units Details,Writable,Starting Value,Type,Notes
    SampleLong1,SampleLong1,Enumeration,1 through 13,FALSE,50,int,Status indicator of service switch
    SampleWritableShort1,SampleWritableShort1,%,0.00 to 100.00 (20 default),TRUE,20,int,Minimum damper position during the standard mode
    SampleBool1,SampleBool1,On / Off,on/off,FALSE,TRUE,boolean,Status indidcator of cooling stage 1"""
    publish_agent.vip.rpc.call(CONFIGURATION_STORE,
                               "manage_store",
                               PLATFORM_DRIVER,
                               "fake.csv",
                               registry_config_string,
                               config_type="csv")
    gevent.sleep(1)  # TODO use retry logic/flexible sleep

    driver_config = {
        "driver_config": {},
        "registry_config": "config://fake.csv",
        "interval": 5,
        "timezone": "US/Pacific",
        "heart_beat_point": "Heartbeat",
        "driver_type": "fake"
    }
    publish_agent.vip.rpc.call(CONFIGURATION_STORE,
                               "manage_store",
                               PLATFORM_DRIVER,
                               "devices/fake",
                               jsonapi.dumps(driver_config),
                               config_type='json')

    gevent.sleep(10)  # TODO use retry logic/flexible sleep
    # TODO add assert to check if config store success.

    yield publish_agent

    volttron_instance.stop_agent(puid)
    publish_agent.core.stop()
