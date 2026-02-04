package domain

import (
	"time"

	"github.com/google/uuid"
)

// LocationType represents the work location type
type LocationType string

const (
	LocationTypeRemote LocationType = "remote"
	LocationTypeHybrid LocationType = "hybrid"
	LocationTypeOnsite LocationType = "onsite"
)

// CompanySize represents company size categories
type CompanySize string

const (
	CompanySizeStartup    CompanySize = "startup"
	CompanySizeSmall      CompanySize = "small"
	CompanySizeMedium     CompanySize = "medium"
	CompanySizeLarge      CompanySize = "large"
	CompanySizeEnterprise CompanySize = "enterprise"
)

// JobSource represents where the job was scraped from
type JobSource string

const (
	JobSourceIndeed      JobSource = "indeed"
	JobSourceDice        JobSource = "dice"
	JobSourceWellfound   JobSource = "wellfound"
	JobSourceYCombinator JobSource = "ycombinator"
	JobSourceBuiltIn     JobSource = "builtin"
	JobSourceLinkedIn    JobSource = "linkedin"
)

// MatchQuality represents the quality of resume-job match
type MatchQuality string

const (
	MatchQualityExcellent MatchQuality = "excellent"
	MatchQualityGood      MatchQuality = "good"
	MatchQualityFair      MatchQuality = "fair"
	MatchQualityPoor      MatchQuality = "poor"
)

// Company represents a company entity
type Company struct {
	ID             uuid.UUID   `json:"id"`
	Name           string      `json:"name"`
	NormalizedName string      `json:"-"`
	LogoURL        *string     `json:"logo_url,omitempty"`
	Website        *string     `json:"website,omitempty"`
	Industry       *string     `json:"industry,omitempty"`
	Size           *CompanySize `json:"size,omitempty"`
	Rating         *float64    `json:"rating,omitempty"`
	CreatedAt      time.Time   `json:"created_at"`
}

// Job represents a job listing
type Job struct {
	ID             uuid.UUID     `json:"id"`
	URL            string        `json:"url"`
	Title          string        `json:"title"`
	Company        Company       `json:"company"`
	Location       *string       `json:"location,omitempty"`
	LocationType   *LocationType `json:"location_type,omitempty"`
	SalaryMin      *int          `json:"salary_min,omitempty"`
	SalaryMax      *int          `json:"salary_max,omitempty"`
	SalaryCurrency string        `json:"salary_currency"`
	SalaryText     *string       `json:"salary_text,omitempty"`
	Description    string        `json:"description"`
	Requirements   []string      `json:"requirements"`
	PostedDate     *time.Time    `json:"posted_date,omitempty"`
	ScrapedAt      time.Time     `json:"scraped_at"`
	Source         JobSource     `json:"source"`
	IsActive       bool          `json:"is_active"`
	EmbeddingID    *uuid.UUID    `json:"-"`
	ContentHash    *string       `json:"-"`
	CreatedAt      time.Time     `json:"created_at"`
	UpdatedAt      time.Time     `json:"updated_at"`

	// Computed fields (from match scoring)
	MatchScore     *float64      `json:"match_score,omitempty"`
	MatchQuality   *MatchQuality `json:"match_quality,omitempty"`
	MatchedSkills  []string      `json:"matched_skills,omitempty"`
	MissingSkills  []string      `json:"missing_skills,omitempty"`
}

// JobBrief is a compact representation for list views
type JobBrief struct {
	ID                uuid.UUID         `json:"id"`
	Title             string            `json:"title"`
	CompanyName       string            `json:"company_name"`
	CompanyLogo       *string           `json:"company_logo,omitempty"`
	Location          *string           `json:"location,omitempty"`
	LocationType      *LocationType     `json:"location_type,omitempty"`
	SalaryText        *string           `json:"salary_text,omitempty"`
	PostedDate        *time.Time        `json:"posted_date,omitempty"`
	Source            JobSource         `json:"source"`
	MatchScore        *float64          `json:"match_score,omitempty"`
	MatchQuality      *MatchQuality     `json:"match_quality,omitempty"`
	ApplicationStatus *ApplicationStatus `json:"application_status,omitempty"`
}

