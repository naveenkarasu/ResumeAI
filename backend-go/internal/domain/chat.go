package domain

import (
	"time"

	"github.com/google/uuid"
)

// ChatMode represents the type of chat interaction
type ChatMode string

const (
	ChatModeChat      ChatMode = "chat"
	ChatModeEmail     ChatMode = "email"
	ChatModeTailor    ChatMode = "tailor"
	ChatModeInterview ChatMode = "interview"
)

// ChatRequest represents an incoming chat request
type ChatRequest struct {
	Message         string   `json:"message" validate:"required"`
	Mode            ChatMode `json:"mode"`
	JobDescription  *string  `json:"job_description,omitempty"`
	UseVerification bool     `json:"use_verification"`
	SessionID       *string  `json:"session_id,omitempty"`
}

// ChatResponse represents the response to a chat request
type ChatResponse struct {
	Response         string     `json:"response"`
	Citations        []Citation `json:"citations,omitempty"`
	Mode             ChatMode   `json:"mode"`
	GroundingScore   *float64   `json:"grounding_score,omitempty"`
	SearchMode       string     `json:"search_mode"` // hybrid, vector
	ProcessingTimeMs int64      `json:"processing_time_ms"`
	SessionID        string     `json:"session_id"`
}

// Citation represents a citation from the resume
type Citation struct {
	Section        string  `json:"section"`
	Text           string  `json:"text"`
	RelevanceScore float64 `json:"relevance_score"`
}

// ChatSession represents a chat session
type ChatSession struct {
	ID        uuid.UUID     `json:"id"`
	Mode      ChatMode      `json:"mode"`
	Messages  []ChatMessage `json:"messages,omitempty"`
	CreatedAt time.Time     `json:"created_at"`
	UpdatedAt time.Time     `json:"updated_at"`
}

// ChatMessage represents a single message in a chat session
type ChatMessage struct {
	ID             uuid.UUID  `json:"id"`
	SessionID      uuid.UUID  `json:"-"`
	Role           string     `json:"role"` // user, assistant
	Content        string     `json:"content"`
	Citations      []Citation `json:"citations,omitempty"`
	GroundingScore *float64   `json:"grounding_score,omitempty"`
	CreatedAt      time.Time  `json:"created_at"`
}

// ChatHistoryResponse represents chat history
type ChatHistoryResponse struct {
	Sessions []ChatSession `json:"sessions"`
	Total    int           `json:"total"`
}

// SuggestedPrompt represents a suggested prompt for a mode
type SuggestedPrompt struct {
	Text     string   `json:"text"`
	Category string   `json:"category"`
	Mode     ChatMode `json:"mode"`
}

// ChatSuggestionsResponse represents suggested prompts
type ChatSuggestionsResponse struct {
	Suggestions []SuggestedPrompt `json:"suggestions"`
	Mode        ChatMode          `json:"mode"`
}

// GetDefaultSuggestions returns default suggestions for a mode
func GetDefaultSuggestions(mode ChatMode) []SuggestedPrompt {
	switch mode {
	case ChatModeChat:
		return []SuggestedPrompt{
			{Text: "What are my key technical skills?", Category: "skills", Mode: mode},
			{Text: "Summarize my work experience", Category: "experience", Mode: mode},
			{Text: "What industries have I worked in?", Category: "background", Mode: mode},
			{Text: "What are my strongest qualifications?", Category: "strengths", Mode: mode},
		}
	case ChatModeEmail:
		return []SuggestedPrompt{
			{Text: "Write an application email for this job", Category: "application", Mode: mode},
			{Text: "Draft a follow-up email", Category: "followup", Mode: mode},
			{Text: "Write a thank you email after interview", Category: "thankyou", Mode: mode},
		}
	case ChatModeTailor:
		return []SuggestedPrompt{
			{Text: "How should I tailor my resume for this job?", Category: "general", Mode: mode},
			{Text: "What keywords should I add?", Category: "keywords", Mode: mode},
			{Text: "What experience should I highlight?", Category: "experience", Mode: mode},
		}
	case ChatModeInterview:
		return []SuggestedPrompt{
			{Text: "What questions might they ask about my experience?", Category: "behavioral", Mode: mode},
			{Text: "How should I explain my career transitions?", Category: "story", Mode: mode},
			{Text: "What technical questions should I prepare for?", Category: "technical", Mode: mode},
		}
	default:
		return []SuggestedPrompt{}
	}
}
