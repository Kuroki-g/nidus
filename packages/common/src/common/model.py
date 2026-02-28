import logging
import threading
from huggingface_hub import snapshot_download
from model2vec import StaticModel

logger = logging.getLogger(__name__)

# https://huggingface.co/hotchpotch/static-embedding-japanese
DEFAULT_MODEL_NAME = "hotchpotch/static-embedding-japanese"
MODEL_VECTOR_SIZE = 1024


class EmbeddingModelManager:
    _instance = None
    _model = None
    _vector_size = None
    _lock = threading.Lock()

    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    logger.debug("initializing model.")
                    cls._instance = super(EmbeddingModelManager, cls).__new__(cls)
                    local_path = snapshot_download(
                        DEFAULT_MODEL_NAME, local_files_only=True
                    )
                    cls._model = StaticModel.from_sentence_transformers(local_path)
                    cls._vector_size = MODEL_VECTOR_SIZE
                    logger.info("initializing model done.")
        return cls._instance

    @property
    def model(self) -> StaticModel:
        return self._model

    @property
    def vector_size(self) -> int:
        return self._vector_size
