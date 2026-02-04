package domain

import (
	"time"

	"github.com/google/uuid"
)

// ApplicationStatus represents the status of a job application
type ApplicationStatus string

const (
	ApplicationStatusSaved     ApplicationStatus = "saved"
	ApplicationStatusApplied   ApplicationStatus = "applied"
	ApplicationStatusScreening ApplicationStatus = "screening"
	ApplicationStatusInterview ApplicationStatus = "interview"
	ApplicationStatusOffer     ApplicationStatus = "offer"
	ApplicationStatusRejected  ApplicationStatus = "rejected"
	ApplicationStatusWithdrawn ApplicationStatus = "withdrawn"
	ApplicationStatusAccepted  ApplicationStatus = "accepted"
)

// Application represents a tracked job application
type Application struct {
	ID            uuid.UUID         `json:"id"`
	Job           JobBrief          `json:"job"`
	Status        ApplicationStatus `json:"status"`
	AppliedDate   *time.Time        `json:"applied_date,omitempty"`
	Notes         *string           `json:"notes,omitempty"`
	ResumeVersion *string           `json:"resume_version,omitempty"`
	CoverLetter   *string           `json:"cover_letter,omitempty"`
	ReminderDate  *time.Time        `json:"reminder_date,omitempty"`
	LastUpdated   time.Time         `json:"last_updated"`
	Timeline      []TimelineEntry   `json:"timeline"`
	CreatedAt     time.Time         `json:"created_at"`
}

// TimelineEntry represents a status change in application history
type TimelineEntry struct {
	ID            uuid.UUID          `json:"id"`
	ApplicationID uuid.UUID          `json:"-"`
	OldStatus     *ApplicationStatus `json:"old_status,omitempty"`
	NewStatus     ApplicationStatus  `json:"new_status"`
	ChangedAt     time.Time          `json:"changed_at"`
	Notes         *string            `json:"notes,omitempty"`
}

// ApplicationCreate represents the request to create an application
type ApplicationCreate struct {
	JobID         uuid.UUID          `json:"job_id" validate:"required"`
	Status        *ApplicationStatus `json:"status,omitempty"`
	Notes         *string            `json:"notes,omitempty"`
	ResumeVersion *string            `json:"resume_version,omitempty"`
	ReminderDate  *time.Time         `json:"reminder_date,omitempty"`
}

// ApplicationUpdate represents the request to update an application
type ApplicationUpdate struct {
	Status       *ApplicationStatus `json:"status,omitempty"`
	Notes        *string            `json:"notes,omitempty"`
	CoverLetter  *string            `json:"cover_letter,omitempty"`
	ReminderDate *time.Time         `json:"reminder_date,omitempty"`
}

// ApplicationListResponse represents the response for listing applications
type ApplicationListResponse struct {
	Applications []Application      `json:"applications"`
	Total        int                `json:"total"`
	ByStatus     map[string]int     `json:"by_status"`
}

// ApplicationStats represents statistics about applications
type ApplicationStats struct {
	TotalApplications     int            `json:"total_applications"`
	ByStatus              map[string]int `json:"by_status"`
	ResponseRate          *float64       `json:"response_rate,omitempty"`
	AverageTimeToResponse *int           `json:"average_time_to_response,omitempty"`
	TopMatchedSkills      []string       `json:"top_matched_skills,omitempty"`
	TopMissingSkills      []string       `json:"top_missing_skills,omitempty"`
}

// SavedSearch represents a saved search preset
type SavedSearch struct {
	ID                  uuid.UUID   `json:"id"`
	Name                string      `json:"name"`
	Query               *string     `json:"query,omitempty"`
	Filters             *JobFilters `json:"filters,omitempty"`
	CreatedAt           time.Time   `json:"created_at"`
	LastRunAt           *time.Time  `json:"last_run_at,omitempty"`
	NotificationEnabled bool        `json:"notification_enabled"`
	ResultCount         *int        `json:"result_count,omitempty"`
}

// SavedSearchCreate represents the request to create a saved search
type SavedSearchCreate struct {
	Name                string      `json:"name" validate:"required"`
	Query               *string     `json:"query,omitempty"`
	Filters             *JobFilters `json:"filters,omitempty"`
	NotificationEnabled *bool       `json:"notification_enabled,omitempty"`
}

// CoverLetterRequest represents a cover letter generation request
type CoverLetterRequest struct {
	JobID        uuid.UUID `json:"job_id" validate:"required"`
	CustomPrompt *string   `json:"custom_prompt,omitempty"`
	Tone         *string   `json:"tone,omitempty"` // professional, casual, enthusiastic
	MaxWords     *int      `json:"max_words,omitempty"`
}

// CoverLetterResponse represents a generated cover letter
type CoverLetterResponse struct {
	JobID          uuid.UUID `json:"job_id"`
	CoverLetter    string    `json:"cover_letter"`
	WordCount      int       `json:"word_count"`
	HighlightsUsed []string  `json:"highlights_used"`
}

// JobRecommendation represents an AI-recommended job
type JobRecommendation struct {
	Job                  JobBrief `json:"job"`
	RecommendationReason string   `json:"recommendation_reason"`
	RelevanceScore       float64  `json:"relevance_score"`
}

// JobSearchStats represents job database statistics
type JobSearchStats struct {
	TotalJobsIndexed    int            `json:"total_jobs_indexed"`
	JobsBySource        map[string]int `json:"jobs_by_source"`
	JobsByLocationType  map[string]int `json:"jobs_by_location_type"`
	AverageSalary       *int           `json:"average_salary,omitempty"`
	LastScrapeAt        *time.Time     `json:"last_scrape_at,omitempty"`
}
