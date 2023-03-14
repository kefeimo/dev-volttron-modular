import json
from volttron.client.vip.agent import Agent
from volttrontesting.server_mock import TestServer
from volttron.client.messaging.health import *

def _test_send_alert():
    """ Test that an agent can send an alert through the pubsub message bus."""

    # Create an agent to run the test with
    agent = Agent(identity='test-health')

    agent_platform_driver = Agent(identity="platform.driver")

    # Create the server and connect the agent with the server
    ts = TestServer()
    ts.connect_agent(agent=agent)

    # The health.send_alert should send a pubsub message through the message bus
    agent.vip.health.send_alert("my_alert", Status.build(STATUS_BAD, "no context"))

    # We know that there should only be a single message sent through the bus and
    # the specifications of the message to test against.
    messages = ts.get_published_messages()
    assert len(messages) == 1
    headers = messages[0].headers
    message = json.loads(messages[0].message)
    assert headers['alert_key'] == 'my_alert'
    assert message['context'] == 'no context'
    assert message['status'] == 'BAD'


if __name__ == '__main__':
    _test_send_alert()
