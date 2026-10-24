import threading
import time
import unittest
from concurrent.futures import ThreadPoolExecutor
from types import SimpleNamespace
from unittest.mock import patch
import numpy as np
from core.camera_stream import CameraStreamWorker


class JpegCacheTests(unittest.TestCase):
    def test_viewers_share_encoding_but_quality_and_raw_are_separate(self):
        worker = SimpleNamespace(_jpeg_lock=threading.Lock(),
            _latest_bgr_frame=np.zeros((10,10,3),dtype=np.uint8),
            _latest_raw_bgr_frame=np.ones((10,10,3),dtype=np.uint8),
            _latest_jpeg_cache=None, _latest_raw_jpeg_cache=None,
            _latest_jpeg_quality=None, _latest_raw_jpeg_quality=None,
            _latest_jpeg_time=0, _latest_raw_jpeg_time=0)
        def encode(extension, frame, options):
            time.sleep(0.01)
            return True,np.array([int(frame[0,0,0]),options[-1]],dtype=np.uint8)
        def get(quality=65,raw=False):
            return CameraStreamWorker.get_latest_jpeg(worker,quality,raw)
        with patch('core.camera_stream.cv2.imencode', side_effect=encode) as encoder, \
             patch('core.camera_stream.time.monotonic', return_value=10):
            with ThreadPoolExecutor(max_workers=8) as pool:
                self.assertEqual(list(pool.map(lambda _:get(), range(8))),[bytes([0,65])]*8)
            self.assertEqual(encoder.call_count,1)
            self.assertEqual(get(90),bytes([0,90]))
            self.assertEqual(get(90,True),bytes([1,90]))
            self.assertEqual(encoder.call_count,3)


if __name__ == '__main__':
    unittest.main()
