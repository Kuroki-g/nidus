pub mod chunker;
pub mod csv;
pub mod docx;
pub mod html;
pub mod markdown;
pub mod pdf;
pub mod text;

use std::path::Path;

pub use chunker::{sections_to_chunks, sentence_boundary_chunker};

pub const DEFAULT_CHUNK_SIZE: usize = 1000;
pub const DEFAULT_OVERLAP: usize = 150;
pub const DEFAULT_MIN_CHUNK: usize = 200;

/// ファイルパスからチャンクリストを生成する。
///
/// サポートされていない拡張子の場合は `None` を返す。
/// 処理中にエラーが発生した場合も `None` を返し、標準エラーに出力する。
pub fn get_chunks(path: &Path) -> Option<Vec<String>> {
    if !path.is_file() {
        return None;
    }

    let ext = path.extension()?.to_str()?.to_lowercase();

    let result = match ext.as_str() {
        "md" => {
            markdown::chunk_markdown(path, DEFAULT_CHUNK_SIZE, DEFAULT_OVERLAP, DEFAULT_MIN_CHUNK)
        }
        "adoc" => {
            text::chunk_asciidoc(path, DEFAULT_CHUNK_SIZE, DEFAULT_OVERLAP, DEFAULT_MIN_CHUNK)
        }
        "txt" => {
            text::chunk_plain_text(path, DEFAULT_CHUNK_SIZE, DEFAULT_OVERLAP, DEFAULT_MIN_CHUNK)
        }
        "pdf" => pdf::chunk_pdf(path, DEFAULT_CHUNK_SIZE, DEFAULT_OVERLAP, DEFAULT_MIN_CHUNK),
        "html" | "htm" => {
            html::chunk_html(path, DEFAULT_CHUNK_SIZE, DEFAULT_OVERLAP, DEFAULT_MIN_CHUNK)
        }
        "docx" => docx::chunk_docx(path, DEFAULT_CHUNK_SIZE, DEFAULT_OVERLAP, DEFAULT_MIN_CHUNK),
        "csv" => csv::chunk_csv(path, DEFAULT_CHUNK_SIZE),
        "tsv" => csv::chunk_tsv(path, DEFAULT_CHUNK_SIZE),
        _ => return None,
    };

    match result {
        Ok(chunks) => Some(chunks),
        Err(e) => {
            eprintln!("processor error [{}]: {e}", path.display());
            None
        }
    }
}
