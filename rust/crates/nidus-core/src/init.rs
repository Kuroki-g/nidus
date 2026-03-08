use std::{
    io::{Read, Write},
    path::Path,
};

use anyhow::{Context, Result};

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
    let url = url.to_string();
    let dest = dest.to_path_buf();
    tokio::task::spawn_blocking(move || download_file_sync(&url, &dest))
        .await
        .context("download thread panicked")?
}

fn download_file_sync(url: &str, dest: &std::path::PathBuf) -> Result<()> {
    let response = ureq::get(url)
        .call()
        .with_context(|| format!("GET {url}"))?;

    let total = response
        .headers()
        .get("content-length")
        .and_then(|v| v.to_str().ok())
        .and_then(|v| v.parse::<u64>().ok());

    // 途中でエラーになっても壊れたファイルが残らないよう .tmp に書いてからリネーム
    let mut tmp_name = dest.file_name().unwrap().to_os_string();
    tmp_name.push(".tmp");
    let tmp_path = dest.with_file_name(tmp_name);
    let mut file = std::fs::File::create(&tmp_path)
        .with_context(|| format!("cannot create {}", tmp_path.display()))?;

    let mut reader = response.into_body().into_reader();
    let mut buf = [0u8; 8192];
    let mut downloaded: u64 = 0;
    loop {
        let n = reader.read(&mut buf).context("stream read error")?;
        if n == 0 {
            break;
        }
        file.write_all(&buf[..n]).context("write error")?;
        downloaded += n as u64;

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
