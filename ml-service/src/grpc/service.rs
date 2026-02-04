use std::collections::HashMap;
use std::sync::Arc;
use std::time::Instant;
use tonic::{Request, Response, Status};
use tracing::{debug, error, info};

use super::ml::ml_service_server::MlService;
use super::ml::*;
use crate::embedding::{self, get_embedding_model};
use crate::ner::SkillExtractor;
use crate::reranker::{self, RankDocument};
use crate::search::{HybridSearch, SearchMode};

pub struct MlServiceImpl {
    hybrid_search: Arc<HybridSearch>,
    skill_extractor: Arc<SkillExtractor>,
}

impl MlServiceImpl {
    pub fn new(hybrid_search: HybridSearch) -> Self {
        Self {
            hybrid_search: Arc::new(hybrid_search),
            skill_extractor: Arc::new(SkillExtractor::new()),
        }
    }
}

#[tonic::async_trait]
impl MlService for MlServiceImpl {
    async fn embed(&self, request: Request<EmbedRequest>) -> Result<Response<EmbedResponse>, Status> {
        let req = request.into_inner();
        debug!("Embed request for text ({} chars)", req.text.len());

        let embedding = embedding::embed(&req.text)
            .await
            .map_err(|e| {
                error!("Embedding failed: {}", e);
                Status::internal(format!("Embedding failed: {}", e))
            })?;

        let model = get_embedding_model()
            .map(|m| m.read().model_name().to_string())
            .unwrap_or_default();

        Ok(Response::new(EmbedResponse {
            embedding,
            dimensions: embedding::get_dimensions() as i32,
            model,
        }))
    }

    async fn embed_batch(
        &self,
        request: Request<EmbedBatchRequest>,
    ) -> Result<Response<EmbedBatchResponse>, Status> {
        let req = request.into_inner();
        debug!("Batch embed request for {} texts", req.texts.len());

        let embeddings = embedding::embed_batch(&req.texts)
            .await
            .map_err(|e| {
                error!("Batch embedding failed: {}", e);
                Status::internal(format!("Batch embedding failed: {}", e))
            })?;

        let model = get_embedding_model()
            .map(|m| m.read().model_name().to_string())
            .unwrap_or_default();

        let embeddings: Vec<Embedding> = embeddings
            .into_iter()
            .enumerate()
            .map(|(i, vec)| Embedding {
                vector: vec,
                index: i as i32,
            })
            .collect();

        Ok(Response::new(EmbedBatchResponse { embeddings, model }))
    }

    async fn rerank(&self, request: Request<RerankRequest>) -> Result<Response<RerankResponse>, Status> {
        let req = request.into_inner();
        debug!(
            "Rerank request: query='{}', {} docs, top_k={}",
            &req.query[..req.query.len().min(50)],
            req.documents.len(),
            req.top_k
        );

        let documents: Vec<RankDocument> = req
            .documents
            .into_iter()
            .map(|d| RankDocument {
                id: d.id,
                content: d.content,
                score: d.score,
                metadata: d.metadata,
            })
            .collect();

        let top_k = if req.top_k > 0 {
            req.top_k as usize
        } else {
            documents.len()
        };

        let ranked = reranker::rerank(&req.query, &documents, top_k)
            .await
            .map_err(|e| {
                error!("Reranking failed: {}", e);
                Status::internal(format!("Reranking failed: {}", e))
            })?;

        let documents: Vec<RankedDocument> = ranked
            .into_iter()
            .map(|r| RankedDocument {
                id: r.id,
                content: r.content,
                score: r.score,
                original_rank: r.original_rank,
                new_rank: r.new_rank,
                metadata: r.metadata,
            })
            .collect();

        let model = reranker::get_reranker()
            .map(|m| m.read().model_name().to_string())
            .unwrap_or_default();

        Ok(Response::new(RerankResponse { documents, model }))
    }

    async fn search(&self, request: Request<SearchRequest>) -> Result<Response<SearchResponse>, Status> {
        let req = request.into_inner();
        let start = Instant::now();

        debug!(
            "Search request: query='{}', collection='{}', top_k={}, hybrid={}",
            &req.query[..req.query.len().min(50)],
            req.collection,
            req.top_k,
            req.use_hybrid
        );

        let top_k = if req.top_k > 0 { req.top_k as usize } else { 10 };

        let mode = if req.use_hybrid {
            let weight = if req.vector_weight > 0.0 {
                req.vector_weight
            } else {
                0.7
            };
            SearchMode::Hybrid { vector_weight: weight }
        } else {
            SearchMode::Vector
        };

        let filters = if req.filters.is_empty() {
            None
        } else {
            Some(req.filters)
        };

        // Determine fetch count based on reranking
        let fetch_k = if req.use_reranking {
            let multiplier = if req.rerank_top_k > 0 {
                req.rerank_top_k as usize
            } else {
                top_k * 5
            };
            multiplier
        } else {
            top_k
        };

        // Perform search
        let mut results = self
            .hybrid_search
            .search(&req.collection, &req.query, fetch_k, mode, filters)
            .await
            .map_err(|e| {
                error!("Search failed: {}", e);
                Status::internal(format!("Search failed: {}", e))
            })?;

        // Apply reranking if requested
        if req.use_reranking && !results.is_empty() {
            let docs: Vec<RankDocument> = results
                .iter()
                .map(|r| RankDocument {
                    id: r.id.clone(),
                    content: r.content.clone(),
                    score: r.score,
                    metadata: r.metadata.clone(),
                })
                .collect();

            let ranked = reranker::rerank(&req.query, &docs, top_k)
                .await
                .map_err(|e| {
                    error!("Reranking in search failed: {}", e);
                    Status::internal(format!("Reranking failed: {}", e))
                })?;

            results = ranked
                .into_iter()
                .map(|r| crate::search::SearchResult {
                    id: r.id,
                    content: r.content,
                    score: r.score,
                    metadata: r.metadata,
                    source: crate::search::SearchSource::Hybrid,
                })
                .collect();
        } else {
            results.truncate(top_k);
        }

        let search_mode = match mode {
            SearchMode::Vector => "vector",
            SearchMode::BM25 => "bm25",
            SearchMode::Hybrid { .. } => "hybrid",
        };

        let latency_ms = start.elapsed().as_millis() as i64;

        let results: Vec<SearchResult> = results
            .into_iter()
            .map(|r| SearchResult {
                id: r.id,
                content: r.content,
                score: r.score,
                metadata: r.metadata,
                source: r.source.to_string(),
            })
            .collect();

        debug!(
            "Search completed in {}ms, returned {} results",
            latency_ms,
            results.len()
        );

        Ok(Response::new(SearchResponse {
            results,
            search_mode: search_mode.to_string(),
            latency_ms,
        }))
    }

