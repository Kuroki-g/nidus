from pathlib import Path
from unittest.mock import MagicMock, patch

import numpy as np
import pytest

import cli.processor.file_processor as fp
from cli.processor.file_processor import (
    CHUNK_STRATEGIES,
    _flush_batch,
    data_generator,
    data_generator_multiprocessing,
    get_chunks,
    get_embedding,
)

# ---------------------------------------------------------------------------
# get_chunks — small tests (no I/O)
# ---------------------------------------------------------------------------


class TestGetChunks:
    @pytest.mark.small
    def test_returns_none_for_non_file(self, tmp_path):
        # ディレクトリを渡すと None
        assert get_chunks(tmp_path) is None

    @pytest.mark.small
    def test_returns_none_for_nonexistent_file(self, tmp_path):
        assert get_chunks(tmp_path / "ghost.md") is None

    @pytest.mark.small
    def test_returns_none_for_unsupported_extension(self, tmp_path):
        f = tmp_path / "file.xyz"
        f.write_text("content")
        result = get_chunks(f)
        assert result is None

    @pytest.mark.small
    def test_calls_correct_strategy_for_md(self, tmp_path):
        f = tmp_path / "test.md"
        f.write_text("# Hello\n\nworld")
        with patch("cli.processor.file_processor.chunk_markdown", return_value=["chunk1"]) as mock:
            result = get_chunks(f)
        mock.assert_called_once_with(f)
        assert result == ["chunk1"]

    @pytest.mark.small
    def test_calls_correct_strategy_for_pdf(self, tmp_path):
        f = tmp_path / "test.pdf"
        f.write_bytes(b"%PDF-1.4")
        with patch("cli.processor.file_processor.chunk_pdf", return_value=["pdf_chunk"]) as mock:
            result = get_chunks(f)
        mock.assert_called_once_with(f)
        assert result == ["pdf_chunk"]

    @pytest.mark.small
    def test_calls_correct_strategy_for_html(self, tmp_path):
        f = tmp_path / "test.html"
        f.write_text("<html></html>")
        with patch("cli.processor.file_processor.chunk_html", return_value=["html_chunk"]) as mock:
            result = get_chunks(f)
        mock.assert_called_once_with(f)
        assert result == ["html_chunk"]

    @pytest.mark.small
    def test_calls_correct_strategy_for_htm(self, tmp_path):
        f = tmp_path / "test.htm"
        f.write_text("<html></html>")
        with patch("cli.processor.file_processor.chunk_html", return_value=["htm_chunk"]) as mock:
            result = get_chunks(f)
        mock.assert_called_once_with(f)
        assert result == ["htm_chunk"]

    @pytest.mark.small
    def test_calls_correct_strategy_for_txt(self, tmp_path):
        f = tmp_path / "test.txt"
        f.write_text("plain text")
        with patch("cli.processor.file_processor.chunk_plain_text", return_value=["txt_chunk"]) as mock:
            result = get_chunks(f)
        mock.assert_called_once_with(f)
        assert result == ["txt_chunk"]

    @pytest.mark.small
    def test_calls_correct_strategy_for_adoc(self, tmp_path):
        f = tmp_path / "test.adoc"
        f.write_text("= Title")
        with patch("cli.processor.file_processor.chunk_asciidoc", return_value=["adoc_chunk"]) as mock:
            result = get_chunks(f)
        mock.assert_called_once_with(f)
        assert result == ["adoc_chunk"]

    @pytest.mark.small
    def test_calls_correct_strategy_for_docx(self, tmp_path):
        f = tmp_path / "test.docx"
        f.write_bytes(b"PK\x03\x04")
        with patch("cli.processor.file_processor.chunk_docx", return_value=["docx_chunk"]) as mock:
            result = get_chunks(f)
        mock.assert_called_once_with(f)
        assert result == ["docx_chunk"]

    @pytest.mark.small
    def test_calls_correct_strategy_for_csv(self, tmp_path):
        f = tmp_path / "test.csv"
        f.write_text("a,b\n1,2")
        with patch("cli.processor.file_processor.chunk_csv", return_value=["csv_chunk"]) as mock:
            result = get_chunks(f)
        mock.assert_called_once_with(f)
        assert result == ["csv_chunk"]

    @pytest.mark.small
    def test_calls_correct_strategy_for_tsv(self, tmp_path):
        f = tmp_path / "test.tsv"
        f.write_text("a\tb\n1\t2")
        with patch("cli.processor.file_processor.chunk_tsv", return_value=["tsv_chunk"]) as mock:
            result = get_chunks(f)
        mock.assert_called_once_with(f)
        assert result == ["tsv_chunk"]

    @pytest.mark.small
    def test_extension_matching_is_case_insensitive(self, tmp_path):
        f = tmp_path / "test.MD"
        f.write_text("# Hello")
        with patch("cli.processor.file_processor.chunk_markdown", return_value=["chunk"]) as mock:
            result = get_chunks(f)
        mock.assert_called_once()
        assert result == ["chunk"]

    @pytest.mark.small
    def test_returns_none_on_strategy_exception(self, tmp_path):
        f = tmp_path / "bad.md"
        f.write_text("content")
        with patch("cli.processor.file_processor.chunk_markdown", side_effect=RuntimeError("parse error")):
            result = get_chunks(f)
        assert result is None


