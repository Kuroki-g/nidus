/// 文境界を優先してテキストをチャンクに分割する。
///
/// 分割点優先順: 。！？ → \n\n → \n → 強制カット
/// overlap: 前チャンク末尾の overlap 文字を次チャンク先頭に追加
/// min_chunk: min_chunk 未満のチャンクは前チャンクに統合
pub fn sentence_boundary_chunker(
    text: &str,
    chunk_size: usize,
    overlap: usize,
    min_chunk: usize,
) -> Vec<String> {
    let text = text.trim();
    if text.is_empty() {
        return vec![];
    }

    let chars: Vec<char> = text.chars().collect();
    let text_len = chars.len();

    if text_len <= chunk_size {
        return vec![text.to_string()];
    }

    let mut chunks: Vec<String> = vec![];
    let mut pos = 0usize;

    while pos < text_len {
        let end = pos + chunk_size;
        if end >= text_len {
            let remaining: String = chars[pos..].iter().collect();
            let remaining = remaining.trim().to_string();
            if !remaining.is_empty() {
                chunks.push(remaining);
            }
            break;
        }

        let split_at = find_split_point(&chars, pos, end);
        let chunk: String = chars[pos..split_at].iter().collect();
        let chunk = chunk.trim().to_string();
        if !chunk.is_empty() {
            chunks.push(chunk);
        }

        let next_pos = split_at.saturating_sub(overlap);
        pos = if next_pos > pos { next_pos } else { split_at };
    }

    merge_short_chunks(chunks, min_chunk)
}

/// start〜end の範囲で最適な分割点を探す
fn find_split_point(chars: &[char], start: usize, end: usize) -> usize {
    const ENDINGS: [char; 3] = ['。', '！', '？'];

    // 1. 句点・感嘆符・疑問符（[。！？]+）の最後のグループ直後
    let mut last_ending: Option<usize> = None;
    let mut i = start;
    while i < end {
        if ENDINGS.contains(&chars[i]) {
            let mut j = i;
            while j < end && ENDINGS.contains(&chars[j]) {
                j += 1;
            }
            last_ending = Some(j);
            i = j;
        } else {
            i += 1;
        }
    }
    if let Some(pos) = last_ending {
        return pos;
    }

    // 2. 段落境界 \n\n（後ろから検索）
    for i in (start..end.saturating_sub(1)).rev() {
        if chars[i] == '\n' && chars[i + 1] == '\n' {
            return i + 2;
        }
    }

    // 3. 行境界 \n（後ろから検索）
    for i in (start..end).rev() {
        if chars[i] == '\n' {
            return i + 1;
        }
    }

    // 4. 強制カット
    end
}

fn merge_short_chunks(chunks: Vec<String>, min_chunk: usize) -> Vec<String> {
    if chunks.is_empty() || min_chunk == 0 {
        return chunks;
    }
    let mut result: Vec<String> = vec![];
    for chunk in chunks {
        if let Some(last) = result.last_mut() {
            if chunk.chars().count() < min_chunk {
                last.push_str("\n\n");
                last.push_str(&chunk);
                continue;
            }
        }
        result.push(chunk);
    }
    result
}

/// `[(heading, body), ...]` からチャンクリストを生成する共通ロジック。
///
/// body が空のセクションはスキップ。heading がある場合は各チャンクにプレフィックスとして付与。
pub fn sections_to_chunks(
    sections: &[(String, String)],
    chunk_size: usize,
    overlap: usize,
    min_chunk: usize,
) -> Vec<String> {
    let mut chunks = vec![];
    for (heading, body) in sections {
        let body = body.trim();
        if body.is_empty() {
            continue;
        }
        let body_chunks = sentence_boundary_chunker(body, chunk_size, overlap, min_chunk);
        for body_chunk in body_chunks {
            if heading.is_empty() {
                chunks.push(body_chunk);
            } else {
                chunks.push(format!("{}\n{}", heading, body_chunk));
            }
        }
    }
    chunks
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_empty_input() {
        assert!(sentence_boundary_chunker("", 1000, 150, 200).is_empty());
        assert!(sentence_boundary_chunker("   ", 1000, 150, 200).is_empty());
    }

    #[test]
    fn test_short_text_no_split() {
        let text = "短いテキスト";
        let chunks = sentence_boundary_chunker(text, 1000, 150, 200);
        assert_eq!(chunks, vec!["短いテキスト"]);
    }

    #[test]
    fn test_split_on_sentence_ending() {
        // 1000文字を超えるテキストで句点で分割されることを確認
        let part1 = "あ".repeat(900);
        let part2 = "い".repeat(900);
        let text = format!("{}。{}", part1, part2);
        let chunks = sentence_boundary_chunker(&text, 1000, 0, 0);
        assert!(chunks.len() >= 2);
        assert!(chunks[0].ends_with('。'));
    }

    #[test]
    fn test_merge_short_chunks() {
        let chunks = vec!["長いチャンク".repeat(50), "短".to_string()];
        let result = merge_short_chunks(chunks.clone(), 200);
        // "短" (1文字) < 200 なので前に統合される
        assert_eq!(result.len(), 1);
    }

    #[test]
    fn test_sections_to_chunks_with_heading() {
        let sections = vec![("## 見出し".to_string(), "本文テキスト".to_string())];
        let chunks = sections_to_chunks(&sections, 1000, 150, 0);
        assert_eq!(chunks.len(), 1);
        assert!(chunks[0].starts_with("## 見出し\n"));
    }

    #[test]
    fn test_sections_to_chunks_empty_body() {
        let sections = vec![("## 見出し".to_string(), "   ".to_string())];
        let chunks = sections_to_chunks(&sections, 1000, 150, 0);
        assert!(chunks.is_empty());
    }
}