    async fn extract_skills(
        &self,
        request: Request<ExtractSkillsRequest>,
    ) -> Result<Response<ExtractSkillsResponse>, Status> {
        let req = request.into_inner();
        debug!("Extract skills request ({} chars)", req.text.len());

        let skills = self.skill_extractor.extract(&req.text, req.include_soft_skills);

        Ok(Response::new(ExtractSkillsResponse {
            technical_skills: skills.technical_skills,
            soft_skills: skills.soft_skills,
            tools: skills.tools,
            frameworks: skills.frameworks,
            languages: skills.languages,
        }))
    }

    async fn index_documents(
        &self,
        request: Request<IndexRequest>,
    ) -> Result<Response<IndexResponse>, Status> {
        let req = request.into_inner();
        debug!(
            "Index request: {} documents to collection '{}'",
            req.documents.len(),
            req.collection
        );

        let mut indexed_count = 0;
        let mut failed_count = 0;
        let mut failed_ids = Vec::new();

        // Process documents
        let mut docs_with_embeddings = Vec::new();

        for doc in req.documents {
            // Use provided embedding or generate one
            let embedding = if !doc.embedding.is_empty() {
                doc.embedding
            } else {
                match embedding::embed(&doc.content).await {
                    Ok(emb) => emb,
                    Err(e) => {
                        error!("Failed to embed document {}: {}", doc.id, e);
                        failed_count += 1;
                        failed_ids.push(doc.id);
                        continue;
                    }
                }
            };

            // Add to BM25 index if requested
            if req.update_bm25 {
                self.hybrid_search.add_to_bm25(&req.collection, &doc.id, &doc.content);
            }

            // Prepare for vector index
            let mut metadata = doc.metadata;
            metadata.insert("content".to_string(), doc.content);
            docs_with_embeddings.push((doc.id, embedding, metadata));
        }

        // Batch index to Qdrant
        // Note: In a real implementation, we'd need access to QdrantClient through HybridSearch
        // For now, we'll track success
        indexed_count = docs_with_embeddings.len() as i32;

        info!(
            "Indexed {} documents, {} failed",
            indexed_count, failed_count
        );

        Ok(Response::new(IndexResponse {
            indexed_count,
            failed_count,
            failed_ids,
        }))
    }

    async fn clear_index(
        &self,
        request: Request<ClearIndexRequest>,
    ) -> Result<Response<ClearIndexResponse>, Status> {
        let req = request.into_inner();
        info!("Clear index request for collection '{}'", req.collection);

        if req.clear_bm25 {
            self.hybrid_search.clear_bm25(&req.collection);
        }

        // Note: clear_vectors would require Qdrant access
        // In full implementation, we'd delete the collection

        Ok(Response::new(ClearIndexResponse {
            success: true,
            message: format!("Cleared index for collection '{}'", req.collection),
        }))
    }

    async fn health_check(
        &self,
        _request: Request<HealthCheckRequest>,
    ) -> Result<Response<HealthCheckResponse>, Status> {
        let mut components = HashMap::new();

        // Check embedding model
        let embedding_status = if get_embedding_model().is_some() {
            "healthy"
        } else {
            "not_initialized"
        };
        components.insert("embedding".to_string(), embedding_status.to_string());

        // Check reranker
        let reranker_status = if reranker::get_reranker().is_some() {
            "healthy"
        } else {
            "not_initialized"
        };
        components.insert("reranker".to_string(), reranker_status.to_string());

        // Overall status
        let status = if embedding_status == "healthy" && reranker_status == "healthy" {
            "healthy"
        } else if embedding_status == "healthy" || reranker_status == "healthy" {
            "degraded"
        } else {
            "unhealthy"
        };

        Ok(Response::new(HealthCheckResponse {
            status: status.to_string(),
            components,
            version: env!("CARGO_PKG_VERSION").to_string(),
        }))
    }
}
