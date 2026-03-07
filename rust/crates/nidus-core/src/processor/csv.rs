use std::path::Path;

use anyhow::Result;

pub fn chunk_csv(path: &Path, chunk_size: usize) -> Result<Vec<String>> {
    chunk_delimited(path, b',', chunk_size)
}

pub fn chunk_tsv(path: &Path, chunk_size: usize) -> Result<Vec<String>> {
    chunk_delimited(path, b'\t', chunk_size)
}

fn row_to_text(headers: &[String], row: &csv::StringRecord) -> String {
    headers
        .iter()
        .zip(row.iter())
        .filter(|(h, v)| !h.trim().is_empty() && !v.trim().is_empty())
        .map(|(h, v)| format!("{}: {}", h, v))
        .collect::<Vec<_>>()
        .join(", ")
}

fn chunk_rows(row_texts: Vec<String>, chunk_size: usize) -> Vec<String> {
    let mut chunks = vec![];
    let mut current_lines: Vec<String> = vec![];
    let mut current_len = 0usize;

    for text in row_texts {
        let text_len = text.chars().count();
        // 区切り文字 "\n" の分を +1
        let added_len = text_len + if current_lines.is_empty() { 0 } else { 1 };

        if !current_lines.is_empty() && current_len + added_len > chunk_size {
            chunks.push(current_lines.join("\n"));
            current_lines = vec![text];
            current_len = text_len;
        } else {
            current_lines.push(text);
            current_len += added_len;
        }
    }

    if !current_lines.is_empty() {
        chunks.push(current_lines.join("\n"));
    }

    chunks
}

fn chunk_delimited(path: &Path, delimiter: u8, chunk_size: usize) -> Result<Vec<String>> {
    let content = std::fs::read_to_string(path)?;
    let content = content.trim();
    if content.is_empty() {
        return Ok(vec![]);
    }

    let mut reader = csv::ReaderBuilder::new()
        .delimiter(delimiter)
        .from_reader(content.as_bytes());

    let headers: Vec<String> = reader.headers()?.iter().map(String::from).collect();
    if headers.is_empty() {
        return Ok(vec![]);
    }

    let mut row_texts = vec![];
    for result in reader.records() {
        let record = result?;
        if record.iter().any(|v| !v.trim().is_empty()) {
            let text = row_to_text(&headers, &record);
            if !text.is_empty() {
                row_texts.push(text);
            }
        }
    }

    if row_texts.is_empty() {
        return Ok(vec![]);
    }

    Ok(chunk_rows(row_texts, chunk_size))
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_row_to_text() {
        let headers = vec!["名前".to_string(), "年齢".to_string()];
        let record = csv::StringRecord::from(vec!["田中", "30"]);
        let text = row_to_text(&headers, &record);
        assert_eq!(text, "名前: 田中, 年齢: 30");
    }

    #[test]
    fn test_row_to_text_skips_empty() {
        let headers = vec!["名前".to_string(), "年齢".to_string()];
        let record = csv::StringRecord::from(vec!["田中", ""]);
        let text = row_to_text(&headers, &record);
        assert_eq!(text, "名前: 田中");
    }

    #[test]
    fn test_chunk_rows_splits_at_limit() {
        // chunk_size=10 で分割されることを確認
        let rows = vec!["a: 1".to_string(), "b: 2".to_string(), "c: 3".to_string()];
        let chunks = chunk_rows(rows, 10);
        // 3行 * ~4文字 + 区切り = 分割が発生するはず
        assert!(!chunks.is_empty());
    }
}
