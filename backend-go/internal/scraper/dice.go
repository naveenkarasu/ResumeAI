package scraper

import (
	"context"
	"fmt"
	"net/url"
	"regexp"
	"strings"
	"time"

	"github.com/PuerkitoBio/goquery"
	"github.com/google/uuid"
	"go.uber.org/zap"

	"github.com/resume-rag/backend/internal/domain"
)

// DiceScraper scrapes Dice.com job listings (tech-focused)
type DiceScraper struct {
	browser *BrowserPool
	logger  *zap.Logger
}

// NewDiceScraper creates a new Dice scraper
func NewDiceScraper(browser *BrowserPool, logger *zap.Logger) *DiceScraper {
	return &DiceScraper{
		browser: browser,
		logger:  logger,
	}
}

// Name returns the scraper name
func (s *DiceScraper) Name() string {
	return "Dice"
}

// Source returns the job source
func (s *DiceScraper) Source() domain.JobSource {
	return domain.JobSourceDice
}

// Scrape performs the scraping operation
func (s *DiceScraper) Scrape(ctx context.Context, query string, opts *ScrapeOptions) (*ScrapeResult, error) {
	if opts == nil {
		opts = DefaultScrapeOptions()
	}

	result := &ScrapeResult{
		Jobs:      make([]*domain.Job, 0),
		StartTime: time.Now(),
	}

	searchURL := s.buildSearchURL(query, opts)
	s.logger.Info("Starting Dice scrape",
		zap.String("query", query),
		zap.String("url", searchURL),
		zap.Int("maxJobs", opts.MaxJobs),
	)

	// Create browser context
	browserCtx, cancel := s.browser.NewContext(2 * time.Minute)
	defer cancel()

	// Fetch search results
	html, err := s.browser.FetchPage(browserCtx, searchURL, "[data-cy='search-card']")
	if err != nil {
		result.Errors = append(result.Errors, err)
		result.EndTime = time.Now()
		return result, fmt.Errorf("failed to fetch search results: %w", err)
	}

	// Parse HTML
	doc, err := goquery.NewDocumentFromReader(strings.NewReader(html))
	if err != nil {
		result.Errors = append(result.Errors, err)
		result.EndTime = time.Now()
		return result, fmt.Errorf("failed to parse HTML: %w", err)
	}

	// Extract job cards
	jobCards := doc.Find("[data-cy='search-card'], .card-title-link")
	result.Total = jobCards.Length()

	s.logger.Debug("Found job cards", zap.Int("count", result.Total))

	jobCards.Each(func(i int, card *goquery.Selection) {
		if i >= opts.MaxJobs {
			return
		}

		job, err := s.parseJobCard(card)
		if err != nil {
			s.logger.Debug("Failed to parse job card", zap.Error(err))
			result.Errors = append(result.Errors, err)
			return
		}

		result.Jobs = append(result.Jobs, job)
		result.Scraped++
	})

	result.EndTime = time.Now()
	s.logger.Info("Dice scrape completed",
		zap.Int("total", result.Total),
		zap.Int("scraped", result.Scraped),
		zap.Duration("duration", result.Duration()),
	)

	return result, nil
}

// ScrapeJob fetches details for a single job
func (s *DiceScraper) ScrapeJob(ctx context.Context, jobURL string) (*domain.Job, error) {
	browserCtx, cancel := s.browser.NewContext(30 * time.Second)
	defer cancel()

	html, err := s.browser.FetchPage(browserCtx, jobURL, "[data-cy='jobDescription']")
	if err != nil {
		return nil, fmt.Errorf("failed to fetch job page: %w", err)
	}

	doc, err := goquery.NewDocumentFromReader(strings.NewReader(html))
	if err != nil {
		return nil, fmt.Errorf("failed to parse HTML: %w", err)
	}

	return s.parseJobDetails(doc, jobURL)
}

func (s *DiceScraper) buildSearchURL(query string, opts *ScrapeOptions) string {
	baseURL := "https://www.dice.com/jobs"
	params := url.Values{}
	params.Set("q", query)
	params.Set("countryCode", "US")
	params.Set("radius", "30")
	params.Set("radiusUnit", "mi")
	params.Set("page", "1")
	params.Set("pageSize", fmt.Sprintf("%d", opts.MaxJobs))

	if opts.Location != "" {
		params.Set("location", opts.Location)
	}

	if opts.Remote {
		params.Set("filters.isRemote", "true")
	}

	// Time filter
	if opts.PostedWithin > 0 {
		switch {
		case opts.PostedWithin <= 24*time.Hour:
			params.Set("filters.postedDate", "ONE")
		case opts.PostedWithin <= 3*24*time.Hour:
			params.Set("filters.postedDate", "THREE")
		case opts.PostedWithin <= 7*24*time.Hour:
			params.Set("filters.postedDate", "SEVEN")
		}
	}

	return baseURL + "?" + params.Encode()
}

