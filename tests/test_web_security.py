"""Local HTTP regression tests. No cameras or external network required."""
import http.client
import json
import threading
import unittest
import tempfile
import os
from pathlib import Path
from types import SimpleNamespace
from urllib.parse import urlsplit, parse_qs

from core.web_server import WebStreamingServer
from core.async_recorder import AsyncVideoRecorder


class WebSecurityTests(unittest.TestCase):
    def setUp(self):
        self.main = SimpleNamespace(active_workers={})
        self.server = WebStreamingServer(self.main, port=0)
        self.assertTrue(self.server.start())
        self.cookie = "cctv_session=" + self.server.access_token

    def tearDown(self):
        self.server.stop()

    def request(self, method, path, data=None, authorized=False, headers=None):
        connection = http.client.HTTPConnection("127.0.0.1", self.server.port, timeout=3)
        request_headers = dict(headers or {})
        if authorized:
            request_headers["Cookie"] = self.cookie
        if data is not None:
            request_headers.setdefault("Content-Type", "application/json")
            data = json.dumps(data)
        connection.request(method, path, body=data, headers=request_headers)
        response = connection.getresponse()
        result = response.status, dict(response.getheaders()), response.read()
        connection.close()
        return result

    def test_private_routes_require_authentication(self):
        for route in ("/api/cameras", "/api/status", "/api/alerts", "/api/recordings", "/qr",
                      "/snapshot/cam", "/stream/cam", "/api/alert_image/id", "/api/alert_video/id",
                      "/api/recording_file?file=test.mp4"):
            with self.subTest(route=route):
                self.assertEqual(self.request("GET", route)[0], 401)
        self.assertEqual(self.request("POST", "/api/clear_alerts", {})[0], 401)
        self.assertEqual(self.request("GET", "/api/cameras", authorized=True)[0], 200)

    def test_login_and_cookie_flags(self):
        self.assertEqual(self.request("POST", "/api/session", {"token": "bad"})[0], 401)
        self.assertEqual(self.request("POST", "/api/session", {"token": "\u2603"})[0], 401)
        status, headers, _ = self.request("POST", "/api/session", {"token": self.server.access_token})
        self.assertEqual(status, 200)
        self.assertIn("HttpOnly", headers["Set-Cookie"])
        self.assertIn("SameSite=Strict", headers["Set-Cookie"])
        self.assertIn("no-store", headers["Cache-Control"])

    def test_code_is_in_fragment_and_rotates_on_restart(self):
        url = urlsplit(self.server.get_local_url())
        self.assertEqual(url.query, "")
        self.assertEqual(parse_qs(url.fragment)["access"], [self.server.access_token])
        self.server.stop()
        self.assertTrue(self.server.start())
        self.assertEqual(self.request("GET", "/api/cameras", authorized=True)[0], 401)

    def test_cross_origin_and_non_json_commands_rejected(self):
        self.assertEqual(self.request("POST", "/api/clear_alerts", {}, True,
                                     {"Origin": "https://attacker.invalid"})[0], 403)
        self.assertEqual(self.request("POST", "/api/clear_alerts", None, True,
                                     {"Content-Type": "application/x-www-form-urlencoded"})[0], 415)

    def test_get_cannot_mutate_and_delete_is_desktop_only(self):
        for path in ("/api/clear_alerts", "/api/record?id=cam&action=start"):
            self.assertEqual(self.request("GET", path, authorized=True)[0], 405)
        self.assertEqual(self.request("POST", "/api/delete_camera", {"id": "cam"}, True)[0], 403)

    def test_malformed_and_large_body(self):
        self.assertEqual(self.request("POST", "/api/session", [], False)[0], 400)
        self.assertEqual(self.request("POST", "/api/session", {}, False, {"Content-Length": "-1"})[0], 413)
        self.assertEqual(self.request("POST", "/api/session", {"token": "x" * 17000})[0], 413)
        self.assertEqual(self.request("POST", "/api/record", {"id": [], "action": 1}, True)[0], 400)

    def test_hostile_numeric_inputs(self):
        for value in ("bad", "NaN", "Infinity", "-1", "1000000000000000000000000"):
            self.assertEqual(self.request("GET", "/api/alerts?limit=" + value, authorized=True)[0], 200)
        self.assertEqual(self.server.total_clients, 0)

    def test_client_tracking_preserves_active_flag_until_last_viewer(self):
        worker = SimpleNamespace(set_web_streaming_active=lambda active: setattr(self.main, "viewing", active))
        self.main.active_workers["cam"] = worker
        self.server.increment_client_count("cam")
        self.server.increment_client_count("cam")
        self.server.decrement_client_count("cam")
        self.assertTrue(self.main.viewing)
        self.server.decrement_client_count("cam")
        self.assertFalse(self.main.viewing)
        self.assertEqual(self.server.total_clients, 0)

    def test_connection_limit_and_timeout(self):
        httpd = self.server.httpd
        for _ in range(32):
            self.assertTrue(httpd._slots.acquire(blocking=False))
        try:
            self.assertEqual(self.request("GET", "/")[0], 503)
        finally:
            for _ in range(32):
                httpd._slots.release()
        self.assertEqual(self.request("GET", "/")[0], 200)

    def test_recording_queue_memory_budget(self):
        for width, height in ((1920, 1080), (3840, 2160), (640, 360)):
            recorder = AsyncVideoRecorder("unused.mp4", width=width, height=height)
            self.assertLessEqual(recorder._queue.maxsize * width * height * 3, 32 * 1024 * 1024)

    def test_video_ranges_and_path_confinement(self):
        previous = os.getcwd()
        with tempfile.TemporaryDirectory() as folder:
            try:
                os.chdir(folder)
                Path('recordings').mkdir()
                Path('recordings/clip.mp4').write_bytes(b'0123456789')
                for value, status, body in [('bytes=2-5',206,b'2345'), ('bytes=-3',206,b'789'),
                                            ('bytes=8-',206,b'89'), ('bytes=50-',416,b''),
                                            ('bytes=3-1',416,b''), ('bytes=-0',416,b'')]:
                    with self.subTest(value=value):
                        result = self.request('GET','/api/recording_file?file=clip.mp4',authorized=True,
                                              headers={'Range':value})
                        self.assertEqual(result[0], status)
                        self.assertEqual(result[2], body)
                for filename in ('C:secret.mp4', '../secret.mp4', 'clip.mp4:secret', 'cameras_config.json'):
                    self.assertEqual(self.request('GET','/api/recording_file?file='+filename,authorized=True)[0],400)
                status, headers, body = self.request('GET','/api/recording_file?file=clip.mp4',authorized=True)
                self.assertEqual(status,200)
                self.assertEqual(body,b'0123456789')
                self.assertEqual(headers['Cache-Control'],'private, no-store')
            finally:
                os.chdir(previous)


if __name__ == "__main__":
    unittest.main()
