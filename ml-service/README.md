# ML Service

High-performance ML service for Resume RAG built in Rust with ONNX Runtime.

## Features

- **Embeddings**: Sentence embeddings using all-MiniLM-L6-v2
- **Reranking**: Cross-encoder reranking using ms-marco-MiniLM-L-6-v2
- **Hybrid Search**: BM25 + Vector search with RRF fusion
- **Skills Extraction**: NER-based skills extraction from resumes
- **gRPC API**: High-performance gRPC interface

## Prerequisites

- Rust 1.75+
- Protocol Buffers compiler (protoc)
- ONNX models in `./models` directory
- Qdrant vector database

## Model Setup

Download ONNX models to the `models` directory:

```bash
mkdir -p models/all-MiniLM-L6-v2
mkdir -p models/ms-marco-MiniLM-L-6-v2

# Download from Hugging Face (example)
# You'll need model.onnx and tokenizer.json for each model
```

## Building

```bash
# Install protoc if needed
# On Windows: choco install protoc
# On macOS: brew install protobuf
# On Linux: apt install protobuf-compiler

# Build
cargo build --release
```

## Running

```bash
# With default config
cargo run --release

# With custom config
cargo run --release -- --config config.yaml

# With debug logging
cargo run --release -- --log-level debug
```

## Configuration

See `config.yaml` for configuration options:

- `server`: gRPC and HTTP port configuration
- `qdrant`: Vector database connection settings
- `models`: Model paths and names
- `search`: Search algorithm parameters

## gRPC API

See `proto/ml.proto` for the full service definition:

- `Embed`: Generate embedding for single text
- `EmbedBatch`: Generate embeddings for multiple texts
- `Rerank`: Rerank documents using cross-encoder
- `Search`: Hybrid search with optional reranking
- `ExtractSkills`: Extract skills from text
- `IndexDocuments`: Index documents for search
- `ClearIndex`: Clear search index
- `HealthCheck`: Service health status

## Testing

```bash
# Run tests
cargo test

# Run with coverage
cargo tarpaulin
```

## Docker

```bash
# Build image
docker build -t ml-service .

# Run container
docker run -p 50051:50051 -v ./models:/app/models ml-service
```
