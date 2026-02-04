use anyhow::{Context, Result};
use ndarray::{Array1, Array2, Axis};
use ort::{inputs, GraphOptimizationLevel, Session};
use std::path::Path;
use tokenizers::Tokenizer;
use tracing::{debug, info};

use crate::config::ModelsConfig;

const MAX_LENGTH: usize = 512;

pub struct EmbeddingModel {
    session: Session,
    tokenizer: Tokenizer,
    model_name: String,
    dim: usize,
}

impl EmbeddingModel {
    pub fn new(config: &ModelsConfig) -> Result<Self> {
        let model_path = Path::new(&config.models_dir).join(&config.embedding_model);

        info!(
            "Loading embedding model from {:?}",
            model_path
        );

        // Load ONNX model
        let model_file = model_path.join("model.onnx");
        let session = Session::builder()?
            .with_optimization_level(GraphOptimizationLevel::Level3)?
            .with_intra_threads(4)?
            .commit_from_file(&model_file)
            .context("Failed to load ONNX model")?;

        // Load tokenizer
        let tokenizer_file = model_path.join("tokenizer.json");
        let tokenizer = Tokenizer::from_file(&tokenizer_file)
            .map_err(|e| anyhow::anyhow!("Failed to load tokenizer: {}", e))?;

        // Determine embedding dimensions from model output
        let dim = session
            .outputs
            .first()
            .and_then(|o| o.output_type.tensor_dimensions())
            .and_then(|dims| dims.last().copied())
            .unwrap_or(384) as usize;

        info!(
            "Embedding model loaded: {} (dim={})",
            config.embedding_model, dim
        );

        Ok(Self {
            session,
            tokenizer,
            model_name: config.embedding_model.clone(),
            dim,
        })
    }

    pub fn dimensions(&self) -> usize {
        self.dim
    }

    pub fn model_name(&self) -> &str {
        &self.model_name
    }

    pub fn embed(&self, text: &str) -> Result<Vec<f32>> {
        let embeddings = self.embed_batch(&[text.to_string()])?;
        embeddings
            .into_iter()
            .next()
            .ok_or_else(|| anyhow::anyhow!("No embedding generated"))
    }

    pub fn embed_batch(&self, texts: &[String]) -> Result<Vec<Vec<f32>>> {
        if texts.is_empty() {
            return Ok(vec![]);
        }

        debug!("Embedding batch of {} texts", texts.len());

        // Tokenize all texts
        let encodings = self
            .tokenizer
            .encode_batch(texts.to_vec(), true)
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
        let input_ids =
            Array2::from_shape_vec((batch_size, max_len), input_ids)?;
        let attention_mask =
            Array2::from_shape_vec((batch_size, max_len), attention_mask)?;
        let token_type_ids =
            Array2::from_shape_vec((batch_size, max_len), token_type_ids)?;

        // Run inference
        let outputs = self.session.run(inputs![
            "input_ids" => input_ids.view(),
            "attention_mask" => attention_mask.view(),
            "token_type_ids" => token_type_ids.view(),
        ]?)?;

        // Extract embeddings (last_hidden_state or sentence_embedding)
        let output = outputs
            .get("last_hidden_state")
            .or_else(|| outputs.get("sentence_embedding"))
            .ok_or_else(|| anyhow::anyhow!("No embedding output found"))?;

        let embeddings: ort::Value = output.try_extract_tensor::<f32>()?;
        let embeddings = embeddings.view();

        // Mean pooling over sequence dimension
        let mut result = Vec::with_capacity(batch_size);

        for i in 0..batch_size {
            let seq_len = encodings[i].get_ids().len().min(max_len);
            let mut embedding = vec![0.0f32; self.dim];

            // Mean pooling
            for j in 0..seq_len {
                for k in 0..self.dim {
                    embedding[k] += embeddings[[i, j, k]];
                }
            }

            // Normalize
            let norm: f32 = embedding.iter().map(|x| x * x).sum::<f32>().sqrt();
            if norm > 0.0 {
                for x in &mut embedding {
                    *x /= norm;
                }
            }

            // Also divide by sequence length for mean
            for x in &mut embedding {
                *x /= seq_len as f32;
            }

            result.push(embedding);
        }

        Ok(result)
    }
}

/// Mean pooling implementation
fn mean_pooling(
    token_embeddings: &Array2<f32>,
    attention_mask: &Array1<i64>,
) -> Array1<f32> {
    let mask = attention_mask.mapv(|x| x as f32);
    let mask_expanded = mask
        .insert_axis(Axis(1))
        .broadcast(token_embeddings.dim())
        .unwrap()
        .to_owned();

    let sum = (token_embeddings * &mask_expanded).sum_axis(Axis(0));
    let count = mask.sum().max(1.0);

    sum / count
}

/// Normalize embedding to unit length
fn normalize(embedding: &mut [f32]) {
    let norm: f32 = embedding.iter().map(|x| x * x).sum::<f32>().sqrt();
    if norm > 0.0 {
        for x in embedding.iter_mut() {
            *x /= norm;
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_normalize() {
        let mut v = vec![3.0, 4.0];
        normalize(&mut v);
        assert!((v[0] - 0.6).abs() < 0.001);
        assert!((v[1] - 0.8).abs() < 0.001);
    }
}
