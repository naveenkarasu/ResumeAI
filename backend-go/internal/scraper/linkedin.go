package scraper

import (
	"context"
	"fmt"
	"net/url"
	"regexp"
	"strconv"
	"strings"
	"time"

	"github.com/PuerkitoBio/goquery"
	"github.com/chromedp/chromedp"
	"github.com/google/uuid"
	"go.uber.org/zap"

	"github.com/resume-rag/backend/internal/domain"
)

// LinkedInScraper scrapes LinkedIn job listings
type LinkedInScraper struct {
	browser *BrowserPool
	logger  *zap.Logger
}

// NewLinkedInScraper creates a new LinkedIn scraper
func NewLinkedInScraper(browser *BrowserPool, logger *zap.Logger) *LinkedInScraper {
	return &LinkedInScraper{
		browser: browser,
		logger:  logger,
	}
}

// Name returns the scraper name
func (s *LinkedInScraper) Name() string {
	return "LinkedIn"
}

// Source returns the job source
func (s *LinkedInScraper) Source() domain.JobSource {
	return domain.JobSourceLinkedIn
}

// Scrape performs the scraping operation
func (s *LinkedInScraper) Scrape(ctx context.Context, query string, opts *ScrapeOptions) (*ScrapeResult, error) {
	if opts == nil {
		opts = DefaultScrapeOptions()
	}

	result := &ScrapeResult{
		Jobs:      make([]*domain.Job, 0),
		StartTime: time.Now(),
	}

	// Build search URL
	searchURL := s.buildSearchURL(query, opts)
	s.logger.Info("Starting LinkedIn scrape",
		zap.String("query", query),
		zap.String("url", searchURL),
		zap.Int("maxJobs", opts.MaxJobs),
	)

	// Create browser context
	browserCtx, cancel := s.browser.NewContext(2 * time.Minute)
	defer cancel()

	// Fetch search results page
	html, err := s.browser.FetchPage(browserCtx, searchURL, ".jobs-search__results-list")
	if err != nil {
		// Try without login wall
		searchURL = s.buildGuestSearchURL(query, opts)
		html, err = s.browser.FetchPage(browserCtx, searchURL, ".jobs-search__results-list")
		if err != nil {
			result.Errors = append(result.Errors, err)
			result.EndTime = time.Now()
			return result, fmt.Errorf("failed to fetch search results: %w", err)
		}
	}

	// Parse job cards
	doc, err := goquery.NewDocumentFromReader(strings.NewReader(html))
	if err != nil {
		result.Errors = append(result.Errors, err)
		result.EndTime = time.Now()
		return result, fmt.Errorf("failed to parse HTML: %w", err)
	}

	// Extract job cards
	jobCards := doc.Find(".jobs-search__results-list li, .job-search-card")
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
	s.logger.Info("LinkedIn scrape completed",
		zap.Int("total", result.Total),
		zap.Int("scraped", result.Scraped),
		zap.Duration("duration", result.Duration()),
	)

	return result, nil
}

// ScrapeJob fetches details for a single job
func (s *LinkedInScraper) ScrapeJob(ctx context.Context, jobURL string) (*domain.Job, error) {
	browserCtx, cancel := s.browser.NewContext(30 * time.Second)
	defer cancel()

	html, err := s.browser.FetchPage(browserCtx, jobURL, ".job-view-layout")
	if err != nil {
		return nil, fmt.Errorf("failed to fetch job page: %w", err)
	}

	doc, err := goquery.NewDocumentFromReader(strings.NewReader(html))
	if err != nil {
		return nil, fmt.Errorf("failed to parse HTML: %w", err)
	}

	return s.parseJobDetails(doc, jobURL)
}

func (s *LinkedInScraper) buildSearchURL(query string, opts *ScrapeOptions) string {
	baseURL := "https://www.linkedin.com/jobs/search"
	params := url.Values{}
	params.Set("keywords", query)
	params.Set("position", "1")
	params.Set("pageNum", "0")

	if opts.Location != "" {
		params.Set("location", opts.Location)
	}

	if opts.Remote {
		params.Set("f_WT", "2") // Remote filter
	}

	// Time filter
	if opts.PostedWithin > 0 {
		switch {
		case opts.PostedWithin <= 24*time.Hour:
			params.Set("f_TPR", "r86400") // Past 24 hours
		case opts.PostedWithin <= 7*24*time.Hour:
			params.Set("f_TPR", "r604800") // Past week
		case opts.PostedWithin <= 30*24*time.Hour:
			params.Set("f_TPR", "r2592000") // Past month
		}
	}

	return baseURL + "?" + params.Encode()
}

