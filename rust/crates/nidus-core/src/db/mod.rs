pub mod connection;
pub mod drop;
pub mod list;
pub mod reindex;
pub mod search;
pub mod status;
pub mod update;

pub use connection::{
    connect, doc_chunk_schema, doc_meta_schema, DEFAULT_TABLE_DOC_CHUNK, DEFAULT_TABLE_DOC_META,
};
pub use drop::drop_files_in_db;
pub use list::{list_docs_in_db, DocListEntry};
pub use reindex::reindex_db;
pub use search::{search_docs, SearchMethod, SearchResult};
pub use status::{db_status, DbStatus, TableInfo};
pub use update::{collect_files, file_hash, update_files_in_db};
