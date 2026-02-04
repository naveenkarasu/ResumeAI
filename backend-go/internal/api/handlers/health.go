package handlers

import (
	"github.com/gofiber/fiber/v2"

	"github.com/resume-rag/backend/internal/config"
)

const version = "2.0.0"

// HealthCheck returns the health status
func HealthCheck(db interface{}) fiber.Handler {
	return func(c *fiber.Ctx) error {
		// Check database connection
		dbStatus := "healthy"
		if db == nil {
			dbStatus = "unavailable"
		}
		// TODO: Actually ping the database

		// Check ML service
		mlStatus := "healthy"
		// TODO: Actually check ML service

		return c.JSON(fiber.Map{
			"status":      "healthy",
			"version":     version,
			"db_status":   dbStatus,
			"ml_status":   mlStatus,
		})
	}
}

// ReadinessCheck returns whether the service is ready to accept traffic
func ReadinessCheck(db interface{}, mlClient interface{}) fiber.Handler {
	return func(c *fiber.Ctx) error {
		// Check database
		if db == nil {
			return c.Status(fiber.StatusServiceUnavailable).JSON(fiber.Map{
				"status": "not_ready",
				"reason": "Database not connected",
			})
		}

		// Check ML service
		if mlClient == nil {
			return c.Status(fiber.StatusServiceUnavailable).JSON(fiber.Map{
				"status": "not_ready",
				"reason": "ML service not connected",
			})
		}

		return c.JSON(fiber.Map{
			"status": "ready",
		})
	}
}

// Root returns basic API info
func Root(cfg *config.Config) fiber.Handler {
	return func(c *fiber.Ctx) error {
		docsURL := "/docs"
		if !cfg.Server.Debug {
			docsURL = "Disabled in production"
		}

		return c.JSON(fiber.Map{
			"name":    "Resume RAG Platform API",
			"version": version,
			"docs":    docsURL,
			"health":  "/health",
			"ready":   "/ready",
		})
	}
}
