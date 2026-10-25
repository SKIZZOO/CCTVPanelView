import base64
import hashlib
import socketserver
import struct
import threading
import unittest
from unittest.mock import patch, MagicMock
import numpy as np
from PyQt6.QtWidgets import QApplication
from core.rtsp_audio import RTSPBackchannel, AudioProtocolError, select_audio_track, REQUIRE
from core.audio_talk_controller import AudioTalkController, AudioConverter, encode_g711
from ui.components.intercom_pad import IntercomPad


class AudioTests(unittest.TestCase):
    def test_g711_silence_and_positive_samples_match_standard_codes(self):
        pcm = struct.pack("<hhh", 0, 1000, -1000)
        self.assertEqual(encode_g711(pcm, "PCMA"), bytes([0xD5, 0xFA, 0x7A]))
        self.assertEqual(encode_g711(pcm, "PCMU"), bytes([0xFF, 0xCE, 0x4E]))

    def test_stereo_native_microphone_is_resampled_continuously(self):
        converter = AudioConverter(48000, 2, "Float")
        wave = (.25 * np.sin(np.arange(48000) * 2 * np.pi * 440 / 48000)).astype("<f4")
        stereo = np.column_stack((wave, wave)).astype("<f4").tobytes()
        pieces = [converter.convert(stereo[i:i + 777]) for i in range(0, len(stereo), 777)]
        result = np.frombuffer(b"".join(pieces), "<i2")
        self.assertEqual(len(result), 8000)
        self.assertLess(len(converter.buffer), 10)
        self.assertGreater(np.max(result), 7000)

    def test_incoming_audio_track_is_never_guessed_as_speaker_output(self):
        sdp = "m=audio 0 RTP/AVP 8\r\na=control:trackID=1\r\na=recvonly\r\n"
        with self.assertRaises(AudioProtocolError):
            select_audio_track(sdp, "rtsp://localhost/camera/")

    def test_dynamic_mulaw_backchannel_and_control_uri_are_selected(self):
        sdp = "m=audio 0 RTP/AVP 96\r\na=rtpmap:96 PCMU/8000\r\na=control:talk\r\na=sendonly\r\n"
        self.assertEqual(select_audio_track(sdp, "rtsp://localhost/camera/"),
                         ("rtsp://localhost/camera/talk", 96, "PCMU"))

    def test_digest_qop_response_is_recomputed_for_method_and_uri(self):
        connection = RTSPBackchannel("rtsp://localhost:8554/camera", "user", "password")
        connection.challenge = 'Digest realm="camera", nonce="nonce", qop="auth,auth-int", algorithm=MD5'
        with patch("core.rtsp_audio.secrets.token_hex", return_value="cnonce"):
            header = connection._authorization("SETUP", "rtsp://localhost:8554/audio")
        md5 = lambda value: hashlib.md5(value.encode()).hexdigest()
        expected = md5(md5("user:camera:password") + ":nonce:00000001:cnonce:auth:" + md5("SETUP:rtsp://localhost:8554/audio"))
        self.assertIn(f'response="{expected}"', header)
        self.assertIn("qop=auth", header)

    def test_fragmented_basic_auth_handshake_uses_negotiated_track_play_and_channel(self):
        requests = []
        errors = []
        class Handler(socketserver.StreamRequestHandler):
            def handle(self):
                try:
                    while True:
                        first = self.rfile.readline()
                        if not first:
                            return
                        method, uri, _ = first.decode().strip().split(" ", 2)
                        headers = {}
                        while True:
                            line = self.rfile.readline()
                            if line in (b"\r\n", b""):
                                break
                            k, v = line.decode().split(":", 1)
                            headers[k.lower()] = v.strip()
                        requests.append((method, uri, headers))
                        if headers.get("authorization") != "Basic " + base64.b64encode(b"user:pass").decode():
                            response = b'RTSP/1.0 401 Unauthorized\r\nWWW-Authenticate: Basic realm="camera"\r\nContent-Length: 0\r\n\r\n'
                        elif method == "DESCRIBE":
                            body = b"v=0\r\nm=audio 0 RTP/AVP 96\r\na=rtpmap:96 PCMU/8000\r\na=control:talk\r\na=sendonly\r\n"
                            base = f"rtsp://127.0.0.1:{self.server.server_address[1]}/session/"
                            response = f"RTSP/1.0 200 OK\r\nContent-Base: {base}\r\nContent-Length: {len(body)}\r\n\r\n".encode() + body
                        elif method == "SETUP":
                            response = b"RTSP/1.0 200 OK\r\nSession: test-session;timeout=60\r\nTransport: RTP/AVP/TCP;unicast;interleaved=4-5\r\nContent-Length: 0\r\n\r\n"
                        else:
                            response = b"RTSP/1.0 200 OK\r\nContent-Length: 0\r\n\r\n"
                        for index in range(0, len(response), 13):
                            self.wfile.write(response[index:index + 13]); self.wfile.flush()
                        if method == "TEARDOWN":
                            return
                except OSError:
                    pass
                except Exception as error:
                    errors.append(str(error))
        server = socketserver.ThreadingTCPServer(("127.0.0.1", 0), Handler)
        server.daemon_threads = True
        serving = threading.Thread(target=server.serve_forever, daemon=True); serving.start()
        connection = RTSPBackchannel(f"rtsp://127.0.0.1:{server.server_address[1]}/stream", "user", "pass")
        try:
            connection.connect()
            self.assertEqual((connection.codec, connection.payload, connection.channel), ("PCMU", 96, 4))
            self.assertEqual([item[0] for item in requests], ["DESCRIBE", "DESCRIBE", "SETUP", "PLAY"])
            self.assertTrue(requests[2][1].endswith("/session/talk"))
            self.assertTrue(all(item[2]["require"] == REQUIRE for item in requests))
            self.assertNotIn("mode=record", requests[2][2]["transport"])
            self.assertFalse(errors)
        finally:
            connection.close(); server.shutdown(); server.server_close()


class IntercomStateTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls): cls.app = QApplication.instance() or QApplication([])

    def test_stopping_during_connect_cannot_start_microphone_later(self):
        controller = AudioTalkController()
        controller._generation = 5
        controller.is_connecting = True
        controller.stop_broadcast()
        with patch("core.audio_talk_controller.QAudioSource") as source:
            controller._begin_capture(MagicMock(), 5)
            source.assert_not_called()
        self.assertFalse(controller.is_broadcasting)
        controller.shutdown()

    def test_camera_change_and_panel_close_stop_pending_or_active_talk(self):
        panel = IntercomPad(settings={})
        cameras = [{"name": "Camera", "ip": "form-host", "streams": [
            {"id": "one", "url": "rtsp://user:pass@127.0.0.1:8554/custom?profile=2"}]}]
        panel.populate_cameras(cameras)
        data = panel.combo_camera.itemData(0)
        self.assertEqual(data["rtsp_port"], 8554)
        self.assertEqual(data["stream_path"], "/custom?profile=2")
        with patch.object(panel.talk_controller, "stop_broadcast") as stop:
            panel._on_camera_dropdown_changed(0)
            stop.assert_called_once()
        panel.talk_controller.shutdown()
        panel.deleteLater()


if __name__ == "__main__": unittest.main()
