package api

import (
	"github.com/gofiber/fiber/v2"

	"github.com/resume-rag/backend/internal/api/handlers"
	"github.com/resume-rag/backend/internal/config"
)

// SetupRoutes configures all API routes
func SetupRoutes(app *fiber.App, cfg *config.Config, deps *Dependencies) {
	// Health check routes (no prefix)
	app.Get("/health", handlers.HealthCheck(deps.DB))
	app.Get("/ready", handlers.ReadinessCheck(deps.DB, deps.MLClient))
	app.Get("/", handlers.Root(cfg))

	// API routes
	api := app.Group("/api")

	// Chat routes
	chat := api.Group("/chat")
	chatHandler := handlers.NewChatHandler(deps.ChatService)
	chat.Post("/", chatHandler.Chat)
	chat.Get("/suggestions", chatHandler.GetSuggestions)
	chat.Get("/history", chatHandler.GetHistory)
	chat.Delete("/history", chatHandler.ClearHistory)

	// Analyze routes
	analyze := api.Group("/analyze")
	analyzeHandler := handlers.NewAnalyzeHandler(deps.AnalyzerService)
	analyze.Post("/job", analyzeHandler.AnalyzeJob)
	analyze.Post("/keywords", analyzeHandler.ExtractKeywords)

	// Jobs routes (matching)
	jobs := api.Group("/jobs")
	jobsHandler := handlers.NewJobsHandler(deps.JobMatchService)
	jobs.Post("/match", jobsHandler.MatchJob)
	jobs.Post("/batch", jobsHandler.BatchMatch)
	jobs.Get("/history", jobsHandler.GetHistory)
	jobs.Get("/history/:match_id", jobsHandler.GetMatchDetails)
	jobs.Get("/analytics", jobsHandler.GetAnalytics)
	jobs.Delete("/history", jobsHandler.ClearHistory)

	// Interview routes
	interview := api.Group("/interview")
	interviewHandler := handlers.NewInterviewHandler(deps.InterviewService)
	interview.Get("/questions", interviewHandler.GetQuestions)
	interview.Get("/categories", interviewHandler.GetCategories)
	interview.Get("/roles", interviewHandler.GetRoles)
	interview.Post("/star", interviewHandler.GenerateSTAR)
	interview.Post("/practice", interviewHandler.EvaluatePractice)
	interview.Get("/company/:company_name", interviewHandler.GetCompanyResearch)

	// Email routes
	email := api.Group("/email")
	emailHandler := handlers.NewEmailHandler(deps.EmailService)
	email.Post("/generate", emailHandler.Generate)
	email.Post("/application", emailHandler.GenerateApplication)
	email.Post("/followup", emailHandler.GenerateFollowup)
	email.Post("/thankyou", emailHandler.GenerateThankYou)

	// Job List routes (search, applications, scraping)
	jobList := api.Group("/job-list")
	jobListHandler := handlers.NewJobListHandler(deps.JobListService)

	// Search
	jobList.Post("/search", jobListHandler.Search)
	jobList.Get("/jobs", jobListHandler.GetJobs)
	jobList.Get("/jobs/:job_id", jobListHandler.GetJobDetails)
	jobList.Get("/recommendations", jobListHandler.GetRecommendations)

	// Applications
	jobList.Get("/applications", jobListHandler.GetApplications)
	jobList.Post("/applications", jobListHandler.CreateApplication)
	jobList.Get("/applications/reminders/due", jobListHandler.GetDueReminders)
	jobList.Get("/applications/:app_id", jobListHandler.GetApplication)
	jobList.Put("/applications/:app_id", jobListHandler.UpdateApplication)
	jobList.Delete("/applications/:app_id", jobListHandler.DeleteApplication)

	// Cover letter
	jobList.Post("/jobs/:job_id/cover-letter", jobListHandler.GenerateCoverLetter)

	// Saved searches
	jobList.Get("/saved-searches", jobListHandler.GetSavedSearches)
	jobList.Post("/saved-searches", jobListHandler.SaveSearch)
	jobList.Delete("/saved-searches/:search_id", jobListHandler.DeleteSavedSearch)

	// Scraping
	jobList.Post("/scrape", jobListHandler.TriggerScrape)
	jobList.Get("/scrape/status/:task_id", jobListHandler.GetScrapeStatus)

	// Statistics
	jobList.Get("/stats/jobs", jobListHandler.GetJobStats)
	jobList.Get("/stats/applications", jobListHandler.GetApplicationStats)

	// Settings routes
	settings := api.Group("/settings")
	settingsHandler := handlers.NewSettingsHandler(cfg, deps.MLClient)
	settings.Get("/", settingsHandler.GetSettings)
	settings.Put("/", settingsHandler.UpdateSettings)
	settings.Get("/backends", settingsHandler.GetAvailableBackends)
}

// Dependencies holds all service dependencies for handlers
type Dependencies struct {
	DB               interface{} // Will be *pgxpool.Pool
	MLClient         interface{} // Will be ML service gRPC client
	ChatService      handlers.ChatService
	AnalyzerService  handlers.AnalyzerService
	JobMatchService  handlers.JobMatchService
	InterviewService handlers.InterviewService
	EmailService     handlers.EmailService
	JobListService   handlers.JobListService
}
