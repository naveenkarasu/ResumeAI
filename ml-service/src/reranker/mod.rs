mod model;

pub use model::Reranker;

use anyhow::Result;
use once_cell::sync::OnceCell;
use parking_lot::RwLock;
use std::sync::Arc;

use crate::config::ModelsConfig;

static RERANKER: OnceCell<Arc<RwLock<Reranker>>> = OnceCell::new();

/// Initialize the global reranker model
pub fn init_reranker(config: &ModelsConfig) -> Result<()> {
    let model = Reranker::new(config)?;
    RERANKER
        .set(Arc::new(RwLock::new(model)))
        .map_err(|_| anyhow::anyhow!("Reranker already initialized"))?;
    Ok(())
}

/// Get the global reranker
pub fn get_reranker() -> Option<Arc<RwLock<Reranker>>> {
    RERANKER.get().cloned()
}

/// Rerank documents given a query
pub async fn rerank(
    query: &str,
    documents: &[RankDocument],
    top_k: usize,
) -> Result<Vec<RankedDocument>> {
    let model = get_reranker()
        .ok_or_else(|| anyhow::anyhow!("Reranker not initialized"))?;

    let model = model.read();
    model.rerank(query, documents, top_k)
}

#[derive(Debug, Clone)]
pub struct RankDocument {
    pub id: String,
    pub content: String,
    pub score: f32,
    pub metadata: std::collections::HashMap<String, String>,
}

#[derive(Debug, Clone)]
pub struct RankedDocument {
    pub id: String,
    pub content: String,
    pub score: f32,
    pub original_rank: i32,
    pub new_rank: i32,
    pub metadata: std::collections::HashMap<String, String>,
}
