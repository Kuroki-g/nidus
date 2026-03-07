use std::path::Path;

use anyhow::Result;
use pulldown_cmark::{Event, HeadingLevel, Options, Parser, Tag, TagEnd};

use crate::processor::chunker::sections_to_chunks;

pub fn chunk_markdown(
    path: &Path,
    chunk_size: usize,
    overlap: usize,
    min_chunk: usize,
) -> Result<Vec<String>> {
    let content = std::fs::read_to_string(path)?;
    Ok(chunk_markdown_text(
        &content, chunk_size, overlap, min_chunk,
    ))
}

pub fn chunk_markdown_text(
    content: &str,
    chunk_size: usize,
    overlap: usize,
    min_chunk: usize,
) -> Vec<String> {
    if content.trim().is_empty() {
        return vec![];
    }
    let sections = extract_sections(content);
    sections_to_chunks(&sections, chunk_size, overlap, min_chunk)
}

fn heading_level_num(level: HeadingLevel) -> usize {
    match level {
        HeadingLevel::H1 => 1,
        HeadingLevel::H2 => 2,
        HeadingLevel::H3 => 3,
        HeadingLevel::H4 => 4,
        HeadingLevel::H5 => 5,
        HeadingLevel::H6 => 6,
    }
}

/// Markdown AST を走査して `[(heading, body), ...]` を構築する。
///
/// heading は `"## 見出し"` 形式。先頭の見出しなし部分は `("", body)`。
fn extract_sections(content: &str) -> Vec<(String, String)> {
    let mut sections: Vec<(String, String)> = vec![];
    let mut current_heading = String::new();
    let mut current_body_parts: Vec<String> = vec![];
    let mut current_text = String::new();
    let mut in_heading = false;
    let mut heading_level = 0usize;

    let parser = Parser::new_ext(content, Options::all());

    for event in parser {
        match event {
            Event::Start(Tag::Heading { level, .. }) => {
                // 現在のテキストバッファを body_parts へフラッシュ
                flush_text(&mut current_text, &mut current_body_parts);
                // 現在のセクションを保存
                if !current_body_parts.is_empty() {
                    sections.push((current_heading.clone(), current_body_parts.join("\n\n")));
                    current_body_parts.clear();
                }
                heading_level = heading_level_num(level);
                in_heading = true;
                current_text.clear();
            }
            Event::End(TagEnd::Heading(_)) => {
                let hashes = "#".repeat(heading_level);
                current_heading = format!("{} {}", hashes, current_text.trim());
                current_text.clear();
                in_heading = false;
            }
            Event::End(TagEnd::Paragraph)
            | Event::End(TagEnd::BlockQuote(_))
            | Event::End(TagEnd::Item) => {
                if !in_heading {
                    flush_text(&mut current_text, &mut current_body_parts);
                }
            }
            Event::Text(t) | Event::Code(t) => {
                current_text.push_str(&t);
            }
            Event::SoftBreak | Event::HardBreak => {
                if !in_heading {
                    current_text.push('\n');
                }
            }
            _ => {}
        }
    }

    // 末尾の残りをフラッシュ
    flush_text(&mut current_text, &mut current_body_parts);
    if !current_body_parts.is_empty() {
        sections.push((current_heading, current_body_parts.join("\n\n")));
    }

    sections
}

fn flush_text(text: &mut String, parts: &mut Vec<String>) {
    let t = text.trim().to_string();
    if !t.is_empty() {
        parts.push(t);
    }
    text.clear();
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_empty() {
        assert!(chunk_markdown_text("", 1000, 150, 200).is_empty());
        assert!(chunk_markdown_text("   ", 1000, 150, 200).is_empty());
    }

    #[test]
    fn test_heading_becomes_prefix() {
        let content = "## はじめに\n\n本文テキストです。";
        let chunks = chunk_markdown_text(content, 1000, 150, 0);
        assert_eq!(chunks.len(), 1);
        assert!(chunks[0].starts_with("## はじめに\n"));
    }

    #[test]
    fn test_preamble_without_heading() {
        let content = "前置き\n\n## セクション\n\n本文";
        let chunks = chunk_markdown_text(content, 1000, 150, 0);
        assert_eq!(chunks.len(), 2);
        assert_eq!(chunks[0], "前置き");
        assert!(chunks[1].starts_with("## セクション\n"));
    }

    #[test]
    fn test_extract_sections_multiple_headings() {
        let content = "## H1\n\nbody1\n\n## H2\n\nbody2";
        let sections = extract_sections(content);
        assert_eq!(sections.len(), 2);
        assert_eq!(sections[0].0, "## H1");
        assert_eq!(sections[1].0, "## H2");
    }
}
