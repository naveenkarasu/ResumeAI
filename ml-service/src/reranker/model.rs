use anyhow::{Context, Result};
use ndarray::Array2;
use ort::{inputs, GraphOptimizationLevel, Session};
use std::path::Path;
use tokenizers::Tokenizer;
use tracing::{debug, info};

use crate::config::ModelsConfig;

use super::{RankDocument, RankedDocument};

const MAX_LENGTH: usize = 512;

pub struct Reranker {
    session: Session,
    tokenizer: Tokenizer,
    model_name: String,
}

impl Reranker {
    pub fn new(config: &ModelsConfig) -> Result<Self> {
        let model_path = Path::new(&config.models_dir).join(&config.reranker_model);

        info!("Loading reranker model from {:?}", model_path);

        // Load ONNX model
        let model_file = model_path.join("model.onnx");
        let session = Session::builder()?
            .with_optimization_level(GraphOptimizationLevel::Level3)?
            .with_intra_threads(4)?
            .commit_from_file(&model_file)
            .context("Failed to load reranker ONNX model")?;

        // Load tokenizer
        let tokenizer_file = model_path.join("tokenizer.json");
        let tokenizer = Tokenizer::from_file(&tokenizer_file)
            .map_err(|e| anyhow::anyhow!("Failed to load reranker tokenizer: {}", e))?;

        info!("Reranker model loaded: {}", config.reranker_model);

        Ok(Self {
            session,
            tokenizer,
            model_name: config.reranker_model.clone(),
        })
    }

    pub fn model_name(&self) -> &str {
        &self.model_name
    }

    /// Rerank documents by computing cross-encoder scores with the query
    pub fn rerank(
        &self,
        query: &str,
        documents: &[RankDocument],
        top_k: usize,
    ) -> Result<Vec<RankedDocument>> {
        if documents.is_empty() {
            return Ok(vec![]);
        }

        debug!("Reranking {} documents for query", documents.len());

        // Create query-document pairs for cross-encoder
        let pairs: Vec<String> = documents
            .iter()
            .map(|doc| format!("{} [SEP] {}", query, doc.content))
            .collect();

        // Tokenize all pairs
        let encodings = self
            .tokenizer
            .encode_batch(pairs, true)
            .map_err(|e| anyhow::anyhow!("Tokenization failed: {}", e))?;

        let batch_size = encodings.len();

        // Find max length in batch
        let max_len = encodings
            .iter()
            .map(|e| e.get_ids().len())
            .max()
            .unwrap_or(0)
            .min(MAX_LENGTH);

        // Prepare input tensors
        let mut input_ids = vec![0i64; batch_size * max_len];
        let mut attention_mask = vec![0i64; batch_size * max_len];
        let mut token_type_ids = vec![0i64; batch_size * max_len];

        for (i, encoding) in encodings.iter().enumerate() {
            let ids = encoding.get_ids();
            let mask = encoding.get_attention_mask();
            let type_ids = encoding.get_type_ids();

            let len = ids.len().min(max_len);
            for j in 0..len {
                input_ids[i * max_len + j] = ids[j] as i64;
                attention_mask[i * max_len + j] = mask[j] as i64;
                token_type_ids[i * max_len + j] = type_ids[j] as i64;
            }
        }

        // Convert to ndarray
        let input_ids = Array2::from_shape_vec((batch_size, max_len), input_ids)?;
        let attention_mask = Array2::from_shape_vec((batch_size, max_len), attention_mask)?;
        let token_type_ids = Array2::from_shape_vec((batch_size, max_len), token_type_ids)?;

        // Run inference
        let outputs = self.session.run(inputs![
            "input_ids" => input_ids.view(),
            "attention_mask" => attention_mask.view(),
            "token_type_ids" => token_type_ids.view(),
        ]?)?;

        // Extract logits - cross-encoder typically outputs a single score
        let logits = outputs
            .get("logits")
            .or_else(|| outputs.get("output"))
            .ok_or_else(|| anyhow::anyhow!("No logits output found"))?;

        let logits: ort::Value = logits.try_extract_tensor::<f32>()?;
        let logits = logits.view();

        // Extract scores and create ranked documents
        let mut scored_docs: Vec<(usize, f32)> = documents
            .iter()
            .enumerate()
            .map(|(i, _)| {
                // Cross-encoder may output shape [batch, 1] or [batch, 2]
                // For single score, take index 0; for binary, take difference or index 1
                let score = if logits.shape().len() == 2 && logits.shape()[1] >= 2 {
                    // Binary classification: use positive class score
                    logits[[i, 1]]
                } else if logits.shape().len() == 2 {
                    logits[[i, 0]]
                } else {
                    logits[[i]]
                };
                (i, score)
            })
            .collect();

        // Sort by score descending
        scored_docs.sort_by(|a, b| b.1.partial_cmp(&a.1).unwrap_or(std::cmp::Ordering::Equal));

        // Take top_k and create ranked documents
        let result: Vec<RankedDocument> = scored_docs
            .into_iter()
            .take(top_k)
            .enumerate()
            .map(|(new_rank, (original_idx, score))| {
                let doc = &documents[original_idx];
                RankedDocument {
                    id: doc.id.clone(),
                    content: doc.content.clone(),
                    score,
                    original_rank: original_idx as i32,
                    new_rank: new_rank as i32,
                    metadata: doc.metadata.clone(),
                }
            })
            .collect();

        debug!("Reranking complete, returning {} results", result.len());

        Ok(result)
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_reranker_creation_fails_without_model() {
        let config = ModelsConfig {
            embedding_model: "test".to_string(),
            reranker_model: "nonexistent".to_string(),
            models_dir: "/nonexistent".to_string(),
        };
        assert!(Reranker::new(&config).is_err());
    }
}
