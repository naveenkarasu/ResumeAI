package scraper

import (
	"context"
	"time"

	"github.com/resume-rag/backend/internal/domain"
)

// Scraper interface for job board scrapers
type Scraper interface {
	// Name returns the scraper name
	Name() string

	// Source returns the job source
	Source() domain.JobSource

	// Scrape performs the scraping operation
	Scrape(ctx context.Context, query string, opts *ScrapeOptions) (*ScrapeResult, error)

	// ScrapeJob fetches details for a single job
	ScrapeJob(ctx context.Context, url string) (*domain.Job, error)
}

// ScrapeOptions configures scraping behavior
type ScrapeOptions struct {
	MaxJobs        int
	Location       string
	Remote         bool
	ExperienceMin  int
	ExperienceMax  int
	PostedWithin   time.Duration
	IncludeExpired bool
}

// DefaultScrapeOptions returns sensible defaults
func DefaultScrapeOptions() *ScrapeOptions {
	return &ScrapeOptions{
		MaxJobs:        50,
		Location:       "",
		Remote:         false,
		ExperienceMin:  0,
		ExperienceMax:  0,
		PostedWithin:   7 * 24 * time.Hour,
		IncludeExpired: false,
	}
}

// ScrapeResult contains scraping results
type ScrapeResult struct {
	Jobs      []*domain.Job
	Total     int
	Scraped   int
	Errors    []error
	StartTime time.Time
	EndTime   time.Time
}

// Duration returns the scraping duration
func (r *ScrapeResult) Duration() time.Duration {
	return r.EndTime.Sub(r.StartTime)
}

// ScraperRegistry manages multiple scrapers
type ScraperRegistry struct {
	scrapers map[domain.JobSource]Scraper
}

// NewScraperRegistry creates a new registry
func NewScraperRegistry() *ScraperRegistry {
	return &ScraperRegistry{
		scrapers: make(map[domain.JobSource]Scraper),
	}
}

// Register adds a scraper to the registry
func (r *ScraperRegistry) Register(s Scraper) {
	r.scrapers[s.Source()] = s
}

// Get retrieves a scraper by source
func (r *ScraperRegistry) Get(source domain.JobSource) (Scraper, bool) {
	s, ok := r.scrapers[source]
	return s, ok
}

// All returns all registered scrapers
func (r *ScraperRegistry) All() []Scraper {
	scrapers := make([]Scraper, 0, len(r.scrapers))
	for _, s := range r.scrapers {
		scrapers = append(scrapers, s)
	}
	return scrapers
}
