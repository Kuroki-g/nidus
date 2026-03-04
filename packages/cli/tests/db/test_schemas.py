import pytest

pytestmark = pytest.mark.small


class TestGetFileHash:
    def test_returns_hex_string(self, tmp_path):
        from cli.db.schemas import get_file_hash

        f = tmp_path / "a.txt"
        f.write_bytes(b"hello")
        result = get_file_hash(f)
        assert isinstance(result, str)
        assert len(result) == 64  # SHA-256 is 64 hex chars

    def test_same_content_same_hash(self, tmp_path):
        from cli.db.schemas import get_file_hash

        f1 = tmp_path / "a.txt"
        f2 = tmp_path / "b.txt"
        f1.write_bytes(b"content")
        f2.write_bytes(b"content")
        assert get_file_hash(f1) == get_file_hash(f2)

    def test_different_content_different_hash(self, tmp_path):
        from cli.db.schemas import get_file_hash

        f1 = tmp_path / "a.txt"
        f2 = tmp_path / "b.txt"
        f1.write_bytes(b"aaa")
        f2.write_bytes(b"bbb")
        assert get_file_hash(f1) != get_file_hash(f2)

    def test_empty_file(self, tmp_path):
        from cli.db.schemas import get_file_hash

        f = tmp_path / "empty.txt"
        f.write_bytes(b"")
        result = get_file_hash(f)
        assert isinstance(result, str)
        assert len(result) == 64

    def test_large_file_chunked(self, tmp_path):
        """4096バイトを超えるファイルも正しくハッシュできる。"""
        from cli.db.schemas import get_file_hash

        f = tmp_path / "large.txt"
        f.write_bytes(b"x" * 10000)
        result = get_file_hash(f)
        assert len(result) == 64
