import logging
import os
from sentence_transformers import SentenceTransformer

logger = logging.getLogger(__name__)

os.environ["TRANSFORMERS_OFFLINE"] = "1"
os.environ["HF_DATASETS_OFFLINE"] = "1"

# https://huggingface.co/hotchpotch/static-embedding-japanese
DEFAULT_MODEL_NAME = "hotchpotch/static-embedding-japanese"
MODEL_VECTOR_SIZE = 1024


class EmbeddingModelManager:
    _instance = None
    _model = None
    _vector_size = None

    def __new__(cls):
        if cls._instance is None:
            logger.debug("initializing database.")
            cls._instance = super(EmbeddingModelManager, cls).__new__(cls)
            model_name = DEFAULT_MODEL_NAME
            cls._model = SentenceTransformer(model_name, local_files_only=True)
            vector_size = MODEL_VECTOR_SIZE
            cls._vector_size = vector_size
            logger.info("initializing database done.")
        return cls._instance

    @property
    def model(self) -> SentenceTransformer:
        return self._model

    @property
    def vector_size(self) -> int:
        return self._vector_size
