import json
from http.server import BaseHTTPRequestHandler, HTTPServer
from threading import Thread

import pytz
import requests

from django.conf import settings
from django.contrib.auth.models import User
from django.core.management import BaseCommand, CommandError
from django.utils import timezone

from temba.archives.models import Archive
from temba.channels.models import Channel
from temba.msgs.models import Msg
from temba.orgs.models import Org

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

    def start(self):
        """
        Starts running mock server in a daemon thread which will automatically shut down when the main process exits
        """
        t = Thread(target=self.serve_forever)
        t.setDaemon(True)
        t.start()


class Command(BaseCommand):
    help = "Runs a simple integration test on an empty database"

    def handle(self, *args, **kwargs):
        try:
            has_data = Org.objects.exists()
        except Exception:  # pragma: no cover
            raise CommandError("Run migrate command first to create database tables")
        if has_data:
            raise CommandError("Can't run test in non-empty database.")

        channel_server = MockChannelServer()
        channel_server.start()

        self._log("Creating test org...\n")

        admin = User.objects.create_user("admin", "admin@nyaruka.com", password="Qwerty123")
        org = self._create_org(admin)
        channel = self._create_channel(org, admin)

        self._create_msg_in(channel, "+593979099111", "Hi there")

        self._log("Releasing test org...\n")

        self._cleanup(org)

    def _create_org(self, admin):
        org = Org.objects.create(
            name="Integration Test",
            timezone=pytz.timezone("America/Bogota"),
            brand=settings.DEFAULT_BRAND,
            created_by=admin,
            modified_by=admin,
        )
        org.administrators.add(admin)
        org.initialize(topup_size=1000)
        return org

    def _create_channel(self, org, user):
        config = {
            Channel.CONFIG_SEND_URL: "http://localhost:49999/send",
            Channel.CONFIG_SEND_METHOD: "POST",
            Channel.CONFIG_CONTENT_TYPE: "application/json",
        }
        return Channel.add_config_external_channel(org, user, "EC", "123456", "EX", config, "SR", ["tel"])

    def _cleanup(self, org):
        users = org.get_org_users()

        # monkey patch remote archive releasing so it's a noop
        Archive.release_org_archives = lambda o: []

        org.release(immediately=True)

        assert Org.objects.count() == 0, "test org wasn't deleted"

        for user in users:
            user.release(brand=settings.DEFAULT_BRAND)
            user.delete()

        assert User.objects.filter(id__in=[u.id for u in users]).count() == 0, "test users weren't deleted"

    def _create_msg_in(self, channel, sender, text):
        response = requests.post(
            f"{COURIER_URL}/c/ex/{str(channel.uuid)}/receive",
            data={"from": sender, "text": text, "date": timezone.now().isoformat()},
        )

        assert response.status_code == 200, f"courier returned non-200 response: {response.content}"

        payload = response.json()

        assert payload["message"] == "Message Accepted", f"courier returned unexpected response: {response.content}"

        print(payload)

        return Msg.objects.get(uuid=payload["data"][0]["msg_uuid"])

    def _log(self, text):
        self.stdout.write(text, ending="")
        self.stdout.flush()
