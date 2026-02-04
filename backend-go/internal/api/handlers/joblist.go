package handlers

import (
	"context"

	"github.com/gofiber/fiber/v2"
	"github.com/google/uuid"

	"github.com/resume-rag/backend/internal/domain"
)

// JobListService defines the interface for job list operations
type JobListService interface {
	Search(ctx context.Context, req domain.JobSearchRequest) (*domain.JobSearchResponse, error)
	GetJobs(ctx context.Context, page, limit int, sortBy, sortOrder string, filters *domain.JobFilters) (*domain.JobSearchResponse, error)
	GetJobDetails(ctx context.Context, jobID uuid.UUID) (*domain.Job, error)
	GetRecommendations(ctx context.Context, limit int) ([]domain.JobRecommendation, error)

	// Applications
	GetApplications(ctx context.Context, status *domain.ApplicationStatus, limit, offset int) (*domain.ApplicationListResponse, error)
	CreateApplication(ctx context.Context, req domain.ApplicationCreate) (*domain.Application, error)
	GetApplication(ctx context.Context, appID uuid.UUID) (*domain.Application, error)
	UpdateApplication(ctx context.Context, appID uuid.UUID, req domain.ApplicationUpdate) (*domain.Application, error)
	DeleteApplication(ctx context.Context, appID uuid.UUID) error
	GetDueReminders(ctx context.Context) ([]domain.Application, error)

	// Cover letter
	GenerateCoverLetter(ctx context.Context, jobID uuid.UUID, customPrompt *string) (*domain.CoverLetterResponse, error)

	// Saved searches
	GetSavedSearches(ctx context.Context) ([]domain.SavedSearch, error)
	SaveSearch(ctx context.Context, req domain.SavedSearchCreate) (*domain.SavedSearch, error)
	DeleteSavedSearch(ctx context.Context, searchID uuid.UUID) error

	// Scraping
	TriggerScrape(ctx context.Context, keywords []string, location *string, sources []string) (*domain.ScrapeTask, error)
	GetScrapeStatus(ctx context.Context, taskID uuid.UUID) (*domain.ScrapeTask, error)

	// Statistics
	GetJobStats(ctx context.Context) (*domain.JobSearchStats, error)
	GetApplicationStats(ctx context.Context) (*domain.ApplicationStats, error)
}

// JobListHandler handles job list API requests
type JobListHandler struct {
	service JobListService
}

// NewJobListHandler creates a new job list handler
func NewJobListHandler(service JobListService) *JobListHandler {
	return &JobListHandler{service: service}
}

// Search handles POST /api/job-list/search
func (h *JobListHandler) Search(c *fiber.Ctx) error {
	var req domain.JobSearchRequest
	if err := c.BodyParser(&req); err != nil {
		return c.Status(fiber.StatusBadRequest).JSON(fiber.Map{
			"error":   "invalid_request",
			"message": "Invalid request body",
		})
	}

	// Validate
	if req.Query == nil && req.Filters == nil {
		return c.Status(fiber.StatusBadRequest).JSON(fiber.Map{
			"error":   "invalid_request",
			"message": "Either query or filters must be provided",
		})
	}

	// Set defaults
	if req.Page == 0 {
		req.Page = 1
	}
	if req.Limit == 0 {
		req.Limit = 20
	}
	if req.SortBy == "" {
		req.SortBy = "match_score"
	}
	if req.SortOrder == "" {
		req.SortOrder = "desc"
	}

	result, err := h.service.Search(c.Context(), req)
	if err != nil {
		return c.Status(fiber.StatusInternalServerError).JSON(fiber.Map{
			"error":   "search_failed",
			"message": err.Error(),
		})
	}

	return c.JSON(result)
}

