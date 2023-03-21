import pytest
import os
from volttron.client.vip.agent import build_agent
from time import sleep
import datetime
from dnp3_outstation.agent import OpenADRVenAgent


@pytest.fixture(scope="module")
def vip_agent():
    a = build_agent()
    print(a)
    return a


def test_vip_agent(vip_agent):
    print(vip_agent)


def test_dummy(vip_agent):
    peer = "dnp3_outstation"
    method = OpenADRVenAgent.rpc_dummy
    peer_method = "rpc_dummy"
    rs = vip_agent.vip.rpc.call(peer, peer_method).get(timeout=5)
    print(datetime.datetime.now(), "rs: ", rs)


def test_outstation_reset(vip_agent):
    peer = "dnp3_outstation"
    method = OpenADRVenAgent.outstation_reset
    peer_method = "outstation_reset"
    rs = vip_agent.vip.rpc.call(peer, peer_method).get(timeout=5)
    print(datetime.datetime.now(), "rs: ", rs)
