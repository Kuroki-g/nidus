pub mod connection;
pub mod drop;
pub mod search;
pub mod update;

pub use connection::{
    connect, doc_chunk_schema, doc_meta_schema, DEFAULT_TABLE_DOC_CHUNK, DEFAULT_TABLE_DOC_META,
};
pub use drop::drop_files_in_db;
pub use search::{search_docs, SearchMethod, SearchResult};
pub use update::{collect_files, file_hash, update_files_in_db};
