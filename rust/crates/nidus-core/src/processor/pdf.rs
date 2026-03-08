use std::path::Path;

use anyhow::Result;
use std::sync::LazyLock;

use regex::Regex;

use crate::processor::chunker::sentence_boundary_chunker;

static RE_PDF_SPACES: LazyLock<Regex> = LazyLock::new(|| Regex::new(r"[ \t]+").unwrap());

pub fn chunk_pdf(
    path: &Path,
    chunk_size: usize,
    overlap: usize,
    min_chunk: usize,
) -> Result<Vec<String>> {
    anyhow::ensure!(path.exists(), "File not found: {}", path.display());

    let text = pdf_extract::extract_text(path)?;
    let text = normalize_pdf_text(&text);

    if text.is_empty() {
        return Ok(vec![]);
    }

    Ok(sentence_boundary_chunker(
        &text, chunk_size, overlap, min_chunk,
    ))
}

/// PDF 特有の前処理: 水平方向の余分な空白を 1 つに正規化する（改行は保持）。
fn normalize_pdf_text(text: &str) -> String {
    RE_PDF_SPACES.replace_all(text, " ").trim().to_string()
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_normalize_pdf_text() {
        let input = "こんにちは   世界\n次の行";
        let result = normalize_pdf_text(input);
        assert_eq!(result, "こんにちは 世界\n次の行");
    }

    #[test]
    fn test_normalize_preserves_newlines() {
        let input = "行1\n\n行2";
        assert_eq!(normalize_pdf_text(input), "行1\n\n行2");
    }
}
