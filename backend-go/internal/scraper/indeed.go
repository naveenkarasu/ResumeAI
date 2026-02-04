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

// IndeedScraper scrapes Indeed job listings
type IndeedScraper struct {
	browser *BrowserPool
	logger  *zap.Logger
}

// NewIndeedScraper creates a new Indeed scraper
func NewIndeedScraper(browser *BrowserPool, logger *zap.Logger) *IndeedScraper {
	return &IndeedScraper{
		browser: browser,
		logger:  logger,
	}
}

// Name returns the scraper name
func (s *IndeedScraper) Name() string {
	return "Indeed"
}

// Source returns the job source
func (s *IndeedScraper) Source() domain.JobSource {
	return domain.JobSourceIndeed
}

// Scrape performs the scraping operation
func (s *IndeedScraper) Scrape(ctx context.Context, query string, opts *ScrapeOptions) (*ScrapeResult, error) {
	if opts == nil {
		opts = DefaultScrapeOptions()
	}

	result := &ScrapeResult{
		Jobs:      make([]*domain.Job, 0),
		StartTime: time.Now(),
	}

	searchURL := s.buildSearchURL(query, opts)
	s.logger.Info("Starting Indeed scrape",
		zap.String("query", query),
		zap.String("url", searchURL),
		zap.Int("maxJobs", opts.MaxJobs),
	)

	// Create browser context
	browserCtx, cancel := s.browser.NewContext(2 * time.Minute)
	defer cancel()

	// Fetch search results
	html, err := s.browser.FetchPage(browserCtx, searchURL, ".jobsearch-ResultsList")
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
	jobCards := doc.Find(".job_seen_beacon, .jobsearch-SerpJobCard, .result")
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
	s.logger.Info("Indeed scrape completed",
		zap.Int("total", result.Total),
		zap.Int("scraped", result.Scraped),
		zap.Duration("duration", result.Duration()),
	)

	return result, nil
}

// ScrapeJob fetches details for a single job
func (s *IndeedScraper) ScrapeJob(ctx context.Context, jobURL string) (*domain.Job, error) {
	browserCtx, cancel := s.browser.NewContext(30 * time.Second)
	defer cancel()

	html, err := s.browser.FetchPage(browserCtx, jobURL, ".jobsearch-JobComponent")
	if err != nil {
		return nil, fmt.Errorf("failed to fetch job page: %w", err)
	}

	doc, err := goquery.NewDocumentFromReader(strings.NewReader(html))
	if err != nil {
		return nil, fmt.Errorf("failed to parse HTML: %w", err)
	}

	return s.parseJobDetails(doc, jobURL)
}

func (s *IndeedScraper) buildSearchURL(query string, opts *ScrapeOptions) string {
	baseURL := "https://www.indeed.com/jobs"
	params := url.Values{}
	params.Set("q", query)

	if opts.Location != "" {
		params.Set("l", opts.Location)
	}

	if opts.Remote {
		params.Set("remotejob", "032b3046-06a3-4876-8dfd-474eb5e7ed11")
	}

	// Time filter
	if opts.PostedWithin > 0 {
		switch {
		case opts.PostedWithin <= 24*time.Hour:
			params.Set("fromage", "1") // Past 24 hours
		case opts.PostedWithin <= 3*24*time.Hour:
			params.Set("fromage", "3") // Past 3 days
		case opts.PostedWithin <= 7*24*time.Hour:
			params.Set("fromage", "7") // Past week
		case opts.PostedWithin <= 14*24*time.Hour:
			params.Set("fromage", "14") // Past 2 weeks
		}
	}

	return baseURL + "?" + params.Encode()
}

