mod bm25;
mod hybrid;
mod qdrant;

pub use bm25::BM25Index;
pub use hybrid::{HybridSearch, SearchMode};
pub use qdrant::QdrantClient;

use std::collections::HashMap;

#[derive(Debug, Clone)]
pub struct SearchResult {
    pub id: String,
    pub content: String,
    pub score: f32,
    pub metadata: HashMap<String, String>,
    pub source: SearchSource,
}

#[derive(Debug, Clone, Copy, PartialEq)]
pub enum SearchSource {
    Vector,
    BM25,
    Hybrid,
}

impl std::fmt::Display for SearchSource {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        match self {
            SearchSource::Vector => write!(f, "vector"),
            SearchSource::BM25 => write!(f, "bm25"),
            SearchSource::Hybrid => write!(f, "hybrid"),
        }
    }
}