func (s *DiceScraper) parseJobCard(card *goquery.Selection) (*domain.Job, error) {
	job := &domain.Job{
		ID:        uuid.New(),
		Source:    domain.JobSourceDice,
		CreatedAt: time.Now(),
		UpdatedAt: time.Now(),
		IsActive:  true,
	}

	// Extract title
	titleEl := card.Find("[data-cy='card-title-link'], .card-title-link")
	job.Title = strings.TrimSpace(titleEl.Text())
	if job.Title == "" {
		return nil, fmt.Errorf("no title found")
	}

	// Extract URL
	if href, exists := titleEl.Attr("href"); exists {
		if strings.HasPrefix(href, "/") {
			job.SourceURL = "https://www.dice.com" + href
		} else {
			job.SourceURL = href
		}
	}

	// Extract job ID from URL
	if job.SourceURL != "" {
		re := regexp.MustCompile(`/job-detail/([a-f0-9-]+)`)
		if matches := re.FindStringSubmatch(job.SourceURL); len(matches) > 1 {
			job.ExternalID = matches[1]
		}
	}

	// Extract company
	companyEl := card.Find("[data-cy='search-result-company-name'], .card-company")
	companyName := strings.TrimSpace(companyEl.Text())
	if companyName != "" {
		job.Company = &domain.Company{Name: companyName}
	}

	// Extract location
	locationEl := card.Find("[data-cy='search-result-location'], .card-location")
	job.Location = strings.TrimSpace(locationEl.Text())

	// Determine location type
	locationLower := strings.ToLower(job.Location)
	if strings.Contains(locationLower, "remote") {
		job.LocationType = domain.LocationTypeRemote
	} else {
		job.LocationType = domain.LocationTypeOnsite
	}

	// Extract posted date
	dateEl := card.Find("[data-cy='card-posted-date'], .posted-date")
	dateText := strings.TrimSpace(dateEl.Text())
	job.PostedAt = s.parseRelativeDate(dateText)

	// Extract employment type
	typeEl := card.Find("[data-cy='search-result-employment-type']")
	job.EmploymentType = strings.ToLower(strings.TrimSpace(typeEl.Text()))

	return job, nil
}

func (s *DiceScraper) parseJobDetails(doc *goquery.Selection, jobURL string) (*domain.Job, error) {
	job := &domain.Job{
		ID:        uuid.New(),
		Source:    domain.JobSourceDice,
		SourceURL: jobURL,
		CreatedAt: time.Now(),
		UpdatedAt: time.Now(),
		IsActive:  true,
	}

	// Title
	job.Title = strings.TrimSpace(doc.Find("[data-cy='jobTitle'], h1.job-title").Text())

	// Company
	companyEl := doc.Find("[data-cy='companyNameLink'], .company-name")
	if companyName := strings.TrimSpace(companyEl.Text()); companyName != "" {
		job.Company = &domain.Company{Name: companyName}
	}

	// Location
	job.Location = strings.TrimSpace(doc.Find("[data-cy='locationDetails'], .job-location").Text())

	// Description
	descEl := doc.Find("[data-cy='jobDescription'], .job-description")
	job.Description = strings.TrimSpace(descEl.Text())

	// Skills/Technologies
	var skills []string
	doc.Find("[data-cy='skillsList'] li, .skill-badge").Each(func(i int, sel *goquery.Selection) {
		skill := strings.TrimSpace(sel.Text())
		if skill != "" {
			skills = append(skills, skill)
		}
	})
	job.RequiredSkills = skills

	// Extract job ID from URL
	re := regexp.MustCompile(`/job-detail/([a-f0-9-]+)`)
	if matches := re.FindStringSubmatch(jobURL); len(matches) > 1 {
		job.ExternalID = matches[1]
	}

	return job, nil
}

func (s *DiceScraper) parseRelativeDate(text string) *time.Time {
	text = strings.ToLower(text)
	now := time.Now()

	if strings.Contains(text, "today") || strings.Contains(text, "just now") {
		return &now
	}

	// Match "X days ago" or "X day ago"
	re := regexp.MustCompile(`(\d+)\s*day`)
	if matches := re.FindStringSubmatch(text); len(matches) > 1 {
		if days, err := parseInt(matches[1]); err == nil {
			t := now.AddDate(0, 0, -days)
			return &t
		}
	}

	// Match "X hours ago"
	re = regexp.MustCompile(`(\d+)\s*hour`)
	if matches := re.FindStringSubmatch(text); len(matches) > 1 {
		if hours, err := parseInt(matches[1]); err == nil {
			t := now.Add(-time.Duration(hours) * time.Hour)
			return &t
		}
	}

	return nil
}
