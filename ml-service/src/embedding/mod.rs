mod model;

pub use model::EmbeddingModel;

use anyhow::Result;
use once_cell::sync::OnceCell;
use parking_lot::RwLock;
use std::sync::Arc;

use crate::config::ModelsConfig;

static EMBEDDING_MODEL: OnceCell<Arc<RwLock<EmbeddingModel>>> = OnceCell::new();

/// Initialize the global embedding model
pub fn init_embedding_model(config: &ModelsConfig) -> Result<()> {
    let model = EmbeddingModel::new(config)?;
    EMBEDDING_MODEL
        .set(Arc::new(RwLock::new(model)))
        .map_err(|_| anyhow::anyhow!("Embedding model already initialized"))?;
    Ok(())
}

/// Get the global embedding model
pub fn get_embedding_model() -> Option<Arc<RwLock<EmbeddingModel>>> {
    EMBEDDING_MODEL.get().cloned()
}

/// Generate embedding for a single text
pub async fn embed(text: &str) -> Result<Vec<f32>> {
    let model = get_embedding_model()
        .ok_or_else(|| anyhow::anyhow!("Embedding model not initialized"))?;

    let model = model.read();
    model.embed(text)
}

/// Generate embeddings for multiple texts
pub async fn embed_batch(texts: &[String]) -> Result<Vec<Vec<f32>>> {
    let model = get_embedding_model()
        .ok_or_else(|| anyhow::anyhow!("Embedding model not initialized"))?;

    let model = model.read();
    model.embed_batch(texts)
}

/// Get embedding dimensions
pub fn get_dimensions() -> usize {
    get_embedding_model()
        .map(|m| m.read().dimensions())
        .unwrap_or(384) // Default for MiniLM
}
