use std::path::Path;

use anyhow::Result;
use std::sync::LazyLock;

use regex::Regex;

use crate::processor::chunker::{sections_to_chunks, sentence_boundary_chunker};

static ADOC_HEADING: LazyLock<Regex> = LazyLock::new(|| Regex::new(r"(?m)^(={1,6})\s+(.+)$").unwrap());

pub fn chunk_plain_text(
    path: &Path,
    chunk_size: usize,
    overlap: usize,
    min_chunk: usize,
) -> Result<Vec<String>> {
    let content = std::fs::read_to_string(path)?;
    let content = content.trim();
    if content.is_empty() {
        return Ok(vec![]);
    }
    Ok(sentence_boundary_chunker(
        content, chunk_size, overlap, min_chunk,
    ))
}

pub fn chunk_asciidoc(
    path: &Path,
    chunk_size: usize,
    overlap: usize,
    min_chunk: usize,
) -> Result<Vec<String>> {
    let content = std::fs::read_to_string(path)?;
    let content = content.trim().to_string();
    if content.is_empty() {
        return Ok(vec![]);
    }
    let sections = extract_asciidoc_sections(&content);
    Ok(sections_to_chunks(
        &sections, chunk_size, overlap, min_chunk,
    ))
}

fn extract_asciidoc_sections(text: &str) -> Vec<(String, String)> {
    // (match_start, body_start, heading_text) を収集
    let matches: Vec<(usize, usize, String)> = ADOC_HEADING
        .captures_iter(text)
        .map(|cap| {
            let m = cap.get(0).unwrap();
            let level_len = cap.get(1).unwrap().as_str().len();
            let title = cap.get(2).unwrap().as_str().trim();
            let heading = format!("{} {}", "=".repeat(level_len), title);
            (m.start(), m.end(), heading)
        })
        .collect();

    if matches.is_empty() {
        return vec![("".to_string(), text.to_string())];
    }

    let mut sections = vec![];

    // 最初の見出し前のプリアンブル
    if matches[0].0 > 0 {
        let preamble = text[..matches[0].0].trim();
        if !preamble.is_empty() {
            sections.push(("".to_string(), preamble.to_string()));
        }
    }

    for i in 0..matches.len() {
        let (_, body_start, ref heading) = matches[i];
        let body_end = if i + 1 < matches.len() {
            matches[i + 1].0
        } else {
            text.len()
        };
        let body = text[body_start..body_end].trim().to_string();
        sections.push((heading.clone(), body));
    }

    sections
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_asciidoc_no_headings() {
        let text = "ただのテキスト";
        let sections = extract_asciidoc_sections(text);
        assert_eq!(sections.len(), 1);
        assert_eq!(sections[0].0, "");
        assert_eq!(sections[0].1, "ただのテキスト");
    }

    #[test]
    fn test_asciidoc_with_headings() {
        let text = "== はじめに\n\n本文1\n\n=== 節\n\n本文2";
        let sections = extract_asciidoc_sections(text);
        assert_eq!(sections.len(), 2);
        assert_eq!(sections[0].0, "== はじめに");
        assert_eq!(sections[1].0, "=== 節");
    }

    #[test]
    fn test_asciidoc_preamble() {
        let text = "前置き\n\n== 見出し\n\n本文";
        let sections = extract_asciidoc_sections(text);
        assert_eq!(sections.len(), 2);
        assert_eq!(sections[0].0, "");
        assert_eq!(sections[0].1, "前置き");
    }
}
