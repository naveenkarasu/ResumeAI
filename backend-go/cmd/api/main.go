package main

import (
	"flag"
	"fmt"
	"os"
	"os/signal"
	"syscall"

	"github.com/gofiber/fiber/v2"
	"go.uber.org/zap"

	"github.com/resume-rag/backend/internal/api"
	"github.com/resume-rag/backend/internal/api/handlers"
	"github.com/resume-rag/backend/internal/api/middleware"
	"github.com/resume-rag/backend/internal/config"
	"github.com/resume-rag/backend/pkg/logger"
)

func main() {
	// Parse flags
	configPath := flag.String("config", "", "Path to config file")
	flag.Parse()

	// Load configuration
	cfg, err := config.Load(*configPath)
	if err != nil {
		fmt.Fprintf(os.Stderr, "Failed to load config: %v\n", err)
		os.Exit(1)
	}

	// Initialize logger
	logger.Init(cfg.Server.Debug)
	defer logger.Sync()

	logger.Info("Starting Resume RAG API",
		zap.String("version", "2.0.0"),
		zap.Bool("debug", cfg.Server.Debug),
	)

	// Create Fiber app
	app := fiber.New(fiber.Config{
		AppName:               "Resume RAG API v2.0.0",
		ReadTimeout:           cfg.Server.ReadTimeout,
		WriteTimeout:          cfg.Server.WriteTimeout,
		DisableStartupMessage: !cfg.Server.Debug,
		ErrorHandler:          errorHandler,
	})

	// Setup middleware
	middleware.Setup(app, cfg)

	// Create placeholder services (will be replaced with real implementations)
	deps := &api.Dependencies{
		DB:               nil, // TODO: Connect to PostgreSQL
		MLClient:         nil, // TODO: Connect to ML service via gRPC
		ChatService:      &handlers.PlaceholderChatService{},
		AnalyzerService:  nil,
		JobMatchService:  nil,
		InterviewService: nil,
		EmailService:     nil,
		JobListService:   &handlers.PlaceholderJobListService{},
	}

	// Setup routes
	api.SetupRoutes(app, cfg, deps)

	// Graceful shutdown
	c := make(chan os.Signal, 1)
	signal.Notify(c, os.Interrupt, syscall.SIGTERM)

	go func() {
		<-c
		logger.Info("Shutting down gracefully...")
		_ = app.Shutdown()
	}()

	// Start server
	addr := fmt.Sprintf("%s:%d", cfg.Server.Host, cfg.Server.Port)
	logger.Info("Server starting",
		zap.String("address", addr),
		zap.String("llm_backend", cfg.LLM.DefaultBackend),
	)

	if err := app.Listen(addr); err != nil {
		logger.Fatal("Server failed to start", zap.Error(err))
	}
}

// errorHandler handles errors globally
func errorHandler(c *fiber.Ctx, err error) error {
	// Default to 500
	code := fiber.StatusInternalServerError
	message := "Internal server error"

	// Check if it's a Fiber error
	if e, ok := err.(*fiber.Error); ok {
		code = e.Code
		message = e.Message
	}

	// Log error
	logger.Error("Request error",
		zap.Int("status", code),
		zap.String("path", c.Path()),
		zap.Error(err),
	)

	return c.Status(code).JSON(fiber.Map{
		"error":   "request_failed",
		"message": message,
		"path":    c.Path(),
	})
}
