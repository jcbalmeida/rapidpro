import json
from http.server import BaseHTTPRequestHandler, HTTPServer
from threading import Thread

import requests

from django.utils import timezone

from temba.channels.models import Channel
from temba.msgs.models import Msg

COURIER_URL = "http://localhost:8080"


class MockChannelHandler(BaseHTTPRequestHandler):
    def do_POST(self):
        length = int(self.headers["content-length"])
        data = json.loads(self.rfile.read(length))

        print(data)


class MockChannelServer(HTTPServer):
    def __init__(self):
        HTTPServer.__init__(self, ("localhost", 49999), MockChannelHandler)

        self.base_url = "http://localhost:49999"
        self.thread = Thread(target=self.serve_forever)
        self.thread.setDaemon(True)
        self.thread.start()


class MockChannel:
    def __init__(self, db_channel, server):
        self.db_channel = db_channel
        self.server = server

    @classmethod
    def create(cls, org, user):
        server = MockChannelServer()

        config = {
            Channel.CONFIG_SEND_URL: f"{server.base_url}/send",
            Channel.CONFIG_SEND_METHOD: "POST",
            Channel.CONFIG_CONTENT_TYPE: "application/json",
        }
        return cls(Channel.add_config_external_channel(org, user, "EC", "123456", "EX", config, "SR", ["tel"]), server)

    def send(self, sender, text):
        response = requests.post(
            f"{COURIER_URL}/c/ex/{str(self.db_channel.uuid)}/receive",
            data={"from": sender, "text": text, "date": timezone.now().isoformat()},
        )

        assert response.status_code == 200, f"courier returned non-200 response: {response.content}"

        payload = response.json()

        assert payload["message"] == "Message Accepted", f"courier returned unexpected response: {response.content}"

        print(payload)

        return Msg.objects.get(uuid=payload["data"][0]["msg_uuid"])

    def release(self):
        self.db_channel.release()
        self.server.shutdown()