// JobFilters represents search filters
type JobFilters struct {
	Keywords         []string       `json:"keywords,omitempty"`
	Location         *string        `json:"location,omitempty"`
	LocationTypes    []LocationType `json:"location_type,omitempty"`
	SalaryMin        *int           `json:"salary_min,omitempty"`
	SalaryMax        *int           `json:"salary_max,omitempty"`
	CompanySizes     []CompanySize  `json:"company_size,omitempty"`
	Sources          []JobSource    `json:"sources,omitempty"`
	PostedWithinDays *int           `json:"posted_within_days,omitempty"`
	ExperienceLevel  *string        `json:"experience_level,omitempty"`
	Industry         *string        `json:"industry,omitempty"`
}

// JobSearchRequest represents a job search request
type JobSearchRequest struct {
	Query              *string     `json:"query,omitempty"`
	Filters            *JobFilters `json:"filters,omitempty"`
	IncludeMatchScores bool        `json:"include_match_scores"`
	Page               int         `json:"page"`
	Limit              int         `json:"limit"`
	SortBy             string      `json:"sort_by"`  // match_score, posted_date, salary
	SortOrder          string      `json:"sort_order"` // asc, desc
}

// JobSearchResponse represents search results
type JobSearchResponse struct {
	Jobs          []JobBrief   `json:"jobs"`
	Total         int          `json:"total"`
	Page          int          `json:"page"`
	Pages         int          `json:"pages"`
	Limit         int          `json:"limit"`
	SearchID      *string      `json:"search_id,omitempty"`
	Cached        bool         `json:"cached"`
	ScrapeStatus  ScrapeStatus `json:"scrape_status"`
	FiltersApplied *JobFilters `json:"filters_applied,omitempty"`
}

// ScrapeStatus represents the status of a scraping task
type ScrapeStatus string

const (
	ScrapeStatusQueued     ScrapeStatus = "queued"
	ScrapeStatusInProgress ScrapeStatus = "in_progress"
	ScrapeStatusCompleted  ScrapeStatus = "completed"
	ScrapeStatusFailed     ScrapeStatus = "failed"
)

// ScrapeTask represents a background scraping task
type ScrapeTask struct {
	ID         uuid.UUID    `json:"id"`
	Keywords   []string     `json:"keywords"`
	Location   *string      `json:"location,omitempty"`
	Sources    []JobSource  `json:"sources"`
	Status     ScrapeStatus `json:"status"`
	JobsFound  int          `json:"jobs_found"`
	Error      *string      `json:"error,omitempty"`
	StartedAt  *time.Time   `json:"started_at,omitempty"`
	FinishedAt *time.Time   `json:"finished_at,omitempty"`
	CreatedAt  time.Time    `json:"created_at"`
}

// JobMatchScore represents pre-calculated match scores
type JobMatchScore struct {
	ID              uuid.UUID `json:"id"`
	JobID           uuid.UUID `json:"job_id"`
	ResumeHash      string    `json:"-"`
	OverallScore    int       `json:"overall_score"`
	SkillsScore     *int      `json:"skills_score,omitempty"`
	ExperienceScore *int      `json:"experience_score,omitempty"`
	EducationScore  *int      `json:"education_score,omitempty"`
	MatchedSkills   []string  `json:"matched_skills"`
	MissingSkills   []string  `json:"missing_skills"`
	CalculatedAt    time.Time `json:"calculated_at"`
}

// GetMatchQuality returns the quality category for a score
func GetMatchQuality(score float64) MatchQuality {
	switch {
	case score >= 80:
		return MatchQualityExcellent
	case score >= 60:
		return MatchQualityGood
	case score >= 40:
		return MatchQualityFair
	default:
		return MatchQualityPoor
	}
}