func (s *IndeedScraper) parseJobCard(card *goquery.Selection) (*domain.Job, error) {
	job := &domain.Job{
		ID:        uuid.New(),
		Source:    domain.JobSourceIndeed,
		CreatedAt: time.Now(),
		UpdatedAt: time.Now(),
		IsActive:  true,
	}

	// Extract title
	titleLink := card.Find("h2.jobTitle a, a.jcs-JobTitle")
	job.Title = strings.TrimSpace(titleLink.Text())
	if job.Title == "" {
		// Try alternative selector
		job.Title = strings.TrimSpace(card.Find("[data-testid='jobTitle']").Text())
	}
	if job.Title == "" {
		return nil, fmt.Errorf("no title found")
	}

	// Extract company
	companyEl := card.Find(".companyName, [data-testid='company-name']")
	companyName := strings.TrimSpace(companyEl.Text())
	if companyName != "" {
		job.Company = &domain.Company{Name: companyName}
	}

	// Extract location
	locationEl := card.Find(".companyLocation, [data-testid='text-location']")
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

	// Extract job key/ID
	if jobKey, exists := card.Attr("data-jk"); exists {
		job.ExternalID = jobKey
		job.SourceURL = fmt.Sprintf("https://www.indeed.com/viewjob?jk=%s", jobKey)
	} else {
		// Try to find link
		if href, exists := titleLink.Attr("href"); exists {
			if strings.HasPrefix(href, "/") {
				job.SourceURL = "https://www.indeed.com" + href
			} else {
				job.SourceURL = href
			}
			// Extract job key from URL
			re := regexp.MustCompile(`jk=([a-f0-9]+)`)
			if matches := re.FindStringSubmatch(href); len(matches) > 1 {
				job.ExternalID = matches[1]
			}
		}
	}

	// Extract salary if available
	salaryEl := card.Find(".salary-snippet-container, [data-testid='attribute_snippet_testid']")
	if salaryText := strings.TrimSpace(salaryEl.Text()); salaryText != "" {
		s.parseSalary(job, salaryText)
	}

	// Extract snippet/description preview
	snippetEl := card.Find(".job-snippet, [data-testid='jobDescriptionSnippet']")
	job.Description = strings.TrimSpace(snippetEl.Text())

	// Extract posted date
	dateEl := card.Find(".date, [data-testid='myJobsStateDate']")
	dateText := strings.TrimSpace(dateEl.Text())
	job.PostedAt = s.parseRelativeDate(dateText)

	return job, nil
}

func (s *IndeedScraper) parseJobDetails(doc *goquery.Selection, jobURL string) (*domain.Job, error) {
	job := &domain.Job{
		ID:        uuid.New(),
		Source:    domain.JobSourceIndeed,
		SourceURL: jobURL,
		CreatedAt: time.Now(),
		UpdatedAt: time.Now(),
		IsActive:  true,
	}

	// Title
	job.Title = strings.TrimSpace(doc.Find(".jobsearch-JobInfoHeader-title, h1[data-testid='jobsearch-JobInfoHeader-title']").Text())

	// Company
	companyEl := doc.Find(".jobsearch-InlineCompanyRating-companyHeader, [data-testid='inlineHeader-companyName']")
	if companyName := strings.TrimSpace(companyEl.Text()); companyName != "" {
		job.Company = &domain.Company{Name: companyName}
	}

	// Location
	locationEl := doc.Find(".jobsearch-JobInfoHeader-subtitle .jobsearch-JobInfoHeader-locationWrapper")
	job.Location = strings.TrimSpace(locationEl.Text())

	// Full description
	descEl := doc.Find("#jobDescriptionText, .jobsearch-jobDescriptionText")
	job.Description = strings.TrimSpace(descEl.Text())

	// Salary
	salaryEl := doc.Find("#salaryInfoAndJobType, [data-testid='attribute_snippet_testid']")
	if salaryText := strings.TrimSpace(salaryEl.Text()); salaryText != "" {
		s.parseSalary(job, salaryText)
	}

	// Extract job key from URL
	re := regexp.MustCompile(`jk=([a-f0-9]+)`)
	if matches := re.FindStringSubmatch(jobURL); len(matches) > 1 {
		job.ExternalID = matches[1]
	}

	return job, nil
}

func (s *IndeedScraper) parseSalary(job *domain.Job, salaryText string) {
	// Common patterns: "$50,000 - $70,000 a year", "$25 - $30 an hour"
	re := regexp.MustCompile(`\$([0-9,]+)(?:\s*-\s*\$([0-9,]+))?`)
	matches := re.FindStringSubmatch(salaryText)
	if len(matches) > 1 {
		minStr := strings.ReplaceAll(matches[1], ",", "")
		if min, err := parseInt(minStr); err == nil {
			// Check if hourly (multiply by 2080 for annual)
			if strings.Contains(strings.ToLower(salaryText), "hour") {
				min *= 2080
			}
			job.SalaryMin = &min
		}
		if len(matches) > 2 && matches[2] != "" {
			maxStr := strings.ReplaceAll(matches[2], ",", "")
			if max, err := parseInt(maxStr); err == nil {
				if strings.Contains(strings.ToLower(salaryText), "hour") {
					max *= 2080
				}
				job.SalaryMax = &max
			}
		}
	}
	job.SalaryCurrency = "USD"
}

func (s *IndeedScraper) parseRelativeDate(text string) *time.Time {
	text = strings.ToLower(text)
	now := time.Now()

	if strings.Contains(text, "just posted") || strings.Contains(text, "today") {
		return &now
	}

	// Match "X days ago"
	re := regexp.MustCompile(`(\d+)\s*day`)
	if matches := re.FindStringSubmatch(text); len(matches) > 1 {
		if days, err := parseInt(matches[1]); err == nil {
			t := now.AddDate(0, 0, -days)
			return &t
		}
	}

	return nil
}

func parseInt(s string) (int, error) {
	var result int
	_, err := fmt.Sscanf(s, "%d", &result)
	return result, err
}
