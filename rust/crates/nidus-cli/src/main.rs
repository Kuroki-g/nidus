use std::path::PathBuf;

use anyhow::Result;
use clap::{Parser, Subcommand};
use nidus_core::{
    config::Config,
    db::{self, update::update_files_in_db},
    embedding::EmbeddingModel,
};

#[derive(Parser)]
#[command(name = "nidus", about = "Japanese local document search engine")]
struct Cli {
    #[command(subcommand)]
    command: Commands,
}

#[derive(Subcommand)]
enum Commands {
    /// Add or update documents in the database.
    ///
    /// nidus add -f update-target.txt -f add-target-dir/
    Add {
        /// File(s) or directory to be added or updated
        #[arg(short = 'f', long = "file", required = true, value_name = "PATH")]
        files: Vec<PathBuf>,
    },
}

#[tokio::main]
async fn main() -> Result<()> {
    let cli = Cli::parse();

    match cli.command {
        Commands::Add { files } => cmd_add(files).await?,
    }

    Ok(())
}

async fn cmd_add(files: Vec<PathBuf>) -> Result<()> {
    let config = Config::load();

    let db = db::connect(&config.db_path).await?;
    let model = EmbeddingModel::load(&config.model_dir)?;

    update_files_in_db(&files, &db, &model).await?;

    Ok(())
}
