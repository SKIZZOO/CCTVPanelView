import tempfile
import unittest
from pathlib import Path
from unittest.mock import mock_open, patch
from core.drive_folder import resolve_drive_folder_url, stage_drive_recording

LINK = "https://drive.google.com/drive/folders/cloud_folder_fixture123"


class LocalDriveFolderTests(unittest.TestCase):
    def test_resolves_real_id_but_rejects_missing_temporary_and_malformed_metadata(self):
        with tempfile.TemporaryDirectory() as temp:
            with patch("builtins.open", mock_open(read_data=b"cloud_folder_fixture123\n")) as read:
                self.assertEqual(resolve_drive_folder_url(temp), LINK)
                self.assertTrue(read.call_args.args[0].endswith(":user.drive.id"))
            for value in (b"local-12345", b"", b"x/../../wrong", b"x" * 513):
                with patch("builtins.open", mock_open(read_data=value)):
                    with self.assertRaises(ValueError): resolve_drive_folder_url(temp)
            with patch("builtins.open", side_effect=FileNotFoundError()):
                with self.assertRaises(ValueError): resolve_drive_folder_url(temp)

    def test_100_mb_copy_is_bounded_keeps_original_and_never_copies_twice_inside_folder(self):
        import shutil
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp); target = root / "drive"; target.mkdir()
            source = root / "full-recording.mp4"
            with source.open("wb") as stream: stream.truncate(100_000_000)
            with patch("core.drive_folder.resolve_drive_folder_url", return_value=LINK), \
                 patch("core.drive_folder.shutil.copyfileobj", wraps=shutil.copyfileobj) as copy:
                link, name = stage_drive_recording(source, target)
                self.assertEqual(link, LINK)
                self.assertEqual(copy.call_args.kwargs["length"], 1024 * 1024)
                self.assertEqual(source.stat().st_size, 100_000_000)
                self.assertEqual((target / name).stat().st_size, 100_000_000)
                copy.reset_mock()
                self.assertEqual(stage_drive_recording(target / name, target), (LINK, name))
                copy.assert_not_called()
            self.assertEqual(len(list(target.iterdir())), 1)

    def test_failed_copy_removes_temporary_file_and_preserves_original(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp); target = root / "drive"; target.mkdir()
            source = root / "recording.mp4"; source.write_bytes(b"original")
            with patch("core.drive_folder.resolve_drive_folder_url", return_value=LINK), \
                 patch("core.drive_folder.shutil.copyfileobj", side_effect=OSError("disk full")):
                with self.assertRaises(OSError): stage_drive_recording(source, target)
            self.assertEqual(source.read_bytes(), b"original")
            self.assertEqual(list(target.iterdir()), [])
