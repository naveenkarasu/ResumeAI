package scraper

import (
	"context"
	"encoding/json"
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

// WellfoundScraper scrapes Wellfound (formerly AngelList) job listings (startup-focused)
type WellfoundScraper struct {
	browser *BrowserPool
	logger  *zap.Logger
}

// NewWellfoundScraper creates a new Wellfound scraper
func NewWellfoundScraper(browser *BrowserPool, logger *zap.Logger) *WellfoundScraper {
	return &WellfoundScraper{
		browser: browser,
		logger:  logger,
	}
}

// Name returns the scraper name
func (s *WellfoundScraper) Name() string {
	return "Wellfound"
}

// Source returns the job source
func (s *WellfoundScraper) Source() domain.JobSource {
	return domain.JobSourceWellfound
}

// Scrape performs the scraping operation
func (s *WellfoundScraper) Scrape(ctx context.Context, query string, opts *ScrapeOptions) (*ScrapeResult, error) {
	if opts == nil {
		opts = DefaultScrapeOptions()
	}

	result := &ScrapeResult{
		Jobs:      make([]*domain.Job, 0),
		StartTime: time.Now(),
	}

	searchURL := s.buildSearchURL(query, opts)
	s.logger.Info("Starting Wellfound scrape",
		zap.String("query", query),
		zap.String("url", searchURL),
		zap.Int("maxJobs", opts.MaxJobs),
	)

	// Create browser context
	browserCtx, cancel := s.browser.NewContext(2 * time.Minute)
	defer cancel()

	// Fetch search results - Wellfound uses React, need to wait for content
	html, err := s.browser.FetchPage(browserCtx, searchURL, "[data-test='StartupResult']")
	if err != nil {
		// Try alternative selector
		html, err = s.browser.FetchPage(browserCtx, searchURL, ".styles_component__")
		if err != nil {
			result.Errors = append(result.Errors, err)
			result.EndTime = time.Now()
			return result, fmt.Errorf("failed to fetch search results: %w", err)
		}
	}

	// Parse HTML
	doc, err := goquery.NewDocumentFromReader(strings.NewReader(html))
	if err != nil {
		result.Errors = append(result.Errors, err)
		result.EndTime = time.Now()
		return result, fmt.Errorf("failed to parse HTML: %w", err)
	}

	// Extract job cards - Wellfound lists companies with their open roles
	companyCards := doc.Find("[data-test='StartupResult'], .styles_component__")
	s.logger.Debug("Found company cards", zap.Int("count", companyCards.Length()))

	companyCards.Each(func(i int, card *goquery.Selection) {
		if result.Scraped >= opts.MaxJobs {
			return
		}

		// Each company can have multiple job listings
		jobs, err := s.parseCompanyCard(card)
		if err != nil {
			s.logger.Debug("Failed to parse company card", zap.Error(err))
			result.Errors = append(result.Errors, err)
			return
		}

		for _, job := range jobs {
			if result.Scraped >= opts.MaxJobs {
				break
			}
			result.Jobs = append(result.Jobs, job)
			result.Scraped++
		}
	})

	result.Total = result.Scraped
	result.EndTime = time.Now()
	s.logger.Info("Wellfound scrape completed",
		zap.Int("total", result.Total),
		zap.Int("scraped", result.Scraped),
		zap.Duration("duration", result.Duration()),
	)

	return result, nil
}

// ScrapeJob fetches details for a single job
func (s *WellfoundScraper) ScrapeJob(ctx context.Context, jobURL string) (*domain.Job, error) {
	browserCtx, cancel := s.browser.NewContext(30 * time.Second)
	defer cancel()

	html, err := s.browser.FetchPage(browserCtx, jobURL, ".styles_description__")
	if err != nil {
		return nil, fmt.Errorf("failed to fetch job page: %w", err)
	}

	doc, err := goquery.NewDocumentFromReader(strings.NewReader(html))
	if err != nil {
		return nil, fmt.Errorf("failed to parse HTML: %w", err)
	}

	return s.parseJobDetails(doc, jobURL)
}

func (s *WellfoundScraper) buildSearchURL(query string, opts *ScrapeOptions) string {
	// Wellfound uses role-based URLs
	baseURL := "https://wellfound.com/role/l"

	// Map query to role slug
	roleSlug := s.mapQueryToRole(query)

	params := url.Values{}
	if opts.Remote {
		params.Set("remote", "true")
	}
	if opts.Location != "" {
		params.Set("locations[]", opts.Location)
	}

	searchURL := baseURL + "/" + roleSlug
	if len(params) > 0 {
		searchURL += "?" + params.Encode()
	}

	return searchURL
}

func (s *WellfoundScraper) mapQueryToRole(query string) string {
	query = strings.ToLower(query)

	roleMap := map[string]string{
		"software engineer":  "software-engineer",
		"frontend":           "frontend-engineer",
		"backend":            "backend-engineer",
		"full stack":         "full-stack-engineer",
		"fullstack":          "full-stack-engineer",
		"devops":             "devops-engineer",
		"data scientist":     "data-scientist",
		"data engineer":      "data-engineer",
		"machine learning":   "machine-learning-engineer",
		"ml engineer":        "machine-learning-engineer",
		"product manager":    "product-manager",
		"designer":           "designer",
		"ux":                 "ux-designer",
		"mobile":             "mobile-developer",
		"ios":                "ios-developer",
		"android":            "android-developer",
	}

	for key, value := range roleMap {
		if strings.Contains(query, key) {
			return value
		}
	}

	// Default to software engineer
	return "software-engineer"
}

func (s *WellfoundScraper) parseCompanyCard(card *goquery.Selection) ([]*domain.Job, error) {
	var jobs []*domain.Job

	// Extract company info
	companyName := strings.TrimSpace(card.Find("[data-test='StartupName'], .styles_startupName__").Text())
	if companyName == "" {
		companyName = strings.TrimSpace(card.Find("h2").First().Text())
	}

	company := &domain.Company{
		Name: companyName,
	}

	// Extract company details
	companyLink := card.Find("a[href*='/company/']")
	if href, exists := companyLink.Attr("href"); exists {
		company.LinkedInURL = "https://wellfound.com" + href
	}

	// Extract funding/stage info
	stageEl := card.Find("[data-test='StartupSize'], .styles_startupSize__")
	if size := strings.TrimSpace(stageEl.Text()); size != "" {
		company.Size = s.parseCompanySize(size)
	}

	// Extract individual job listings within the company
	jobListings := card.Find("[data-test='JobListing'], .styles_jobListing__")
	if jobListings.Length() == 0 {
		// Try alternative: look for role links
		jobListings = card.Find("a[href*='/jobs/']")
	}

	jobListings.Each(func(i int, listing *goquery.Selection) {
		job := &domain.Job{
			ID:        uuid.New(),
			Source:    domain.JobSourceWellfound,
			Company:   company,
			CreatedAt: time.Now(),
			UpdatedAt: time.Now(),
			IsActive:  true,
		}

		// Extract job title
		titleEl := listing.Find("[data-test='JobTitle'], .styles_jobTitle__")
		if titleEl.Length() == 0 {
			// The listing itself might be the title link
			job.Title = strings.TrimSpace(listing.Text())
		} else {
			job.Title = strings.TrimSpace(titleEl.Text())
		}

		if job.Title == "" {
			return
		}

		// Extract job URL
		if href, exists := listing.Attr("href"); exists {
			if strings.HasPrefix(href, "/") {
				job.SourceURL = "https://wellfound.com" + href
			} else {
				job.SourceURL = href
			}
		} else if link := listing.Find("a").First(); link.Length() > 0 {
			if href, exists := link.Attr("href"); exists {
				if strings.HasPrefix(href, "/") {
					job.SourceURL = "https://wellfound.com" + href
				} else {
					job.SourceURL = href
				}
			}
		}

		// Extract job ID from URL
		if job.SourceURL != "" {
			re := regexp.MustCompile(`/jobs/(\d+)`)
			if matches := re.FindStringSubmatch(job.SourceURL); len(matches) > 1 {
				job.ExternalID = matches[1]
			}
		}

		// Extract location
		locationEl := listing.Find("[data-test='JobLocation'], .styles_location__")
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

		// Extract salary range
		salaryEl := listing.Find("[data-test='JobSalary'], .styles_salary__")
		if salaryText := strings.TrimSpace(salaryEl.Text()); salaryText != "" {
			s.parseSalary(job, salaryText)
		}

		// Extract equity if available
		equityEl := listing.Find("[data-test='JobEquity'], .styles_equity__")
		if equity := strings.TrimSpace(equityEl.Text()); equity != "" {
			if job.Metadata == nil {
				job.Metadata = make(map[string]interface{})
			}
			job.Metadata["equity"] = equity
		}

		jobs = append(jobs, job)
	})

	// If no individual listings found, create one job for the company
	if len(jobs) == 0 && companyName != "" {
		job := &domain.Job{
			ID:        uuid.New(),
			Source:    domain.JobSourceWellfound,
			Company:   company,
			Title:     "Open Positions",
			CreatedAt: time.Now(),
			UpdatedAt: time.Now(),
			IsActive:  true,
		}

		if href, exists := card.Find("a").First().Attr("href"); exists {
			if strings.HasPrefix(href, "/") {
				job.SourceURL = "https://wellfound.com" + href
			}
		}

		jobs = append(jobs, job)
	}

	return jobs, nil
}

func (s *WellfoundScraper) parseJobDetails(doc *goquery.Selection, jobURL string) (*domain.Job, error) {
	job := &domain.Job{
		ID:        uuid.New(),
		Source:    domain.JobSourceWellfound,
		SourceURL: jobURL,
		CreatedAt: time.Now(),
		UpdatedAt: time.Now(),
		IsActive:  true,
	}

	// Title
	job.Title = strings.TrimSpace(doc.Find("h1, .styles_title__").First().Text())

	// Company
	companyEl := doc.Find("[data-test='CompanyName'], .styles_companyName__")
	if companyName := strings.TrimSpace(companyEl.Text()); companyName != "" {
		job.Company = &domain.Company{Name: companyName}
	}

	// Location
	locationEl := doc.Find("[data-test='Location'], .styles_location__")
	job.Location = strings.TrimSpace(locationEl.Text())

	// Description
	descEl := doc.Find("[data-test='JobDescription'], .styles_description__")
	job.Description = strings.TrimSpace(descEl.Text())

	// Skills
	var skills []string
	doc.Find("[data-test='Skill'], .styles_skill__").Each(func(i int, sel *goquery.Selection) {
		skill := strings.TrimSpace(sel.Text())
		if skill != "" {
			skills = append(skills, skill)
		}
	})
	job.RequiredSkills = skills

	// Extract job ID from URL
	re := regexp.MustCompile(`/jobs/(\d+)`)
	if matches := re.FindStringSubmatch(jobURL); len(matches) > 1 {
		job.ExternalID = matches[1]
	}

	return job, nil
}

func (s *WellfoundScraper) parseCompanySize(sizeText string) domain.CompanySize {
	sizeText = strings.ToLower(sizeText)

	if strings.Contains(sizeText, "1-10") {
		return domain.CompanySizeStartup
	} else if strings.Contains(sizeText, "11-50") {
		return domain.CompanySizeSmall
	} else if strings.Contains(sizeText, "51-200") {
		return domain.CompanySizeMedium
	} else if strings.Contains(sizeText, "201-500") || strings.Contains(sizeText, "501-1000") {
		return domain.CompanySizeLarge
	} else if strings.Contains(sizeText, "1000+") || strings.Contains(sizeText, "1001") {
		return domain.CompanySizeEnterprise
	}

	return domain.CompanySizeStartup // Default for Wellfound
}

func (s *WellfoundScraper) parseSalary(job *domain.Job, salaryText string) {
	// Wellfound format: "$100K – $150K" or "$100,000 - $150,000"
	re := regexp.MustCompile(`\$([0-9,]+)K?\s*[–-]\s*\$([0-9,]+)K?`)
	matches := re.FindStringSubmatch(salaryText)

	if len(matches) >= 3 {
		minStr := strings.ReplaceAll(matches[1], ",", "")
		maxStr := strings.ReplaceAll(matches[2], ",", "")

		if min, err := parseInt(minStr); err == nil {
			// If "K" format, multiply by 1000
			if strings.Contains(salaryText, "K") {
				min *= 1000
			}
			job.SalaryMin = &min
		}

		if max, err := parseInt(maxStr); err == nil {
			if strings.Contains(salaryText, "K") {
				max *= 1000
			}
			job.SalaryMax = &max
		}
	}

	job.SalaryCurrency = "USD"
}
