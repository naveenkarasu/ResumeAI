package middleware

import (
	"time"

	"github.com/gofiber/fiber/v2"
	"github.com/gofiber/fiber/v2/middleware/cors"
	"github.com/gofiber/fiber/v2/middleware/limiter"
	"github.com/gofiber/fiber/v2/middleware/recover"
	"github.com/gofiber/fiber/v2/middleware/requestid"
	"github.com/google/uuid"
	"go.uber.org/zap"

	"github.com/resume-rag/backend/internal/config"
	"github.com/resume-rag/backend/pkg/logger"
)

// Setup configures all middleware for the application
func Setup(app *fiber.App, cfg *config.Config) {
	// Recovery middleware (panic handler)
	app.Use(recover.New(recover.Config{
		EnableStackTrace: cfg.Server.Debug,
	}))

	// Request ID middleware
	app.Use(requestid.New(requestid.Config{
		Generator: func() string {
			return uuid.New().String()
		},
	}))

	// CORS middleware
	app.Use(cors.New(cors.Config{
		AllowOrigins:     joinStrings(cfg.CORS.AllowedOrigins),
		AllowMethods:     joinStrings(cfg.CORS.AllowedMethods),
		AllowHeaders:     joinStrings(cfg.CORS.AllowedHeaders),
		AllowCredentials: true,
		MaxAge:           cfg.CORS.MaxAge,
	}))

	// Rate limiting middleware
	if cfg.RateLimit.Enabled {
		app.Use(limiter.New(limiter.Config{
			Max:        cfg.RateLimit.RequestsPerMinute,
			Expiration: time.Minute,
			KeyGenerator: func(c *fiber.Ctx) string {
				return c.IP()
			},
			LimitReached: func(c *fiber.Ctx) error {
				return c.Status(fiber.StatusTooManyRequests).JSON(fiber.Map{
					"error":   "rate_limit_exceeded",
					"message": "Too many requests. Please try again later.",
				})
			},
		}))
	}

	// Logging middleware
	app.Use(RequestLogger(cfg.Server.Debug))

	// Timing middleware
	app.Use(RequestTiming())
}

// RequestLogger returns a logging middleware
func RequestLogger(debug bool) fiber.Handler {
	return func(c *fiber.Ctx) error {
		start := time.Now()

		// Process request
		err := c.Next()

		// Calculate duration
		duration := time.Since(start)

		// Get status code
		status := c.Response().StatusCode()

		// Log fields
		fields := []zap.Field{
			zap.String("request_id", c.GetRespHeader("X-Request-ID")),
			zap.String("method", c.Method()),
			zap.String("path", c.Path()),
			zap.Int("status", status),
			zap.Duration("duration", duration),
			zap.String("ip", c.IP()),
		}

		// Add user agent in debug mode
		if debug {
			fields = append(fields, zap.String("user_agent", c.Get("User-Agent")))
		}

		// Log based on status code
		switch {
		case status >= 500:
			logger.Error("Server error", fields...)
		case status >= 400:
			logger.Warn("Client error", fields...)
		case duration > 2*time.Second:
			logger.Warn("Slow request", fields...)
		default:
			if debug {
				logger.Debug("Request completed", fields...)
			}
		}

		return err
	}
}

// RequestTiming adds timing headers to responses
func RequestTiming() fiber.Handler {
	return func(c *fiber.Ctx) error {
		start := time.Now()

		// Process request
		err := c.Next()

		// Add timing header
		duration := time.Since(start)
		c.Set("X-Process-Time", duration.String())

		return err
	}
}

// joinStrings joins strings with comma
func joinStrings(strs []string) string {
	if len(strs) == 0 {
		return "*"
	}
	result := strs[0]
	for i := 1; i < len(strs); i++ {
		result += "," + strs[i]
	}
	return result
}
