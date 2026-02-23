from common.os_utils import flatten_path_to_file
import pytest


@pytest.fixture
def temp_dir_structure(tmp_path):
    """
    テスト用のディレクトリ構造を作成:
    /root
      /subdir
        file_a.txt
        file_b.log
      /exclude_me
        file_c.txt
      file_d.py
      temp_file.tmp
    """
    root = tmp_path / "root"
    root.mkdir()

    subdir = root / "subdir"
    subdir.mkdir()
    (subdir / "file_a.txt").write_text("a")
    (subdir / "file_b.log").write_text("b")

    exclude_dir = root / "exclude_me"
    exclude_dir.mkdir()
    (exclude_dir / "file_c.txt").write_text("c")

    (root / "file_d.py").write_text("d")
    (root / "temp_file.tmp").write_text("temp")

    return root


def test_flatten_all_files(temp_dir_structure):
    """除外設定なしですべてのファイルが取得できるか"""
    files = list(flatten_path_to_file(temp_dir_structure))
    assert len(files) == 5
    assert any(f.name == "file_a.txt" for f in files)
    assert any(f.name == "file_d.py" for f in files)


def test_exclude_by_extension(temp_dir_structure):
    """拡張子による除外（*.tmp）が機能するか"""
    files = list(flatten_path_to_file(temp_dir_structure, exclude_patterns="*.tmp"))

    assert len(files) == 4
    assert not any(f.suffix == ".tmp" for f in files)


def test_exclude_directory(temp_dir_structure):
    """ディレクトリ名による除外が機能し、その中身も走査されないか"""
    files = list(
        flatten_path_to_file(temp_dir_structure, exclude_patterns="exclude_me")
    )

    assert len(files) == 4
    assert not any(f.name == "file_c.txt" for f in files)


def test_multiple_excludes(temp_dir_structure):
    """複数の除外パターンが機能するか"""
    excludes = ["*.log", "*.tmp", "exclude_me"]
    files = list(flatten_path_to_file(temp_dir_structure, exclude_patterns=excludes))

    # 残るべきは file_a.txt と file_d.py のみ
    assert len(files) == 2
    names = {f.name for f in files}
    assert names == {"file_a.txt", "file_d.py"}


def test_single_file_input(temp_dir_structure):
    """ディレクトリではなく単一ファイルを渡した場合の挙動"""
    target_file = temp_dir_structure / "file_d.py"
    files = list(flatten_path_to_file(target_file))

    assert len(files) == 1
    assert files[0].name == "file_d.py"


def test_non_existent_path():
    """存在しないパスを渡してもエラーにならず空を返すか"""
    files = list(flatten_path_to_file("non_existent_path_12345"))
    assert len(files) == 0