class TestChunkStrategiesKeys:
    @pytest.mark.small
    def test_all_expected_extensions_present(self):
        expected = {".md", ".adoc", ".txt", ".pdf", ".html", ".htm", ".docx", ".csv", ".tsv"}
        assert expected == set(CHUNK_STRATEGIES.keys())


# ---------------------------------------------------------------------------
# data_generator — medium tests (uses tmp_path, mocks embedding)
# ---------------------------------------------------------------------------


_FAKE_VECTOR = np.zeros(1024, dtype=np.float32)


class TestDataGenerator:
    @pytest.mark.medium
    def test_empty_path_list_yields_nothing(self):
        results = list(data_generator([]))
        assert results == []

    @pytest.mark.medium
    def test_single_file_single_chunk(self, tmp_path):
        f = tmp_path / "a.md"
        f.write_text("# Hello\n\nworld")

        with (
            patch("cli.processor.file_processor.get_chunks", return_value=["chunk0"]),
            patch("cli.processor.file_processor.get_embedding", return_value=_FAKE_VECTOR),
            patch("common.os_utils.flatten_path_to_file", return_value=[f]),
        ):
            batches = list(data_generator([f]))

        assert len(batches) == 1
        assert len(batches[0]) == 1
        rec = batches[0][0]
        assert rec["chunk_text"] == "chunk0"
        assert rec["chunk_id"] == 0
        assert rec["source"] == str(f.absolute())
        assert rec["doc_name"] == f.name

    @pytest.mark.medium
    def test_batch_splits_at_batch_size(self, tmp_path):
        f = tmp_path / "b.md"
        f.write_text("content")
        chunks = [f"chunk{i}" for i in range(5)]

        with (
            patch("cli.processor.file_processor.get_chunks", return_value=chunks),
            patch("cli.processor.file_processor.get_embedding", return_value=_FAKE_VECTOR),
            patch("common.os_utils.flatten_path_to_file", return_value=[f]),
        ):
            batches = list(data_generator([f], batch_size=3))

        assert len(batches) == 2
        assert len(batches[0]) == 3
        assert len(batches[1]) == 2

    @pytest.mark.medium
    def test_skips_file_with_no_chunks(self, tmp_path):
        f = tmp_path / "empty.md"
        f.write_text("")

        with (
            patch("cli.processor.file_processor.get_chunks", return_value=None),
            patch("common.os_utils.flatten_path_to_file", return_value=[f]),
        ):
            batches = list(data_generator([f]))

        assert batches == []

    @pytest.mark.medium
    def test_skips_file_with_empty_chunk_list(self, tmp_path):
        f = tmp_path / "empty2.md"
        f.write_text("")

        with (
            patch("cli.processor.file_processor.get_chunks", return_value=[]),
            patch("common.os_utils.flatten_path_to_file", return_value=[f]),
        ):
            batches = list(data_generator([f]))

        assert batches == []

    @pytest.mark.medium
    def test_skips_chunk_on_embedding_error(self, tmp_path):
        f = tmp_path / "err.md"
        f.write_text("content")

        with (
            patch("cli.processor.file_processor.get_chunks", return_value=["ok", "bad", "ok2"]),
            patch(
                "cli.processor.file_processor.get_embedding",
                side_effect=[_FAKE_VECTOR, RuntimeError("fail"), _FAKE_VECTOR],
            ),
            patch("common.os_utils.flatten_path_to_file", return_value=[f]),
        ):
            batches = list(data_generator([f]))

        # "bad" チャンクはスキップされ、残り2件が1バッチで返る
        records = [r for batch in batches for r in batch]
        assert len(records) == 2
        assert records[0]["chunk_text"] == "ok"
        assert records[1]["chunk_text"] == "ok2"

    @pytest.mark.medium
    def test_multiple_files(self, tmp_path):
        f1 = tmp_path / "f1.md"
        f2 = tmp_path / "f2.md"
        f1.write_text("a")
        f2.write_text("b")

        def fake_get_chunks(path):
            return [f"chunk_from_{path.name}"]

        with (
            patch("cli.processor.file_processor.get_chunks", side_effect=fake_get_chunks),
            patch("cli.processor.file_processor.get_embedding", return_value=_FAKE_VECTOR),
            patch("common.os_utils.flatten_path_to_file", side_effect=lambda p: [p]),
        ):
            batches = list(data_generator([f1, f2], batch_size=10))

        records = [r for batch in batches for r in batch]
        assert len(records) == 2
        texts = {r["chunk_text"] for r in records}
        assert texts == {"chunk_from_f1.md", "chunk_from_f2.md"}

    @pytest.mark.medium
    def test_directory_entries_are_skipped(self, tmp_path):
        # flatten_path_to_file がディレクトリを返した場合はスキップ
        subdir = tmp_path / "subdir"
        subdir.mkdir()

        with (
            patch("common.os_utils.flatten_path_to_file", return_value=[subdir]),
        ):
            batches = list(data_generator([subdir]))

        assert batches == []


