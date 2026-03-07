use std::path::PathBuf;

use anyhow::Result;
use clap::{Parser, Subcommand};
use nidus_core::{
    config::Config,
    db::{self, search::search_docs, update::update_files_in_db, SearchResult},
    embedding::EmbeddingModel,
    init::download_model,
};

#[derive(Parser)]
#[command(name = "nidus", about = "Japanese local document search engine")]
struct Cli {
    #[command(subcommand)]
    command: Commands,
}

#[derive(Subcommand)]
enum Commands {
    /// Download the embedding model from HuggingFace.
    ///
    /// nidus init
    Init,
    /// Add or update documents in the database.
    ///
    /// nidus add -f update-target.txt -f add-target-dir/
    Add {
        /// File(s) or directory to be added or updated
        #[arg(short = 'f', long = "file", required = true, value_name = "PATH")]
        files: Vec<PathBuf>,
    },
    /// Search documents in the database.
    ///
    /// nidus search "キーワード"
    Search {
        /// Search query
        query: String,
        /// Output results as JSON
        #[arg(long)]
        json: bool,
    },
}

#[tokio::main]
async fn main() -> Result<()> {
    let cli = Cli::parse();

    match cli.command {
        Commands::Init => cmd_init().await?,
        Commands::Add { files } => cmd_add(files).await?,
        Commands::Search { query, json } => cmd_search(query, json).await?,
    }

    Ok(())
}

async fn cmd_init() -> Result<()> {
    let config = Config::load();
    download_model(&config.model_dir).await?;
    println!("Model ready at {}", config.model_dir.display());
    Ok(())
}

async fn cmd_add(files: Vec<PathBuf>) -> Result<()> {
    let config = Config::load();

    let db = db::connect(&config.db_path).await?;
    let model = EmbeddingModel::load(&config.model_dir)?;

    update_files_in_db(&files, &db, &model).await?;

    Ok(())
}

async fn cmd_search(query: String, output_json: bool) -> Result<()> {
    let config = Config::load();

    let db = db::connect(&config.db_path).await?;
    let model = EmbeddingModel::load(&config.model_dir)?;

    let results = search_docs(
        &query,
        &db,
        &model,
        config.search_limit,
        config.search_rrf_k,
        config.search_adjacent_window,
    )
    .await?;

    if output_json {
        display_json(&results);
    } else {
        display_simple(&results);
    }

    Ok(())
}

fn display_simple(results: &[SearchResult]) {
    println!(
        "{:<8} | {:<10} | {:<15} | {}",
        "Score", "Method", "Source", "Text"
    );
    println!("{}", "-".repeat(80));

    for res in results {
        let score = format!("{:.4}", res.score);
        let method = res.method.to_string();
        let source = if res.source.len() > 15 {
            format!("{}..", &res.source[..13])
        } else {
            res.source.clone()
        };
        let text_flat = res.text.replace('\n', " ");
        let text = if text_flat.chars().count() > 50 {
            let truncated: String = text_flat.chars().take(50).collect();
            format!("{}...", truncated)
        } else {
            text_flat
        };
        println!("{:<8} | {:<10} | {:<15} | {}", score, method, source, text);
    }
}

fn display_json(results: &[SearchResult]) {
    let output: Vec<serde_json::Value> = results
        .iter()
        .map(|res| {
            serde_json::json!({
                "score": res.score,
                "method": res.method.to_string(),
                "source": res.source,
                "chunk_id": res.chunk_id,
                "text": res.text,
            })
        })
        .collect();
    println!("{}", serde_json::to_string_pretty(&output).unwrap());
}
