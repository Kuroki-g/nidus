from pathlib import Path
from typing import Iterable, List, Optional, Union


from common.model import EmbeddingModelManager
import numpy as np

model = EmbeddingModelManager()


def get_embedding(text):
    return model.model.encode(text).astype(np.float32)


def load_and_chunk_md(file_path: Path, chunk_size=500):
    with open(file_path, "r", encoding="utf-8") as f:
        content = f.read()

    # NOTE: 簡易的な文字数分割
    # セクション単位などにブラッシュアップしたいところ
    chunks = [content[i : i + chunk_size] for i in range(0, len(content), chunk_size)]
    return chunks


def get_chunk(file_path: Path) -> Optional[List[str]]:
    if not file_path.is_file():
        return None
    if file_path.suffix == ".md":
        return load_and_chunk_md(file_path)
    else:
        print("TODO: implement pdf, txt parse")
        return None


def data_generator(
    path_list: List[Union[str, Path]], batch_size: int = 1000
) -> Iterable[List[dict]]:
    """TODO: refactoring"""
    buffer = []

    for p in path_list:
        path_obj = Path(p)
        targets = path_obj.rglob("*") if path_obj.is_dir() else [path_obj]

        for file_path in targets:
            chunks = get_chunk(file_path)
            if not chunks:
                print(f"[Skip] No content or not supported: {file_path}")
                continue

            print(f"Processing: {file_path} ({len(chunks)} chunks)")

            for i, chunk in enumerate(chunks):
                try:
                    # スキーマに合わせてデータを構築
                    vector_data = get_embedding(chunk)
                    record = {
                        "vector": vector_data,
                        "text": chunk,
                        "metadata": {
                            "source": str(file_path.absolute()),
                            "chunk_id": i,
                        },
                    }
                    buffer.append(record)

                    # 指定したバッチサイズに達したら yield
                    if len(buffer) >= batch_size:
                        yield buffer
                        buffer = []

                except Exception as e:
                    print(f"[Error] Failed to process chunk {i} in {file_path}: {e}")
    if buffer:
        yield buffer
