package handlers

import (
	"context"

	"github.com/gofiber/fiber/v2"
	"github.com/google/uuid"

	"github.com/resume-rag/backend/internal/domain"
)

// ChatService defines the interface for chat operations
type ChatService interface {
	Chat(ctx context.Context, req domain.ChatRequest) (*domain.ChatResponse, error)
	GetSuggestions(ctx context.Context, mode domain.ChatMode) (*domain.ChatSuggestionsResponse, error)
	GetHistory(ctx context.Context, sessionID *uuid.UUID, limit int) (*domain.ChatHistoryResponse, error)
	ClearHistory(ctx context.Context, sessionID *uuid.UUID) error
}

// ChatHandler handles chat API requests
type ChatHandler struct {
	service ChatService
}

// NewChatHandler creates a new chat handler
func NewChatHandler(service ChatService) *ChatHandler {
	return &ChatHandler{service: service}
}

// Chat handles POST /api/chat
func (h *ChatHandler) Chat(c *fiber.Ctx) error {
	var req domain.ChatRequest
	if err := c.BodyParser(&req); err != nil {
		return c.Status(fiber.StatusBadRequest).JSON(fiber.Map{
			"error":   "invalid_request",
			"message": "Invalid request body",
		})
	}

	// Validate
	if req.Message == "" {
		return c.Status(fiber.StatusBadRequest).JSON(fiber.Map{
			"error":   "invalid_request",
			"message": "Message is required",
		})
	}

	// Set default mode
	if req.Mode == "" {
		req.Mode = domain.ChatModeChat
	}

	result, err := h.service.Chat(c.Context(), req)
	if err != nil {
		return c.Status(fiber.StatusInternalServerError).JSON(fiber.Map{
			"error":   "chat_failed",
			"message": err.Error(),
		})
	}

	return c.JSON(result)
}

// GetSuggestions handles GET /api/chat/suggestions
func (h *ChatHandler) GetSuggestions(c *fiber.Ctx) error {
	mode := domain.ChatMode(c.Query("mode", "chat"))

	result, err := h.service.GetSuggestions(c.Context(), mode)
	if err != nil {
		return c.Status(fiber.StatusInternalServerError).JSON(fiber.Map{
			"error":   "fetch_failed",
			"message": err.Error(),
		})
	}

	return c.JSON(result)
}

// GetHistory handles GET /api/chat/history
func (h *ChatHandler) GetHistory(c *fiber.Ctx) error {
	limit := c.QueryInt("limit", 20)

	var sessionID *uuid.UUID
	if sid := c.Query("session_id"); sid != "" {
		if id, err := uuid.Parse(sid); err == nil {
			sessionID = &id
		}
	}

	result, err := h.service.GetHistory(c.Context(), sessionID, limit)
	if err != nil {
		return c.Status(fiber.StatusInternalServerError).JSON(fiber.Map{
			"error":   "fetch_failed",
			"message": err.Error(),
		})
	}

	return c.JSON(result)
}

// ClearHistory handles DELETE /api/chat/history
func (h *ChatHandler) ClearHistory(c *fiber.Ctx) error {
	var sessionID *uuid.UUID
	if sid := c.Query("session_id"); sid != "" {
		if id, err := uuid.Parse(sid); err == nil {
			sessionID = &id
		}
	}

	if err := h.service.ClearHistory(c.Context(), sessionID); err != nil {
		return c.Status(fiber.StatusInternalServerError).JSON(fiber.Map{
			"error":   "clear_failed",
			"message": err.Error(),
		})
	}

	return c.JSON(fiber.Map{
		"success": true,
		"message": "History cleared",
	})
}
