from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from cli.watch import _NidusEventHandler, _to_str

pytestmark = pytest.mark.small

MEDIUM = pytest.mark.medium

SUPPORTED = frozenset({".md", ".txt", ".adoc", ".pdf", ".html", ".htm"})


def _make_event(src_path: str, is_directory: bool = False):
    event = MagicMock()
    event.src_path = src_path
    event.is_directory = is_directory
    return event


def _make_moved_event(src_path: str, dest_path: str, is_directory: bool = False):
    event = MagicMock()
    event.src_path = src_path
    event.dest_path = dest_path
    event.is_directory = is_directory
    return event


class TestToStr:
    def test_str_passthrough(self):
        assert _to_str("/path/to/file.md") == "/path/to/file.md"

    def test_bytes_decoded(self):
        assert _to_str(b"/path/to/file.md") == "/path/to/file.md"


class TestIsSupported:
    def test_supported_md(self):
        handler = _NidusEventHandler(SUPPORTED)
        assert handler._is_supported("/doc.md")

    def test_supported_pdf(self):
        handler = _NidusEventHandler(SUPPORTED)
        assert handler._is_supported("/doc.pdf")

    def test_supported_html(self):
        handler = _NidusEventHandler(SUPPORTED)
        assert handler._is_supported("/doc.html")

    def test_unsupported_extension(self):
        handler = _NidusEventHandler(SUPPORTED)
        assert not handler._is_supported("/doc.xyz")

    def test_case_insensitive(self):
        handler = _NidusEventHandler(SUPPORTED)
        assert handler._is_supported("/doc.MD")
        assert handler._is_supported("/doc.PDF")


class TestOnCreated:
    def test_calls_add_for_supported_file(self):
        handler = _NidusEventHandler(SUPPORTED)
        event = _make_event("/path/to/doc.md")
        with patch("cli.watch._add") as mock_add:
            handler.on_created(event)
        mock_add.assert_called_once_with([Path("/path/to/doc.md")])

    def test_ignores_directory_event(self):
        handler = _NidusEventHandler(SUPPORTED)
        event = _make_event("/path/to/dir", is_directory=True)
        with patch("cli.watch._add") as mock_add:
            handler.on_created(event)
        mock_add.assert_not_called()

    def test_ignores_unsupported_extension(self):
        handler = _NidusEventHandler(SUPPORTED)
        event = _make_event("/path/to/file.xyz")
        with patch("cli.watch._add") as mock_add:
            handler.on_created(event)
        mock_add.assert_not_called()


class TestOnModified:
    def test_calls_add_for_supported_file(self):
        handler = _NidusEventHandler(SUPPORTED)
        event = _make_event("/path/to/doc.txt")
        with patch("cli.watch._add") as mock_add:
            handler.on_modified(event)
        mock_add.assert_called_once_with([Path("/path/to/doc.txt")])

    def test_ignores_directory_event(self):
        handler = _NidusEventHandler(SUPPORTED)
        event = _make_event("/path/to/dir/", is_directory=True)
        with patch("cli.watch._add") as mock_add:
            handler.on_modified(event)
        mock_add.assert_not_called()

    def test_ignores_unsupported_extension(self):
        handler = _NidusEventHandler(SUPPORTED)
        event = _make_event("/path/to/file.log")
        with patch("cli.watch._add") as mock_add:
            handler.on_modified(event)
        mock_add.assert_not_called()


class TestOnDeleted:
    def test_calls_delete_for_supported_file(self):
        handler = _NidusEventHandler(SUPPORTED)
        event = _make_event("/path/to/doc.md")
        with patch("cli.watch._delete") as mock_delete:
            handler.on_deleted(event)
        mock_delete.assert_called_once_with([Path("/path/to/doc.md")])

    def test_ignores_directory_event(self):
        handler = _NidusEventHandler(SUPPORTED)
        event = _make_event("/path/to/dir", is_directory=True)
        with patch("cli.watch._delete") as mock_delete:
            handler.on_deleted(event)
        mock_delete.assert_not_called()

    def test_ignores_unsupported_extension(self):
        handler = _NidusEventHandler(SUPPORTED)
        event = _make_event("/path/to/file.xyz")
        with patch("cli.watch._delete") as mock_delete:
            handler.on_deleted(event)
        mock_delete.assert_not_called()


class TestOnMoved:
    def test_both_supported_deletes_old_and_adds_new(self):
        handler = _NidusEventHandler(SUPPORTED)
        event = _make_moved_event("/old/doc.md", "/new/doc.md")
        with patch("cli.watch._delete") as mock_delete, patch("cli.watch._add") as mock_add:
            handler.on_moved(event)
        mock_delete.assert_called_once_with([Path("/old/doc.md")])
        mock_add.assert_called_once_with([Path("/new/doc.md")])

    def test_unsupported_src_only_adds_new(self):
        handler = _NidusEventHandler(SUPPORTED)
        event = _make_moved_event("/old/doc.xyz", "/new/doc.md")
        with patch("cli.watch._delete") as mock_delete, patch("cli.watch._add") as mock_add:
            handler.on_moved(event)
        mock_delete.assert_not_called()
        mock_add.assert_called_once_with([Path("/new/doc.md")])

    def test_unsupported_dest_only_deletes_old(self):
        handler = _NidusEventHandler(SUPPORTED)
        event = _make_moved_event("/old/doc.md", "/new/doc.xyz")
        with patch("cli.watch._delete") as mock_delete, patch("cli.watch._add") as mock_add:
            handler.on_moved(event)
        mock_delete.assert_called_once_with([Path("/old/doc.md")])
        mock_add.assert_not_called()

    def test_dir_move_nonexistent_dest_does_nothing(self):
        handler = _NidusEventHandler(SUPPORTED)
        event = _make_moved_event("/old/dir", "/new/dir", is_directory=True)
        with patch("cli.watch._delete") as mock_delete, patch("cli.watch._add") as mock_add:
            handler.on_moved(event)
        mock_delete.assert_not_called()
        mock_add.assert_not_called()


@MEDIUM
class TestOnMovedDirectory:
    def test_dir_move_deletes_old_and_adds_new(self, tmp_path: Path):
        src = tmp_path / "notes"
        dest = tmp_path / "archive"
        dest.mkdir()
        (dest / "a.md").write_text("hello")
        (dest / "b.txt").write_text("world")
        (dest / "skip.xyz").write_text("ignored")

        handler = _NidusEventHandler(SUPPORTED)
        event = _make_moved_event(str(src), str(dest), is_directory=True)
        with patch("cli.watch._delete") as mock_delete, patch("cli.watch._add") as mock_add:
            handler.on_moved(event)

        deleted = mock_delete.call_args[0][0]
        added = mock_add.call_args[0][0]
        assert set(deleted) == {src / "a.md", src / "b.txt"}
        assert set(added) == {dest / "a.md", dest / "b.txt"}

    def test_dir_move_empty_dest_does_nothing(self, tmp_path: Path):
        src = tmp_path / "notes"
        dest = tmp_path / "archive"
        dest.mkdir()

        handler = _NidusEventHandler(SUPPORTED)
        event = _make_moved_event(str(src), str(dest), is_directory=True)
        with patch("cli.watch._delete") as mock_delete, patch("cli.watch._add") as mock_add:
            handler.on_moved(event)
        mock_delete.assert_not_called()
        mock_add.assert_not_called()
