use std::path::PathBuf;

#[derive(Debug, Clone)]
pub struct Config {
    pub db_path: PathBuf,
    pub model_dir: PathBuf,
    pub table_name: String,
    pub search_limit: usize,
    pub search_rrf_k: usize,
    pub search_adjacent_window: usize,
}

impl Config {
    pub fn load() -> Self {
        // .env があれば読み込む（なければ無視）
        let _ = dotenvy::dotenv();

        let cache_dir = cache_dir();
        let db_path = env_path("DB_PATH").unwrap_or_else(|| cache_dir.join(".lancedb"));
        let model_dir = env_path("MODEL_DIR").unwrap_or_else(|| cache_dir.join("model"));

        Self {
            db_path,
            model_dir,
            table_name: env_str("TABLE_NAME", "docs"),
            search_limit: env_usize("SEARCH_LIMIT", 5),
            search_rrf_k: env_usize("SEARCH_RRF_K", 60),
            search_adjacent_window: env_usize("SEARCH_ADJACENT_WINDOW", 1),
        }
    }
}

/// XDG_CACHE_HOME / "nidus" または ~/.cache/nidus
fn cache_dir() -> PathBuf {
    if let Ok(xdg) = std::env::var("XDG_CACHE_HOME") {
        if !xdg.is_empty() {
            return PathBuf::from(xdg).join("nidus");
        }
    }
    dirs::cache_dir()
        .unwrap_or_else(|| PathBuf::from(".cache"))
        .join("nidus")
}

fn env_str(key: &str, default: &str) -> String {
    std::env::var(key).unwrap_or_else(|_| default.to_string())
}

fn env_usize(key: &str, default: usize) -> usize {
    std::env::var(key)
        .ok()
        .and_then(|v| v.parse().ok())
        .unwrap_or(default)
}

fn env_path(key: &str) -> Option<PathBuf> {
    std::env::var(key).ok().map(PathBuf::from)
}
