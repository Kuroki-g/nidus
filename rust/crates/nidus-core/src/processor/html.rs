use std::path::Path;

use anyhow::Result;
use std::sync::LazyLock;

use ego_tree::iter::Edge;
use regex::Regex;
use scraper::{Html, Node};

use crate::processor::chunker::sections_to_chunks;

static RE_SPACES: LazyLock<Regex> = LazyLock::new(|| Regex::new(r"[^\S\n]+").unwrap());
static RE_NEWLINES: LazyLock<Regex> = LazyLock::new(|| Regex::new(r"\n{3,}").unwrap());

const SKIP_TAGS: &[&str] = &["script", "style", "noscript", "iframe", "svg", "head"];
const HEADING_TAGS: &[&str] = &["h1", "h2", "h3", "h4", "h5", "h6"];
const BLOCK_TAGS: &[&str] = &[
    "p",
    "div",
    "li",
    "td",
    "th",
    "dt",
    "dd",
    "blockquote",
    "pre",
    "section",
    "article",
    "main",
    "nav",
    "footer",
    "header",
    "aside",
];

pub fn chunk_html(
    path: &Path,
    chunk_size: usize,
    overlap: usize,
    min_chunk: usize,
) -> Result<Vec<String>> {
    let content = std::fs::read_to_string(path)?;
    if content.trim().is_empty() {
        return Ok(vec![]);
    }
    let document = Html::parse_document(&content);
    let sections = extract_html_sections(&document);
    if sections.is_empty() {
        return Ok(vec![]);
    }
    Ok(sections_to_chunks(
        &sections, chunk_size, overlap, min_chunk,
    ))
}

fn normalize_whitespace(text: &str) -> String {
    let s = RE_SPACES.replace_all(text, " ");
    let s = RE_NEWLINES.replace_all(&s, "\n\n");
    s.trim().to_string()
}

fn extract_html_sections(doc: &Html) -> Vec<(String, String)> {
    let mut sections: Vec<(String, String)> = vec![];
    let mut current_heading = String::new();
    let mut current_body = String::new();
    let mut skip_depth: i32 = 0;
    let mut in_heading = false;
    let mut heading_buf = String::new();

    for edge in doc.root_element().traverse() {
        match edge {
            Edge::Open(node) => match node.value() {
                Node::Element(element) => {
                    let tag = element.name();
                    if skip_depth > 0 {
                        if SKIP_TAGS.contains(&tag) {
                            skip_depth += 1;
                        }
                        continue;
                    }
                    if SKIP_TAGS.contains(&tag) {
                        skip_depth += 1;
                        continue;
                    }
                    if HEADING_TAGS.contains(&tag) {
                        let body = normalize_whitespace(&current_body);
                        if !body.is_empty() {
                            sections.push((current_heading.clone(), body));
                        }
                        current_heading = String::new();
                        current_body = String::new();
                        in_heading = true;
                        heading_buf = String::new();
                    } else if BLOCK_TAGS.contains(&tag) {
                        current_body.push('\n');
                    }
                }
                Node::Text(text) => {
                    if skip_depth > 0 {
                        continue;
                    }
                    let s: &str = text;
                    if in_heading {
                        heading_buf.push_str(s);
                    } else {
                        current_body.push_str(s);
                    }
                }
                _ => {}
            },
            Edge::Close(node) => {
                if let Node::Element(element) = node.value() {
                    let tag = element.name();
                    if SKIP_TAGS.contains(&tag) {
                        skip_depth = (skip_depth - 1).max(0);
                        continue;
                    }
                    if skip_depth > 0 {
                        continue;
                    }
                    if HEADING_TAGS.contains(&tag) && in_heading {
                        current_heading = normalize_whitespace(&heading_buf);
                        in_heading = false;
                    } else if BLOCK_TAGS.contains(&tag) {
                        current_body.push('\n');
                    }
                }
            }
        }
    }

    let body = normalize_whitespace(&current_body);
    if !body.is_empty() {
        sections.push((current_heading, body));
    }

    sections
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_basic_html() {
        let html = "<html><body><h1>タイトル</h1><p>本文</p></body></html>";
        let doc = Html::parse_document(html);
        let sections = extract_html_sections(&doc);
        assert!(!sections.is_empty());
        assert_eq!(sections[0].0, "タイトル");
    }

    #[test]
    fn test_script_skipped() {
        let html = "<html><body><script>alert(1)</script><p>テキスト</p></body></html>";
        let doc = Html::parse_document(html);
        let sections = extract_html_sections(&doc);
        // スクリプト内容は含まれないこと
        for (h, b) in &sections {
            assert!(!h.contains("alert") && !b.contains("alert"));
        }
    }

    #[test]
    fn test_normalize_whitespace() {
        assert_eq!(normalize_whitespace("a  b\n\n\nc"), "a b\n\nc");
    }
}
