import logging
from pathlib import Path
from common.config import settings
import threading
from huggingface_hub import snapshot_download
from model2vec import StaticModel

logger = logging.getLogger(__name__)

# https://huggingface.co/hotchpotch/static-embedding-japanese
DEFAULT_MODEL_ID = "hotchpotch/static-embedding-japanese"
MODEL_VECTOR_SIZE = 1024


class EmbeddingModelManager:
    _instance = None
    _model = None
    _model_id = None
    _vector_size = None
    _lock = threading.Lock()

    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    logger.debug("initializing model.")
                    cls._init_model(cls)
                    logger.info("initializing model done.")
        return cls._instance

    def _init_model(cls):
        cls._instance = super(EmbeddingModelManager, cls).__new__(cls)
        _model_id = DEFAULT_MODEL_ID

        logger.debug("reading: local file model snapshot...")
        local_path = snapshot_download(_model_id, local_files_only=True)
        local_path = Path(local_path).resolve()
        if local_path.exists():
            logger.debug(f"success to resolve model path: {local_path}")
        else:
            logger.warning(f"failed to resolve model path: {local_path}")

        logger.debug("done: reading local file model snapshot.")
        cls._model = StaticModel.from_sentence_transformers(
            _model_id,
            force_download=False,
        )
        cls._vector_size = MODEL_VECTOR_SIZE

    @property
    def model(self) -> StaticModel:
        return self._model

    @property
    def vector_size(self) -> int:
        return self._vector_size
