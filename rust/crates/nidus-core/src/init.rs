use std::{io::Write, path::Path};

use anyhow::{Context, Result};
use futures::StreamExt;

pub const DEFAULT_MODEL_ID: &str = "hotchpotch/static-embedding-japanese";

/// model_dir に配置する (remote_path, local_name) のペア。
const MODEL_FILES: &[(&str, &str)] = &[
    ("0_StaticEmbedding/tokenizer.json", "tokenizer.json"),
    ("0_StaticEmbedding/model.safetensors", "model.safetensors"),
];

/// HuggingFace からモデルファイルをダウンロードして `model_dir` に保存する。
///
/// ファイルが既に存在する場合はスキップする。
/// ダウンロード中は進捗をターミナルに出力する。
pub async fn download_model(model_dir: &Path) -> Result<()> {
    std::fs::create_dir_all(model_dir)
        .with_context(|| format!("cannot create model dir: {}", model_dir.display()))?;

    for (remote_path, local_name) in MODEL_FILES {
        let dest = model_dir.join(local_name);
        if dest.exists() {
            println!("{local_name}: already exists, skipping.");
            continue;
        }

        let url = format!("https://huggingface.co/{DEFAULT_MODEL_ID}/resolve/main/{remote_path}");
        println!("Downloading {local_name}...");
        download_file(&url, &dest)
            .await
            .with_context(|| format!("failed to download {local_name}"))?;
        println!("  -> saved to {}", dest.display());
    }

    Ok(())
}

async fn download_file(url: &str, dest: &Path) -> Result<()> {
    let client = reqwest::Client::new();
    let response = client
        .get(url)
        .send()
        .await
        .with_context(|| format!("GET {url}"))?;

    anyhow::ensure!(
        response.status().is_success(),
        "HTTP {} for {url}",
        response.status()
    );

    let total = response.content_length();
    let mut stream = response.bytes_stream();

    // 途中でエラーになっても壊れたファイルが残らないよう .tmp に書いてからリネーム
    let mut tmp_name = dest.file_name().unwrap().to_os_string();
    tmp_name.push(".tmp");
    let tmp_path = dest.with_file_name(tmp_name);
    let mut file = std::fs::File::create(&tmp_path)
        .with_context(|| format!("cannot create {}", tmp_path.display()))?;

    let mut downloaded: u64 = 0;
    while let Some(chunk) = stream.next().await {
        let chunk = chunk.context("stream read error")?;
        file.write_all(&chunk).context("write error")?;
        downloaded += chunk.len() as u64;

        if let Some(total) = total {
            let pct = downloaded * 100 / total;
            print!("\r  {downloaded}/{total} bytes ({pct}%)   ");
            let _ = std::io::stdout().flush();
        }
    }
    if total.is_some() {
        println!();
    }

    std::fs::rename(&tmp_path, dest)
        .with_context(|| format!("rename {} -> {}", tmp_path.display(), dest.display()))?;

    Ok(())
}
