from unittest.mock import MagicMock, patch

import pytest
from common.model import DEFAULT_MODEL_ID, MODEL_VECTOR_SIZE, EmbeddingModelManager

pytestmark = pytest.mark.small


@pytest.fixture(autouse=True)
def reset_singleton():
    EmbeddingModelManager._instance = None
    EmbeddingModelManager._model = None
    EmbeddingModelManager._model_id = None
    EmbeddingModelManager._vector_size = None
    yield
    EmbeddingModelManager._instance = None
    EmbeddingModelManager._model = None
    EmbeddingModelManager._model_id = None
    EmbeddingModelManager._vector_size = None


def _patch_init(mock_model: MagicMock):
    """_init_model をモックして、シングルトンを即座に初期化する。"""

    def side_effect():
        EmbeddingModelManager._instance = object.__new__(EmbeddingModelManager)
        EmbeddingModelManager._model = mock_model
        EmbeddingModelManager._vector_size = MODEL_VECTOR_SIZE

    return patch.object(EmbeddingModelManager, "_init_model", side_effect=side_effect)


def test_singleton_returns_same_instance():
    mock_static = MagicMock()
    with _patch_init(mock_static):
        instance1 = EmbeddingModelManager()
        instance2 = EmbeddingModelManager()
    assert instance1 is instance2


def test_vector_size_property():
    mock_static = MagicMock()
    with _patch_init(mock_static):
        instance = EmbeddingModelManager()
    assert instance.vector_size == MODEL_VECTOR_SIZE


def test_model_property_returns_mock():
    mock_static = MagicMock()
    with _patch_init(mock_static):
        instance = EmbeddingModelManager()
    assert instance.model is mock_static


def test_default_model_id_defined():
    assert DEFAULT_MODEL_ID == "hotchpotch/static-embedding-japanese"


def test_model_vector_size_constant():
    assert MODEL_VECTOR_SIZE == 1024


def test_init_model_called_once_for_singleton():
    mock_static = MagicMock()
    with _patch_init(mock_static) as mock_init:
        EmbeddingModelManager()
        EmbeddingModelManager()
    mock_init.assert_called_once()