func (s *LinkedInScraper) buildGuestSearchURL(query string, opts *ScrapeOptions) string {
	baseURL := "https://www.linkedin.com/jobs-guest/jobs/api/seeMoreJobPostings/search"
	params := url.Values{}
	params.Set("keywords", query)
	params.Set("start", "0")

	if opts.Location != "" {
		params.Set("location", opts.Location)
	}

	return baseURL + "?" + params.Encode()
}

func (s *LinkedInScraper) parseJobCard(card *goquery.Selection) (*domain.Job, error) {
	job := &domain.Job{
		ID:        uuid.New(),
		Source:    domain.JobSourceLinkedIn,
		CreatedAt: time.Now(),
		UpdatedAt: time.Now(),
		IsActive:  true,
	}

	// Extract title
	titleLink := card.Find(".base-search-card__title, .job-search-card__title")
	job.Title = strings.TrimSpace(titleLink.Text())
	if job.Title == "" {
		return nil, fmt.Errorf("no title found")
	}

	// Extract company name
	companyEl := card.Find(".base-search-card__subtitle, .job-search-card__company-name")
	companyName := strings.TrimSpace(companyEl.Text())
	if companyName != "" {
		job.Company = &domain.Company{Name: companyName}
	}

	// Extract location
	locationEl := card.Find(".job-search-card__location")
	job.Location = strings.TrimSpace(locationEl.Text())

	// Determine location type
	locationLower := strings.ToLower(job.Location)
	if strings.Contains(locationLower, "remote") {
		job.LocationType = domain.LocationTypeRemote
	} else if strings.Contains(locationLower, "hybrid") {
		job.LocationType = domain.LocationTypeHybrid
	} else {
		job.LocationType = domain.LocationTypeOnsite
	}

	// Extract URL
	linkEl := card.Find("a.base-card__full-link, a.job-search-card__link")
	if href, exists := linkEl.Attr("href"); exists {
		job.SourceURL = strings.Split(href, "?")[0] // Remove tracking params
	}

	// Extract job ID from URL
	if job.SourceURL != "" {
		re := regexp.MustCompile(`/view/(\d+)`)
		if matches := re.FindStringSubmatch(job.SourceURL); len(matches) > 1 {
			job.ExternalID = matches[1]
		}
	}

	// Extract posted date
	dateEl := card.Find("time")
	if datetime, exists := dateEl.Attr("datetime"); exists {
		if t, err := time.Parse(time.RFC3339, datetime); err == nil {
			job.PostedAt = &t
		}
	}

	return job, nil
}

func (s *LinkedInScraper) parseJobDetails(doc *goquery.Selection, jobURL string) (*domain.Job, error) {
	job := &domain.Job{
		ID:        uuid.New(),
		Source:    domain.JobSourceLinkedIn,
		SourceURL: jobURL,
		CreatedAt: time.Now(),
		UpdatedAt: time.Now(),
		IsActive:  true,
	}

	// Title
	job.Title = strings.TrimSpace(doc.Find(".job-details-jobs-unified-top-card__job-title, h1.jobs-unified-top-card__job-title").Text())

	// Company
	companyEl := doc.Find(".job-details-jobs-unified-top-card__company-name, .jobs-unified-top-card__company-name")
	if companyName := strings.TrimSpace(companyEl.Text()); companyName != "" {
		job.Company = &domain.Company{Name: companyName}
	}

	// Location
	job.Location = strings.TrimSpace(doc.Find(".job-details-jobs-unified-top-card__bullet, .jobs-unified-top-card__bullet").First().Text())

	// Description
	descEl := doc.Find(".jobs-description__content, .description__text")
	job.Description = strings.TrimSpace(descEl.Text())

	// Employment type
	doc.Find(".job-details-jobs-unified-top-card__job-insight").Each(func(i int, sel *goquery.Selection) {
		text := strings.ToLower(sel.Text())
		if strings.Contains(text, "full-time") {
			job.EmploymentType = "full-time"
		} else if strings.Contains(text, "part-time") {
			job.EmploymentType = "part-time"
		} else if strings.Contains(text, "contract") {
			job.EmploymentType = "contract"
		}
	})

	// Extract job ID
	re := regexp.MustCompile(`/view/(\d+)`)
	if matches := re.FindStringSubmatch(jobURL); len(matches) > 1 {
		job.ExternalID = matches[1]
	}

	return job, nil
}
