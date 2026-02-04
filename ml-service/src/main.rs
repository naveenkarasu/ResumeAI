use anyhow::{Context, Result};
use clap::Parser;
use std::net::SocketAddr;
use tonic::transport::Server;
use tracing::{info, Level};
use tracing_subscriber::FmtSubscriber;

use ml_service::config::Config;
use ml_service::embedding;
use ml_service::grpc::ml::ml_service_server::MlServiceServer;
use ml_service::grpc::MlServiceImpl;
use ml_service::reranker;
use ml_service::search::{HybridSearch, QdrantClient};

#[derive(Parser, Debug)]
#[command(name = "ml-service")]
#[command(about = "ML Service for ResumeAI - embeddings, reranking, and hybrid search")]
struct Args {
    /// Config file path
    #[arg(short, long, default_value = "config.yaml")]
    config: String,

    /// Log level
    #[arg(short, long, default_value = "info")]
    log_level: String,
}

#[tokio::main]
async fn main() -> Result<()> {
    let args = Args::parse();

    // Initialize logging
    let log_level = match args.log_level.to_lowercase().as_str() {
        "trace" => Level::TRACE,
        "debug" => Level::DEBUG,
        "info" => Level::INFO,
        "warn" => Level::WARN,
        "error" => Level::ERROR,
        _ => Level::INFO,
    };

    let subscriber = FmtSubscriber::builder()
        .with_max_level(log_level)
        .with_target(true)
        .with_thread_ids(true)
        .with_file(true)
        .with_line_number(true)
        .finish();

    tracing::subscriber::set_global_default(subscriber)
        .context("Failed to set tracing subscriber")?;

    info!("Starting ML Service v{}", env!("CARGO_PKG_VERSION"));

    // Load configuration
    let config = Config::load().context("Failed to load configuration")?;
    info!("Configuration loaded");

    // Initialize embedding model
    info!("Initializing embedding model...");
    embedding::init_embedding_model(&config.models)
        .context("Failed to initialize embedding model")?;
    info!(
        "Embedding model initialized (dim={})",
        embedding::get_dimensions()
    );

    // Initialize reranker
    info!("Initializing reranker model...");
    reranker::init_reranker(&config.models).context("Failed to initialize reranker")?;
    info!("Reranker model initialized");

    // Initialize Qdrant client
    info!("Connecting to Qdrant...");
    let qdrant_client = QdrantClient::new(&config.qdrant)
        .await
        .context("Failed to connect to Qdrant")?;

    // Check Qdrant health
    if qdrant_client.health_check().await? {
        info!("Qdrant connection established");
    } else {
        tracing::warn!("Qdrant health check failed, continuing anyway");
    }

    // Create hybrid search
    let hybrid_search = HybridSearch::new(qdrant_client, config.search.rrf_k);

    // Create gRPC service
    let ml_service = MlServiceImpl::new(hybrid_search);

    // Start gRPC server
    let addr: SocketAddr = format!("{}:{}", config.server.host, config.server.grpc_port)
        .parse()
        .context("Invalid server address")?;

    info!("Starting gRPC server on {}", addr);

    Server::builder()
        .add_service(MlServiceServer::new(ml_service))
        .serve_with_shutdown(addr, shutdown_signal())
        .await
        .context("gRPC server failed")?;

    info!("ML Service shut down gracefully");
    Ok(())
}

async fn shutdown_signal() {
    let ctrl_c = async {
        tokio::signal::ctrl_c()
            .await
            .expect("Failed to install Ctrl+C handler");
    };

    #[cfg(unix)]
    let terminate = async {
        tokio::signal::unix::signal(tokio::signal::unix::SignalKind::terminate())
            .expect("Failed to install signal handler")
            .recv()
            .await;
    };

    #[cfg(not(unix))]
    let terminate = std::future::pending::<()>();

    tokio::select! {
        _ = ctrl_c => {
            info!("Received Ctrl+C, shutting down...");
        }
        _ = terminate => {
            info!("Received terminate signal, shutting down...");
        }
    }
}