// GetJobs handles GET /api/job-list/jobs
func (h *JobListHandler) GetJobs(c *fiber.Ctx) error {
	page := c.QueryInt("page", 1)
	limit := c.QueryInt("limit", 20)
	sortBy := c.Query("sort_by", "posted_date")
	sortOrder := c.Query("sort_order", "desc")

	// Parse filters
	var filters *domain.JobFilters
	locationType := c.Query("location_type")
	source := c.Query("source")

	if locationType != "" || source != "" {
		filters = &domain.JobFilters{}
		if locationType != "" {
			filters.LocationTypes = []domain.LocationType{domain.LocationType(locationType)}
		}
		if source != "" {
			filters.Sources = []domain.JobSource{domain.JobSource(source)}
		}
	}

	result, err := h.service.GetJobs(c.Context(), page, limit, sortBy, sortOrder, filters)
	if err != nil {
		return c.Status(fiber.StatusInternalServerError).JSON(fiber.Map{
			"error":   "fetch_failed",
			"message": err.Error(),
		})
	}

	return c.JSON(result)
}

// GetJobDetails handles GET /api/job-list/jobs/:job_id
func (h *JobListHandler) GetJobDetails(c *fiber.Ctx) error {
	jobID, err := uuid.Parse(c.Params("job_id"))
	if err != nil {
		return c.Status(fiber.StatusBadRequest).JSON(fiber.Map{
			"error":   "invalid_id",
			"message": "Invalid job ID format",
		})
	}

	job, err := h.service.GetJobDetails(c.Context(), jobID)
	if err != nil {
		return c.Status(fiber.StatusNotFound).JSON(fiber.Map{
			"error":   "not_found",
			"message": "Job not found",
		})
	}

	return c.JSON(job)
}

// GetRecommendations handles GET /api/job-list/recommendations
func (h *JobListHandler) GetRecommendations(c *fiber.Ctx) error {
	limit := c.QueryInt("limit", 10)

	recommendations, err := h.service.GetRecommendations(c.Context(), limit)
	if err != nil {
		return c.Status(fiber.StatusInternalServerError).JSON(fiber.Map{
			"error":   "fetch_failed",
			"message": err.Error(),
		})
	}

	return c.JSON(recommendations)
}

// GetApplications handles GET /api/job-list/applications
func (h *JobListHandler) GetApplications(c *fiber.Ctx) error {
	limit := c.QueryInt("limit", 50)
	offset := c.QueryInt("offset", 0)

	var status *domain.ApplicationStatus
	if s := c.Query("status"); s != "" {
		st := domain.ApplicationStatus(s)
		status = &st
	}

	result, err := h.service.GetApplications(c.Context(), status, limit, offset)
	if err != nil {
		return c.Status(fiber.StatusInternalServerError).JSON(fiber.Map{
			"error":   "fetch_failed",
			"message": err.Error(),
		})
	}

	return c.JSON(result)
}

// CreateApplication handles POST /api/job-list/applications
func (h *JobListHandler) CreateApplication(c *fiber.Ctx) error {
	var req domain.ApplicationCreate
	if err := c.BodyParser(&req); err != nil {
		return c.Status(fiber.StatusBadRequest).JSON(fiber.Map{
			"error":   "invalid_request",
			"message": "Invalid request body",
		})
	}

	app, err := h.service.CreateApplication(c.Context(), req)
	if err != nil {
		return c.Status(fiber.StatusBadRequest).JSON(fiber.Map{
			"error":   "create_failed",
			"message": err.Error(),
		})
	}

	return c.Status(fiber.StatusCreated).JSON(app)
}

// GetApplication handles GET /api/job-list/applications/:app_id
func (h *JobListHandler) GetApplication(c *fiber.Ctx) error {
	appID, err := uuid.Parse(c.Params("app_id"))
	if err != nil {
		return c.Status(fiber.StatusBadRequest).JSON(fiber.Map{
			"error":   "invalid_id",
			"message": "Invalid application ID format",
		})
	}

	app, err := h.service.GetApplication(c.Context(), appID)
	if err != nil {
		return c.Status(fiber.StatusNotFound).JSON(fiber.Map{
			"error":   "not_found",
			"message": "Application not found",
		})
	}

	return c.JSON(app)
}

