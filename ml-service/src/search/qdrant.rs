use anyhow::{Context, Result};
use qdrant_client::qdrant::{
    vectors_config::Config, CreateCollection, Distance, PointStruct, SearchPoints, VectorParams,
    VectorsConfig, WithPayloadSelector, WithVectorsSelector,
};
use qdrant_client::Qdrant;
use std::collections::HashMap;
use tracing::{debug, info};
use uuid::Uuid;

use crate::config::QdrantConfig;

use super::SearchResult;

/// Qdrant vector database client
pub struct QdrantClient {
    client: Qdrant,
    collection_prefix: String,
}

impl QdrantClient {
    pub async fn new(config: &QdrantConfig) -> Result<Self> {
        let url = config.url();
        info!("Connecting to Qdrant at {}", url);

        let client = Qdrant::from_url(&url)
            .build()
            .context("Failed to create Qdrant client")?;

        Ok(Self {
            client,
            collection_prefix: config.collection_prefix.clone(),
        })
    }

    /// Get full collection name with prefix
    fn collection_name(&self, name: &str) -> String {
        format!("{}_{}", self.collection_prefix, name)
    }

    /// Ensure a collection exists with the given dimensions
    pub async fn ensure_collection(&self, name: &str, dimensions: u64) -> Result<()> {
        let collection_name = self.collection_name(name);

        // Check if collection exists
        let collections = self.client.list_collections().await?;
        let exists = collections
            .collections
            .iter()
            .any(|c| c.name == collection_name);

        if !exists {
            info!("Creating collection: {} (dim={})", collection_name, dimensions);

            self.client
                .create_collection(CreateCollection {
                    collection_name: collection_name.clone(),
                    vectors_config: Some(VectorsConfig {
                        config: Some(Config::Params(VectorParams {
                            size: dimensions,
                            distance: Distance::Cosine.into(),
                            ..Default::default()
                        })),
                    }),
                    ..Default::default()
                })
                .await
                .context("Failed to create collection")?;

            info!("Collection created: {}", collection_name);
        }

        Ok(())
    }

    /// Index documents with embeddings
    pub async fn index_documents(
        &self,
        collection: &str,
        documents: Vec<(String, Vec<f32>, HashMap<String, String>)>,
    ) -> Result<usize> {
        if documents.is_empty() {
            return Ok(0);
        }

        let collection_name = self.collection_name(collection);
        debug!("Indexing {} documents to {}", documents.len(), collection_name);

        let points: Vec<PointStruct> = documents
            .into_iter()
            .map(|(id, embedding, metadata)| {
                // Convert metadata to Qdrant payload
                let payload: HashMap<String, qdrant_client::qdrant::Value> = metadata
                    .into_iter()
                    .map(|(k, v)| {
                        (k, qdrant_client::qdrant::Value {
                            kind: Some(qdrant_client::qdrant::value::Kind::StringValue(v)),
                        })
                    })
                    .collect();

                PointStruct::new(
                    // Use UUID if id is not valid, otherwise use the id as the point ID
                    id.parse::<u64>().unwrap_or_else(|_| {
                        // Generate deterministic ID from string
                        let uuid = Uuid::new_v5(&Uuid::NAMESPACE_OID, id.as_bytes());
                        uuid.as_u128() as u64
                    }),
                    embedding,
                    payload,
                )
            })
            .collect();

        let count = points.len();

        self.client
            .upsert_points(collection_name, None, points, None)
            .await
            .context("Failed to upsert points")?;

        debug!("Indexed {} documents", count);
        Ok(count)
    }

    /// Search for similar vectors
    pub async fn search(
        &self,
        collection: &str,
        query_vector: Vec<f32>,
        top_k: u64,
        filters: Option<HashMap<String, String>>,
    ) -> Result<Vec<SearchResult>> {
        let collection_name = self.collection_name(collection);
        debug!("Searching {} for {} results", collection_name, top_k);

        // Build filter if provided
        let filter = filters.map(|f| {
            use qdrant_client::qdrant::{Condition, Filter, FieldCondition, Match, match_value::MatchValue};

            let conditions: Vec<Condition> = f
                .into_iter()
                .map(|(key, value)| {
                    Condition::field(FieldCondition {
                        key,
                        r#match: Some(Match {
                            match_value: Some(MatchValue::Keyword(value)),
                        }),
                        ..Default::default()
                    })
                })
                .collect();

            Filter {
                must: conditions,
                ..Default::default()
            }
        });

        let search_result = self
            .client
            .search_points(SearchPoints {
                collection_name,
                vector: query_vector,
                limit: top_k,
                filter,
                with_payload: Some(WithPayloadSelector {
                    selector_options: Some(
                        qdrant_client::qdrant::with_payload_selector::SelectorOptions::Enable(true),
                    ),
                }),
                with_vectors: Some(WithVectorsSelector {
                    selector_options: Some(
                        qdrant_client::qdrant::with_vectors_selector::SelectorOptions::Enable(false),
                    ),
                }),
                ..Default::default()
            })
            .await
            .context("Search failed")?;

        let results: Vec<SearchResult> = search_result
            .result
            .into_iter()
            .map(|point| {
                let metadata: HashMap<String, String> = point
                    .payload
                    .into_iter()
                    .filter_map(|(k, v)| {
                        if let Some(qdrant_client::qdrant::value::Kind::StringValue(s)) = v.kind {
                            Some((k, s))
                        } else {
                            None
                        }
                    })
                    .collect();

                let content = metadata.get("content").cloned().unwrap_or_default();
                let id = point.id.map(|id| format!("{:?}", id)).unwrap_or_default();

                SearchResult {
                    id,
                    content,
                    score: point.score,
                    metadata,
                    source: super::SearchSource::Vector,
                }
            })
            .collect();

        debug!("Found {} results", results.len());
        Ok(results)
    }

    /// Delete a collection
    pub async fn delete_collection(&self, name: &str) -> Result<()> {
        let collection_name = self.collection_name(name);
        info!("Deleting collection: {}", collection_name);

        self.client
            .delete_collection(collection_name)
            .await
            .context("Failed to delete collection")?;

        Ok(())
    }

    /// Check if Qdrant is healthy
    pub async fn health_check(&self) -> Result<bool> {
        match self.client.health_check().await {
            Ok(_) => Ok(true),
            Err(e) => {
                debug!("Qdrant health check failed: {}", e);
                Ok(false)
            }
        }
    }
}