# ---------------------------------------------------------------------------
# _get_model / get_embedding — small tests
# ---------------------------------------------------------------------------


class TestGetModel:
    @pytest.mark.small
    def test_caches_model_instance(self):
        # _model をリセットしてキャッシュ動作を確認
        original = fp._model
        try:
            fp._model = None
            mock_instance = MagicMock()
            with patch("cli.processor.file_processor.EmbeddingModelManager", return_value=mock_instance):
                m1 = fp._get_model()
                m2 = fp._get_model()
            assert m1 is m2
            assert m1 is mock_instance
        finally:
            fp._model = original

    @pytest.mark.small
    def test_returns_existing_instance_without_creating(self):
        sentinel = MagicMock()
        original = fp._model
        try:
            fp._model = sentinel
            with patch("cli.processor.file_processor.EmbeddingModelManager") as cls:
                result = fp._get_model()
            cls.assert_not_called()
            assert result is sentinel
        finally:
            fp._model = original


class TestGetEmbedding:
    @pytest.mark.small
    def test_returns_float32_array(self):
        fake_vec = np.ones(1024, dtype=np.float64)  # float64 → float32 に変換される
        mock_model = MagicMock()
        mock_model.model.encode.return_value = fake_vec

        with patch("cli.processor.file_processor._get_model", return_value=mock_model):
            result = get_embedding("hello")

        assert result.dtype == np.float32
        mock_model.model.encode.assert_called_once_with(
            "hello", show_progress_bar=False, convert_to_numpy=True
        )


# ---------------------------------------------------------------------------
# data_generator_multiprocessing — medium tests
# ---------------------------------------------------------------------------


