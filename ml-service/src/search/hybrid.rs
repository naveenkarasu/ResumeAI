use anyhow::Result;
use std::collections::HashMap;
use tracing::debug;

use super::{BM25Index, QdrantClient, SearchResult, SearchSource};
use crate::embedding;

/// Search mode configuration
#[derive(Debug, Clone, Copy)]
pub enum SearchMode {
    Vector,
    BM25,
    Hybrid { vector_weight: f32 },
}

impl Default for SearchMode {
    fn default() -> Self {
        SearchMode::Hybrid { vector_weight: 0.7 }
    }
}

/// Hybrid search combining vector and BM25 with RRF fusion
pub struct HybridSearch {
    qdrant: QdrantClient,
    bm25_indices: parking_lot::RwLock<HashMap<String, BM25Index>>,
    rrf_k: usize,
}

impl HybridSearch {
    pub fn new(qdrant: QdrantClient, rrf_k: usize) -> Self {
        Self {
            qdrant,
            bm25_indices: parking_lot::RwLock::new(HashMap::new()),
            rrf_k,
        }
    }

    /// Get or create BM25 index for a collection
    pub fn get_or_create_bm25(&self, collection: &str) -> &Self {
        let mut indices = self.bm25_indices.write();
        indices
            .entry(collection.to_string())
            .or_insert_with(BM25Index::new);
        self
    }

    /// Add document to BM25 index
    pub fn add_to_bm25(&self, collection: &str, id: &str, content: &str) {
        let mut indices = self.bm25_indices.write();
        let index = indices
            .entry(collection.to_string())
            .or_insert_with(BM25Index::new);
        index.add_document(id, content);
    }

    /// Clear BM25 index for a collection
    pub fn clear_bm25(&self, collection: &str) {
        let mut indices = self.bm25_indices.write();
        if let Some(index) = indices.get_mut(collection) {
            index.clear();
        }
    }

    /// Perform search with the specified mode
    pub async fn search(
        &self,
        collection: &str,
        query: &str,
        top_k: usize,
        mode: SearchMode,
        filters: Option<HashMap<String, String>>,
    ) -> Result<Vec<SearchResult>> {
        match mode {
            SearchMode::Vector => {
                self.vector_search(collection, query, top_k, filters).await
            }
            SearchMode::BM25 => {
                self.bm25_search(collection, query, top_k)
            }
            SearchMode::Hybrid { vector_weight } => {
                self.hybrid_search(collection, query, top_k, vector_weight, filters)
                    .await
            }
        }
    }

    /// Vector-only search
    async fn vector_search(
        &self,
        collection: &str,
        query: &str,
        top_k: usize,
        filters: Option<HashMap<String, String>>,
    ) -> Result<Vec<SearchResult>> {
        debug!("Performing vector search for collection: {}", collection);

        // Generate query embedding
        let query_embedding = embedding::embed(query).await?;

        // Search Qdrant
        self.qdrant
            .search(collection, query_embedding, top_k as u64, filters)
            .await
    }

    /// BM25-only search
    fn bm25_search(
        &self,
        collection: &str,
        query: &str,
        top_k: usize,
    ) -> Result<Vec<SearchResult>> {
        debug!("Performing BM25 search for collection: {}", collection);

        let indices = self.bm25_indices.read();
        let index = indices
            .get(collection)
            .ok_or_else(|| anyhow::anyhow!("BM25 index not found for collection: {}", collection))?;

        let bm25_results = index.search(query, top_k);

        let results: Vec<SearchResult> = bm25_results
            .into_iter()
            .map(|(id, score)| {
                let content = index.get_document(&id).unwrap_or_default();
                SearchResult {
                    id,
                    content,
                    score,
                    metadata: HashMap::new(),
                    source: SearchSource::BM25,
                }
            })
            .collect();

        Ok(results)
    }

    /// Hybrid search with RRF fusion
    async fn hybrid_search(
        &self,
        collection: &str,
        query: &str,
        top_k: usize,
        vector_weight: f32,
        filters: Option<HashMap<String, String>>,
    ) -> Result<Vec<SearchResult>> {
        debug!(
            "Performing hybrid search for collection: {} (vector_weight={})",
            collection, vector_weight
        );

        // Fetch more results for fusion
        let fetch_k = top_k * 3;

        // Run both searches concurrently
        let (vector_results, bm25_results) = tokio::join!(
            self.vector_search(collection, query, fetch_k, filters),
            async { self.bm25_search(collection, query, fetch_k) }
        );

        let vector_results = vector_results.unwrap_or_default();
        let bm25_results = bm25_results.unwrap_or_default();

        // Apply RRF fusion
        let fused = self.rrf_fusion(
            vector_results,
            bm25_results,
            vector_weight,
            top_k,
        );

        Ok(fused)
    }

    /// Reciprocal Rank Fusion to combine results
    fn rrf_fusion(
        &self,
        vector_results: Vec<SearchResult>,
        bm25_results: Vec<SearchResult>,
        vector_weight: f32,
        top_k: usize,
    ) -> Vec<SearchResult> {
        let bm25_weight = 1.0 - vector_weight;
        let k = self.rrf_k as f32;

        // Build score maps
        let mut scores: HashMap<String, (f32, Option<SearchResult>)> = HashMap::new();

        // Add vector results with RRF score
        for (rank, result) in vector_results.into_iter().enumerate() {
            let rrf_score = vector_weight * (1.0 / (k + rank as f32 + 1.0));
            scores
                .entry(result.id.clone())
                .and_modify(|(score, _)| *score += rrf_score)
                .or_insert((rrf_score, Some(result)));
        }

        // Add BM25 results with RRF score
        for (rank, result) in bm25_results.into_iter().enumerate() {
            let rrf_score = bm25_weight * (1.0 / (k + rank as f32 + 1.0));
            scores
                .entry(result.id.clone())
                .and_modify(|(score, existing)| {
                    *score += rrf_score;
                    // Keep the more complete result
                    if existing.is_none() {
                        *existing = Some(result.clone());
                    }
                })
                .or_insert((rrf_score, Some(result)));
        }

        // Sort by fused score and take top_k
        let mut results: Vec<(String, f32, SearchResult)> = scores
            .into_iter()
            .filter_map(|(id, (score, result))| {
                result.map(|mut r| {
                    r.score = score;
                    r.source = SearchSource::Hybrid;
                    (id, score, r)
                })
            })
            .collect();

        results.sort_by(|a, b| b.1.partial_cmp(&a.1).unwrap_or(std::cmp::Ordering::Equal));
        results.truncate(top_k);

        results.into_iter().map(|(_, _, r)| r).collect()
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_search_mode_default() {
        let mode = SearchMode::default();
        match mode {
            SearchMode::Hybrid { vector_weight } => {
                assert!((vector_weight - 0.7).abs() < 0.001);
            }
            _ => panic!("Expected hybrid mode as default"),
        }
    }
}
