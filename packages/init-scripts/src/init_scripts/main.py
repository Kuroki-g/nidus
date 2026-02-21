import os
from pathlib import Path
from typing import List, Union
from sentence_transformers import SentenceTransformer

import lancedb

# Offline not to access hagging face by mistake
os.environ["TRANSFORMERS_OFFLINE"] = "1"
os.environ["HF_DATASETS_OFFLINE"] = "1"

# https://huggingface.co/hotchpotch/static-embedding-japanese
model_name = "hotchpotch/static-embedding-japanese"
model = SentenceTransformer(model_name, local_files_only=True)

def get_embedding(text):
    return model.encode(text).tolist()

def load_and_chunk_md(file_path: Path, chunk_size=500):
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()

    # NOTE: 簡易的な文字数分割
    # セクション単位などにブラッシュアップしたいところ
    chunks = [content[i:i + chunk_size] for i in range(0, len(content), chunk_size)]
    return chunks

def init_db(path_list: List[Union[str, Path]], table_name: str = "markdown_docs"):
    """
    指定されたファイルまたはディレクトリからドキュメント類を読み込み、LanceDBを初期化する
    """
    db = lancedb.connect("./.lancedb")
    
    all_data = []
    for p in path_list:
        path_obj = Path(p)
        targets = path_obj.rglob("*.md") if path_obj.is_dir() else [path_obj]
        
        for file_path in targets:
            if not file_path.is_file():
                continue
            if file_path.suffix == ".md":
                chunks = load_and_chunk_md(file_path)
            else:
                print("TODO: implement pdf, txt parse")
                continue
            print(f"Indexing: {file_path}")
            
            for i, chunk in enumerate(chunks):
                all_data.append({
                    "vector": get_embedding(chunk),
                    "text": chunk,
                    "metadata": {
                        "source": str(file_path.absolute()),
                        "chunk_id": i
                    }
                })

    if all_data:
        table = db.create_table(table_name, data=all_data, mode="overwrite")
        print(f"Total: {len(all_data)} chunks indexed.")
        return table
    
    print("No data found.")
    return None

def main():
    targets = ["./docs", "README.md"] 
    init_db(targets)

if __name__ == "__main__":
    main()
