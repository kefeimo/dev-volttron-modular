from volttron.client.vip.agent import build_agent
from volttron.utils.commands import vip_main
from volttron.client.vip.agent import Agent, Core
from volttron.client.known_identities import CONFIGURATION_STORE, PLATFORM_DRIVER
from volttron.utils import jsonapi

class TestAgent(Agent):
    def __init__(self, config_path, **kwargs):
        super().__init__(**kwargs)
        self.config_path = config_path


# def main():
#     """Main method called during startup of agent.
#     :return:"""
#     try:
#         a = vip_main(TestAgent, version=0.1)
#     except Exception as e:
#         print(f"unhandled exception {e}")
#     print()
#
#     # agent = ExampleAgent('example')
#     # print('1 ===========================')
#     # greenlet = gevent.spawn(agent.core.run)

def main():
    pass
    print(CONFIGURATION_STORE)
    a = build_agent()
    print(a)

    peer = "platform_driver"

    # get_point example
    peer_method = "get_point"
    # rs = a.vip.rpc.call(peer, peer_method, "campus-vm/building-vm/dnp3", "AnalogInput_index0").get(timeout=10)
    # ref: https://volttron.readthedocs.io/en/main/platform-features/message-bus/vip/vip-json-rpc.html?highlight=manage_store#vctl-rpc-commands

    rs = a.vip.rpc.call(CONFIGURATION_STORE,
                 "manage_list_configs",
                    "platform_driver"
                 ).get(10)
    print(f"========== rs {rs}")

    rs = a.vip.rpc.call(CONFIGURATION_STORE,
                        "manage_list_stores",
                        ).get(10)
    print(f"========== rs {rs}")


    rs = a.vip.peerlist.list().get(10)
    print(f"========== rs {rs}")

    rs = a.vip.rpc.call(CONFIGURATION_STORE,
                                    "manage_list_configs",
                                    "platform_driver"
                                    ).get(10)
    print(f"========== rs {rs}")


if __name__ == "__main__":
    main()
