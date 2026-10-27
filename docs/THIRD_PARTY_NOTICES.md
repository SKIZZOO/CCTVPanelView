# Third-party components in Windows builds

Application source is MIT licensed; dependencies retain their own licenses.

- Python: https://www.python.org/psf/license/
- PyQt6: https://www.riverbankcomputing.com/software/pyqt/ (GPLv3 distribution)
- Qt: https://www.qt.io/licensing/ and https://download.qt.io/archive/qt/
- OpenCV: https://opencv.org/license/
- NumPy: https://numpy.org/doc/stable/license.html
- Pillow: https://github.com/python-pillow/Pillow/blob/main/LICENSE
- psutil: https://github.com/giampaolo/psutil/blob/master/LICENSE
- qrcode: https://github.com/lincolnloop/python-qrcode/blob/main/LICENSE
- PyInstaller bootloader exception: https://pyinstaller.org/en/stable/license.html

FFmpeg, FFplay and FFprobe 9.0.2 are Gyan's standalone Windows essentials build, run as separate processes. The included GPLv3 license and complete build configuration are in `assets/third_party/ffmpeg/`. Build provider: https://www.gyan.dev/ffmpeg/builds/. Corresponding FFmpeg source revision: https://github.com/FFmpeg/FFmpeg/commit/946fcce07b. Release source: https://ffmpeg.org/releases/ffmpeg-9.0.2.tar.xz. External library names and their versions/source repositories are listed in the included build README. These notices also remain available in the release source archive.

## certifi CA bundle

The packaged application includes certifi (Mozilla public CA roots), distributed under MPL-2.0. The license is included at `assets/licenses/certifi-LICENSE.txt`. Upstream source and bundle updates: https://github.com/certifi/python-certifi . The CA bundle is not modified.