// UpdateApplication handles PUT /api/job-list/applications/:app_id
func (h *JobListHandler) UpdateApplication(c *fiber.Ctx) error {
	appID, err := uuid.Parse(c.Params("app_id"))
	if err != nil {
		return c.Status(fiber.StatusBadRequest).JSON(fiber.Map{
			"error":   "invalid_id",
			"message": "Invalid application ID format",
		})
	}

	var req domain.ApplicationUpdate
	if err := c.BodyParser(&req); err != nil {
		return c.Status(fiber.StatusBadRequest).JSON(fiber.Map{
			"error":   "invalid_request",
			"message": "Invalid request body",
		})
	}

	app, err := h.service.UpdateApplication(c.Context(), appID, req)
	if err != nil {
		return c.Status(fiber.StatusNotFound).JSON(fiber.Map{
			"error":   "not_found",
			"message": "Application not found",
		})
	}

	return c.JSON(app)
}

// DeleteApplication handles DELETE /api/job-list/applications/:app_id
func (h *JobListHandler) DeleteApplication(c *fiber.Ctx) error {
	appID, err := uuid.Parse(c.Params("app_id"))
	if err != nil {
		return c.Status(fiber.StatusBadRequest).JSON(fiber.Map{
			"error":   "invalid_id",
			"message": "Invalid application ID format",
		})
	}

	if err := h.service.DeleteApplication(c.Context(), appID); err != nil {
		return c.Status(fiber.StatusNotFound).JSON(fiber.Map{
			"error":   "not_found",
			"message": "Application not found",
		})
	}

	return c.JSON(fiber.Map{
		"success": true,
		"message": "Application deleted",
	})
}

// GetDueReminders handles GET /api/job-list/applications/reminders/due
func (h *JobListHandler) GetDueReminders(c *fiber.Ctx) error {
	apps, err := h.service.GetDueReminders(c.Context())
	if err != nil {
		return c.Status(fiber.StatusInternalServerError).JSON(fiber.Map{
			"error":   "fetch_failed",
			"message": err.Error(),
		})
	}

	return c.JSON(apps)
}

// GenerateCoverLetter handles POST /api/job-list/jobs/:job_id/cover-letter
func (h *JobListHandler) GenerateCoverLetter(c *fiber.Ctx) error {
	jobID, err := uuid.Parse(c.Params("job_id"))
	if err != nil {
		return c.Status(fiber.StatusBadRequest).JSON(fiber.Map{
			"error":   "invalid_id",
			"message": "Invalid job ID format",
		})
	}

	var req struct {
		CustomPrompt *string `json:"custom_prompt"`
	}
	_ = c.BodyParser(&req) // Optional body

	result, err := h.service.GenerateCoverLetter(c.Context(), jobID, req.CustomPrompt)
	if err != nil {
		return c.Status(fiber.StatusInternalServerError).JSON(fiber.Map{
			"error":   "generation_failed",
			"message": err.Error(),
		})
	}

	return c.JSON(result)
}

// GetSavedSearches handles GET /api/job-list/saved-searches
func (h *JobListHandler) GetSavedSearches(c *fiber.Ctx) error {
	searches, err := h.service.GetSavedSearches(c.Context())
	if err != nil {
		return c.Status(fiber.StatusInternalServerError).JSON(fiber.Map{
			"error":   "fetch_failed",
			"message": err.Error(),
		})
	}

	return c.JSON(searches)
}

// SaveSearch handles POST /api/job-list/saved-searches
func (h *JobListHandler) SaveSearch(c *fiber.Ctx) error {
	var req domain.SavedSearchCreate
	if err := c.BodyParser(&req); err != nil {
		return c.Status(fiber.StatusBadRequest).JSON(fiber.Map{
			"error":   "invalid_request",
			"message": "Invalid request body",
		})
	}

	search, err := h.service.SaveSearch(c.Context(), req)
	if err != nil {
		return c.Status(fiber.StatusBadRequest).JSON(fiber.Map{
			"error":   "save_failed",
			"message": err.Error(),
		})
	}

	return c.Status(fiber.StatusCreated).JSON(search)
}

