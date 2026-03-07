use std::io::Read;
use std::path::Path;

use anyhow::Result;
use quick_xml::events::Event as XmlEvent;
use quick_xml::Reader;

use crate::processor::markdown::chunk_markdown_text;

pub fn chunk_docx(
    path: &Path,
    chunk_size: usize,
    overlap: usize,
    min_chunk: usize,
) -> Result<Vec<String>> {
    let text = extract_docx_text(path)?;
    if text.trim().is_empty() {
        return Ok(vec![]);
    }
    // XML パーサーが出力する Markdown 形式テキストをそのままチャンク化
    Ok(chunk_markdown_text(&text, chunk_size, overlap, min_chunk))
}

/// DOCX ファイルから word/document.xml を取り出してテキストを抽出する。
fn extract_docx_text(path: &Path) -> Result<String> {
    let file = std::fs::File::open(path)?;
    let mut archive = zip::ZipArchive::new(file)?;

    let xml_content = {
        let mut entry = archive.by_name("word/document.xml")?;
        let mut content = String::new();
        entry.read_to_string(&mut content)?;
        content
    };

    parse_docx_xml(&xml_content)
}

/// DOCX の document.xml を解析してテキストを Markdown 形式で返す。
///
/// - `<w:pStyle w:val="Heading1">` → `# 見出し\n\n`
/// - 通常段落 → `本文\n\n`
fn parse_docx_xml(xml: &str) -> Result<String> {
    let mut reader = Reader::from_str(xml);

    let mut output = String::new();
    let mut current_para = String::new();
    let mut current_style: Option<String> = None;
    let mut in_para = false;
    let mut in_t = false;
    let mut buf = Vec::new();

    loop {
        match reader.read_event_into(&mut buf)? {
            XmlEvent::Start(ref e) => match e.local_name().as_ref() {
                b"p" => {
                    in_para = true;
                    current_para.clear();
                    current_style = None;
                }
                b"t" => {
                    in_t = true;
                }
                _ => {}
            },
            XmlEvent::Empty(ref e) => {
                // <w:pStyle w:val="Heading1"/> のようなスタイル宣言
                if e.local_name().as_ref() == b"pStyle" && in_para {
                    for attr in e.attributes().flatten() {
                        if attr.key.local_name().as_ref() == b"val" {
                            if let Ok(val) = attr.unescape_value() {
                                current_style = Some(val.into_owned());
                            }
                        }
                    }
                }
            }
            XmlEvent::End(ref e) => match e.local_name().as_ref() {
                b"p" => {
                    let para = current_para.trim();
                    if !para.is_empty() {
                        if let Some(level) = style_to_heading_level(current_style.as_deref()) {
                            let hashes = "#".repeat(level);
                            output.push_str(&format!("{} {}\n\n", hashes, para));
                        } else {
                            output.push_str(para);
                            output.push_str("\n\n");
                        }
                    }
                    in_para = false;
                    in_t = false;
                    current_style = None;
                }
                b"t" => {
                    in_t = false;
                }
                _ => {}
            },
            XmlEvent::Text(e) if in_t => {
                let text = e.unescape()?;
                current_para.push_str(&text);
            }
            XmlEvent::Eof => break,
            _ => {}
        }
        buf.clear();
    }

    Ok(output)
}

/// DOCX スタイル名から Markdown 見出しレベル（1〜6）に変換する。
///
/// 英語名 "Heading1"〜"Heading6" のみ対応。未知のスタイルは None を返す。
fn style_to_heading_level(style: Option<&str>) -> Option<usize> {
    let style = style?;
    let lower = style.to_lowercase();
    let rest = lower.strip_prefix("heading")?;
    let n: usize = rest.trim().parse().ok()?;
    if (1..=6).contains(&n) {
        Some(n)
    } else {
        None
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_style_to_heading_level() {
        assert_eq!(style_to_heading_level(Some("Heading1")), Some(1));
        assert_eq!(style_to_heading_level(Some("Heading6")), Some(6));
        assert_eq!(style_to_heading_level(Some("Normal")), None);
        assert_eq!(style_to_heading_level(None), None);
    }

    #[test]
    fn test_parse_docx_xml_heading() {
        let xml = r#"<?xml version="1.0" encoding="UTF-8"?>
<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">
<w:body>
  <w:p>
    <w:pPr><w:pStyle w:val="Heading1"/></w:pPr>
    <w:r><w:t>はじめに</w:t></w:r>
  </w:p>
  <w:p>
    <w:r><w:t>本文テキスト。</w:t></w:r>
  </w:p>
</w:body>
</w:document>"#;
        let result = parse_docx_xml(xml).unwrap();
        assert!(result.contains("# はじめに"));
        assert!(result.contains("本文テキスト。"));
    }
}
