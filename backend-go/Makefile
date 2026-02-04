.PHONY: build run test clean deps lint docker

# Variables
BINARY_NAME=api
MAIN_PATH=./cmd/api
DOCKER_IMAGE=resume-rag-api

# Go commands
GOCMD=go
GOBUILD=$(GOCMD) build
GORUN=$(GOCMD) run
GOTEST=$(GOCMD) test
GOMOD=$(GOCMD) mod
GOVET=$(GOCMD) vet

# Build the application
build:
	$(GOBUILD) -o bin/$(BINARY_NAME) $(MAIN_PATH)

# Run the application
run:
	$(GORUN) $(MAIN_PATH)

# Run with hot reload (requires air)
dev:
	air -c .air.toml

# Run tests
test:
	$(GOTEST) -v ./...

# Run tests with coverage
test-coverage:
	$(GOTEST) -v -coverprofile=coverage.out ./...
	$(GOCMD) tool cover -html=coverage.out -o coverage.html

# Clean build artifacts
clean:
	rm -rf bin/
	rm -f coverage.out coverage.html

# Download dependencies
deps:
	$(GOMOD) download
	$(GOMOD) tidy

# Run linter (requires golangci-lint)
lint:
	golangci-lint run ./...

# Vet the code
vet:
	$(GOVET) ./...

# Build Docker image
docker:
	docker build -t $(DOCKER_IMAGE) .

# Run Docker container
docker-run:
	docker run -p 8080:8080 --env-file .env $(DOCKER_IMAGE)

# Generate gRPC code (requires protoc)
proto:
	protoc --go_out=. --go-grpc_out=. proto/ml/ml.proto

# Format code
fmt:
	$(GOCMD) fmt ./...

# Check for security issues (requires gosec)
security:
	gosec ./...

# Build for all platforms
build-all:
	GOOS=linux GOARCH=amd64 $(GOBUILD) -o bin/$(BINARY_NAME)-linux-amd64 $(MAIN_PATH)
	GOOS=darwin GOARCH=amd64 $(GOBUILD) -o bin/$(BINARY_NAME)-darwin-amd64 $(MAIN_PATH)
	GOOS=windows GOARCH=amd64 $(GOBUILD) -o bin/$(BINARY_NAME)-windows-amd64.exe $(MAIN_PATH)

# Show help
help:
	@echo "Available targets:"
	@echo "  build        - Build the application"
	@echo "  run          - Run the application"
	@echo "  dev          - Run with hot reload"
	@echo "  test         - Run tests"
	@echo "  test-coverage- Run tests with coverage"
	@echo "  clean        - Clean build artifacts"
	@echo "  deps         - Download dependencies"
	@echo "  lint         - Run linter"
	@echo "  vet          - Vet the code"
	@echo "  docker       - Build Docker image"
	@echo "  docker-run   - Run Docker container"
	@echo "  proto        - Generate gRPC code"
	@echo "  fmt          - Format code"
	@echo "  security     - Check for security issues"
	@echo "  build-all    - Build for all platforms"