// DeleteSavedSearch handles DELETE /api/job-list/saved-searches/:search_id
func (h *JobListHandler) DeleteSavedSearch(c *fiber.Ctx) error {
	searchID, err := uuid.Parse(c.Params("search_id"))
	if err != nil {
		return c.Status(fiber.StatusBadRequest).JSON(fiber.Map{
			"error":   "invalid_id",
			"message": "Invalid search ID format",
		})
	}

	if err := h.service.DeleteSavedSearch(c.Context(), searchID); err != nil {
		return c.Status(fiber.StatusNotFound).JSON(fiber.Map{
			"error":   "not_found",
			"message": "Search not found",
		})
	}

	return c.JSON(fiber.Map{
		"success": true,
		"message": "Search deleted",
	})
}

// TriggerScrape handles POST /api/job-list/scrape
func (h *JobListHandler) TriggerScrape(c *fiber.Ctx) error {
	var req struct {
		Keywords []string  `json:"keywords"`
		Location *string   `json:"location"`
		Sources  []string  `json:"sources"`
	}

	// Also support query params
	keywords := c.QueryArray("keywords")
	if len(keywords) == 0 {
		if err := c.BodyParser(&req); err != nil || len(req.Keywords) == 0 {
			return c.Status(fiber.StatusBadRequest).JSON(fiber.Map{
				"error":   "invalid_request",
				"message": "Keywords are required",
			})
		}
		keywords = req.Keywords
	}

	location := c.Query("location")
	if location == "" && req.Location != nil {
		location = *req.Location
	}
	var locationPtr *string
	if location != "" {
		locationPtr = &location
	}

	sources := c.QueryArray("sources")
	if len(sources) == 0 {
		sources = req.Sources
	}

	task, err := h.service.TriggerScrape(c.Context(), keywords, locationPtr, sources)
	if err != nil {
		return c.Status(fiber.StatusInternalServerError).JSON(fiber.Map{
			"error":   "scrape_failed",
			"message": err.Error(),
		})
	}

	return c.Status(fiber.StatusAccepted).JSON(fiber.Map{
		"task_id": task.ID,
		"status":  task.Status,
		"message": "Scraping started",
	})
}

// GetScrapeStatus handles GET /api/job-list/scrape/status/:task_id
func (h *JobListHandler) GetScrapeStatus(c *fiber.Ctx) error {
	taskID, err := uuid.Parse(c.Params("task_id"))
	if err != nil {
		return c.Status(fiber.StatusBadRequest).JSON(fiber.Map{
			"error":   "invalid_id",
			"message": "Invalid task ID format",
		})
	}

	task, err := h.service.GetScrapeStatus(c.Context(), taskID)
	if err != nil {
		return c.Status(fiber.StatusNotFound).JSON(fiber.Map{
			"error":   "not_found",
			"message": "Task not found",
		})
	}

	return c.JSON(task)
}

// GetJobStats handles GET /api/job-list/stats/jobs
func (h *JobListHandler) GetJobStats(c *fiber.Ctx) error {
	stats, err := h.service.GetJobStats(c.Context())
	if err != nil {
		return c.Status(fiber.StatusInternalServerError).JSON(fiber.Map{
			"error":   "fetch_failed",
			"message": err.Error(),
		})
	}

	return c.JSON(stats)
}

// GetApplicationStats handles GET /api/job-list/stats/applications
func (h *JobListHandler) GetApplicationStats(c *fiber.Ctx) error {
	stats, err := h.service.GetApplicationStats(c.Context())
	if err != nil {
		return c.Status(fiber.StatusInternalServerError).JSON(fiber.Map{
			"error":   "fetch_failed",
			"message": err.Error(),
		})
	}

	return c.JSON(stats)
}