class TestDataGeneratorMultiprocessing:
    @pytest.mark.medium
    def test_empty_path_list_yields_nothing(self):
        results = list(data_generator_multiprocessing([]))
        assert results == []

    @pytest.mark.medium
    def test_single_file_with_chunks(self, tmp_path):
        f = tmp_path / "test.md"
        f.write_text("# Hello")

        fake_vectors = np.zeros((1, 1024), dtype=np.float32)
        mock_model = MagicMock()
        mock_model.model.encode.return_value = fake_vectors

        mock_executor = MagicMock()
        mock_executor.__enter__ = lambda s: s
        mock_executor.__exit__ = MagicMock(return_value=False)
        mock_executor.map.return_value = [["chunk0"]]

        with (
            patch("cli.processor.file_processor.ProcessPoolExecutor", return_value=mock_executor),
            patch("cli.processor.file_processor._get_model", return_value=mock_model),
            patch("multiprocessing.get_context"),
        ):
            batches = list(data_generator_multiprocessing([f]))

        records = [r for batch in batches for r in batch]
        assert len(records) == 1
        assert records[0]["text"] == "chunk0"
        assert records[0]["chunk_id"] == 0

    @pytest.mark.medium
    def test_skips_file_with_none_chunks(self, tmp_path):
        f = tmp_path / "test.md"
        f.write_text("content")

        mock_executor = MagicMock()
        mock_executor.__enter__ = lambda s: s
        mock_executor.__exit__ = MagicMock(return_value=False)
        mock_executor.map.return_value = [None]

        with (
            patch("cli.processor.file_processor.ProcessPoolExecutor", return_value=mock_executor),
            patch("multiprocessing.get_context"),
        ):
            batches = list(data_generator_multiprocessing([f]))

        assert batches == []

    @pytest.mark.medium
    def test_batch_splits_at_batch_size(self, tmp_path):
        f = tmp_path / "test.md"
        f.write_text("content")
        chunks = [f"c{i}" for i in range(5)]

        fake_vectors = np.zeros((3, 1024), dtype=np.float32)
        fake_vectors2 = np.zeros((2, 1024), dtype=np.float32)
        mock_model = MagicMock()
        mock_model.model.encode.side_effect = [fake_vectors, fake_vectors2]

        mock_executor = MagicMock()
        mock_executor.__enter__ = lambda s: s
        mock_executor.__exit__ = MagicMock(return_value=False)
        mock_executor.map.return_value = [chunks]

        with (
            patch("cli.processor.file_processor.ProcessPoolExecutor", return_value=mock_executor),
            patch("cli.processor.file_processor._get_model", return_value=mock_model),
            patch("multiprocessing.get_context"),
        ):
            batches = list(data_generator_multiprocessing([f], batch_size=3))

        assert len(batches) == 2
        assert len(batches[0]) == 3
        assert len(batches[1]) == 2

    @pytest.mark.medium
    def test_ignores_non_supported_files_in_directory(self, tmp_path):
        # サポート外ファイルはall_filesに入らない
        txt_file = tmp_path / "ignored.xyz"
        txt_file.write_text("ignored")

        mock_executor = MagicMock()
        mock_executor.__enter__ = lambda s: s
        mock_executor.__exit__ = MagicMock(return_value=False)
        mock_executor.map.return_value = []

        with (
            patch("cli.processor.file_processor.ProcessPoolExecutor", return_value=mock_executor),
            patch("multiprocessing.get_context"),
        ):
            batches = list(data_generator_multiprocessing([tmp_path]))

        assert batches == []


# ---------------------------------------------------------------------------
# _flush_batch — small tests
# ---------------------------------------------------------------------------


class TestFlushBatch:
    @pytest.mark.small
    def test_returns_correct_records(self):
        items = [
            {"text": "hello", "source": "/a.md", "chunk_id": 0},
            {"text": "world", "source": "/a.md", "chunk_id": 1},
        ]
        vectors = np.array([[0.1] * 1024, [0.2] * 1024], dtype=np.float32)

        mock_model_instance = MagicMock()
        mock_model_instance.model.encode.return_value = vectors

        with patch("cli.processor.file_processor._get_model", return_value=mock_model_instance):
            records = _flush_batch(items)

        assert len(records) == 2
        assert records[0]["text"] == "hello"
        assert records[0]["source"] == "/a.md"
        assert records[0]["chunk_id"] == 0
        assert records[1]["text"] == "world"
        assert records[1]["chunk_id"] == 1

    @pytest.mark.small
    def test_empty_items_returns_empty_list(self):
        mock_model_instance = MagicMock()
        mock_model_instance.model.encode.return_value = np.empty((0, 1024), dtype=np.float32)

        with patch("cli.processor.file_processor._get_model", return_value=mock_model_instance):
            records = _flush_batch([])

        assert records == []
