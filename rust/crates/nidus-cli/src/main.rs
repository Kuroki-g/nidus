use std::path::PathBuf;

use anyhow::Result;
use clap::{Parser, Subcommand};
use nidus_core::{
    config::Config,
    db::{
        self, drop::drop_files_in_db, list::list_docs_in_db, reindex::reindex_db,
        search::search_docs, status::db_status, update::update_files_in_db, SearchResult,
    },
    embedding::EmbeddingModel,
    init::download_model,
    watch::watch_directories,
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
    /// Delete existing document information from the database.
    Drop {
        /// File(s) or directory to be removed
        #[arg(short = 'f', long = "file", required = true, value_name = "PATH")]
        files: Vec<PathBuf>,
    },
    /// List documents registered in the database.
    ///
    /// nidus list [keyword]
    List {
        /// Filter by keyword
        keyword: Option<String>,
    },
    /// Re-index all registered documents from scratch.
    ///
    /// nidus reindex [--dry-run]
    Reindex {
        /// Show what would be reindexed without making any changes
        #[arg(long)]
        dry_run: bool,
    },
    /// Show metadata for the database.
    ///
    /// nidus status
    Status,
    /// Watch directories and auto-index on file changes.
    ///
    /// nidus watch -f ./docs -f ./notes
    Watch {
        /// Directory (or file) to watch
        #[arg(short = 'f', long = "file", required = true, value_name = "PATH")]
        dirs: Vec<PathBuf>,
    },
}

#[tokio::main]
async fn main() -> Result<()> {
    tracing_subscriber::fmt()
        .with_max_level(tracing::Level::INFO)
        .with_target(false)
        .init();

    let cli = Cli::parse();

    match cli.command {
        Commands::Init => cmd_init().await?,
        Commands::Add { files } => cmd_add(files).await?,
        Commands::Search { query, json } => cmd_search(query, json).await?,
        Commands::Drop { files } => cmd_drop(files).await?,
        Commands::List { keyword } => cmd_list(keyword).await?,
        Commands::Reindex { dry_run } => cmd_reindex(dry_run).await?,
        Commands::Status => cmd_status().await?,
        Commands::Watch { dirs } => cmd_watch(dirs).await?,
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

async fn cmd_status() -> Result<()> {
    let config = Config::load();
    let db_path_str = config.db_path.to_string_lossy().into_owned();
    let db = db::connect(&config.db_path).await?;

    let status = db_status(&db, &db_path_str).await?;

    println!("\n--- Database Status ---");
    println!("Path:  {}", status.db_path);
    println!("Total: {} table(s)", status.tables.len());
    println!("{}", "-".repeat(80));
    println!(
        "{:<20} | {:>8} | {:>7} | {}",
        "Table Name", "Rows", "Version", "Fields"
    );
    println!("{}", "-".repeat(80));

    for t in &status.tables {
        let fields = t.fields.join(", ");
        let display_fields = if fields.len() > 40 {
            format!("{}...", &fields[..40])
        } else {
            fields
        };
        println!(
            "{:<20} | {:>8} | {:>7} | {}",
            t.name, t.row_count, t.version, display_fields
        );
    }
    println!("{}", "-".repeat(80));

    Ok(())
}

async fn cmd_reindex(dry_run: bool) -> Result<()> {
    let config = Config::load();
    let db = db::connect(&config.db_path).await?;

    let model = if dry_run {
        None
    } else {
        Some(EmbeddingModel::load(&config.model_dir)?)
    };

    let count = reindex_db(&db, model.as_ref(), dry_run).await?;
    if count > 0 && !dry_run {
        println!("Reindexed {} document(s).", count);
    }

    Ok(())
}

async fn cmd_list(keyword: Option<String>) -> Result<()> {
    let config = Config::load();
    let db = db::connect(&config.db_path).await?;

    let entries = list_docs_in_db(&db, keyword.as_deref(), config.search_limit).await?;

    if entries.is_empty() {
        println!("No documents registered.");
        return Ok(());
    }

    println!("{:<60} | {}", "Source", "Name");
    println!("{}", "-".repeat(80));
    for entry in &entries {
        println!("{:<60} | {}", entry.source, entry.doc_name);
    }

    Ok(())
}

async fn cmd_drop(files: Vec<PathBuf>) -> Result<()> {
    let config = Config::load();
    let db = db::connect(&config.db_path).await?;
    drop_files_in_db(&files, &db).await?;
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

async fn cmd_watch(dirs: Vec<PathBuf>) -> Result<()> {
    let config = Config::load();
    let db = db::connect(&config.db_path).await?;
    let model = EmbeddingModel::load(&config.model_dir)?;
    watch_directories(&dirs, &db, &model).await?;
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
