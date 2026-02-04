use serde::Deserialize;
use std::env;

#[derive(Debug, Clone, Deserialize)]
pub struct Config {
    pub server: ServerConfig,
    pub qdrant: QdrantConfig,
    pub models: ModelsConfig,
    pub search: SearchConfig,
}

#[derive(Debug, Clone, Deserialize)]
pub struct ServerConfig {
    pub grpc_port: u16,
    pub http_port: u16,
    pub host: String,
}

#[derive(Debug, Clone, Deserialize)]
pub struct QdrantConfig {
    pub host: String,
    pub port: u16,
    pub collection_prefix: String,
}

#[derive(Debug, Clone, Deserialize)]
pub struct ModelsConfig {
    pub embedding_model: String,
    pub reranker_model: String,
    pub models_dir: String,
}

#[derive(Debug, Clone, Deserialize)]
pub struct SearchConfig {
    pub default_top_k: usize,
    pub vector_weight: f32,
    pub bm25_weight: f32,
    pub rrf_k: usize,
    pub rerank_fetch_multiplier: usize,
}

impl Config {
    pub fn load() -> Result<Self, config::ConfigError> {
        // Load .env file
        let _ = dotenvy::dotenv();

        let config = config::Config::builder()
            // Set defaults
            .set_default("server.grpc_port", 50051)?
            .set_default("server.http_port", 50052)?
            .set_default("server.host", "0.0.0.0")?
            .set_default("qdrant.host", "localhost")?
            .set_default("qdrant.port", 6333)?
            .set_default("qdrant.collection_prefix", "resume_rag")?
            .set_default("models.embedding_model", "all-MiniLM-L6-v2")?
            .set_default("models.reranker_model", "ms-marco-MiniLM-L-6-v2")?
            .set_default("models.models_dir", "./models")?
            .set_default("search.default_top_k", 10)?
            .set_default("search.vector_weight", 0.7)?
            .set_default("search.bm25_weight", 0.3)?
            .set_default("search.rrf_k", 60)?
            .set_default("search.rerank_fetch_multiplier", 5)?
            // Load from environment
            .add_source(
                config::Environment::default()
                    .separator("__")
                    .prefix("ML"),
            )
            .build()?;

        config.try_deserialize()
    }

    pub fn from_env() -> Self {
        Self {
            server: ServerConfig {
                grpc_port: env::var("ML_GRPC_PORT")
                    .ok()
                    .and_then(|s| s.parse().ok())
                    .unwrap_or(50051),
                http_port: env::var("ML_HTTP_PORT")
                    .ok()
                    .and_then(|s| s.parse().ok())
                    .unwrap_or(50052),
                host: env::var("ML_HOST").unwrap_or_else(|_| "0.0.0.0".to_string()),
            },
            qdrant: QdrantConfig {
                host: env::var("QDRANT_HOST").unwrap_or_else(|_| "localhost".to_string()),
                port: env::var("QDRANT_PORT")
                    .ok()
                    .and_then(|s| s.parse().ok())
                    .unwrap_or(6333),
                collection_prefix: env::var("QDRANT_COLLECTION_PREFIX")
                    .unwrap_or_else(|_| "resume_rag".to_string()),
            },
            models: ModelsConfig {
                embedding_model: env::var("EMBEDDING_MODEL")
                    .unwrap_or_else(|_| "all-MiniLM-L6-v2".to_string()),
                reranker_model: env::var("RERANKER_MODEL")
                    .unwrap_or_else(|_| "ms-marco-MiniLM-L-6-v2".to_string()),
                models_dir: env::var("MODELS_DIR").unwrap_or_else(|_| "./models".to_string()),
            },
            search: SearchConfig {
                default_top_k: env::var("DEFAULT_TOP_K")
                    .ok()
                    .and_then(|s| s.parse().ok())
                    .unwrap_or(10),
                vector_weight: env::var("VECTOR_WEIGHT")
                    .ok()
                    .and_then(|s| s.parse().ok())
                    .unwrap_or(0.7),
                bm25_weight: env::var("BM25_WEIGHT")
                    .ok()
                    .and_then(|s| s.parse().ok())
                    .unwrap_or(0.3),
                rrf_k: env::var("RRF_K")
                    .ok()
                    .and_then(|s| s.parse().ok())
                    .unwrap_or(60),
                rerank_fetch_multiplier: env::var("RERANK_FETCH_MULTIPLIER")
                    .ok()
                    .and_then(|s| s.parse().ok())
                    .unwrap_or(5),
            },
        }
    }
}

impl QdrantConfig {
    pub fn url(&self) -> String {
        format!("http://{}:{}", self.host, self.port)
    }
}
