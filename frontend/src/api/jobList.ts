/**
 * Job List API Client
 *
 * API client for job search, application tracking, and AI features
 */

import { get, post, put, del } from './client';

// ============== Enums ==============

export type LocationType = 'remote' | 'hybrid' | 'onsite';
export type CompanySize = 'startup' | 'small' | 'medium' | 'large' | 'enterprise';
export type ApplicationStatus = 'saved' | 'applied' | 'screening' | 'interview' | 'offer' | 'rejected' | 'withdrawn' | 'accepted';
export type MatchQuality = 'excellent' | 'good' | 'fair' | 'poor';
export type JobSource = 'linkedin' | 'indeed' | 'wellfound' | 'dice' | 'ycombinator' | 'levelsfyi' | 'builtin' | 'roberthalf' | 'github' | 'simplify' | 'jobright' | 'remoteok' | 'hackernews' | 'weworkremotely' | 'google_dork';
export type ScrapeStatus = 'completed' | 'in_progress' | 'queued' | 'failed';

// ============== Company ==============

export interface Company {
  id: string;
  name: string;
  logo_url?: string;
  website?: string;
  industry?: string;
  size?: CompanySize;
  rating?: number;
}

// ============== Job Listing ==============

export interface JobListingBrief {
  id: string;
  title: string;
  company_name: string;
  company_logo?: string;
  location?: string;
  location_type?: LocationType;
  salary_text?: string;
  posted_date?: string;
  source: JobSource;
  match_score?: number;
  match_quality?: MatchQuality;
  application_status?: ApplicationStatus;
}

export interface JobListing {
  id: string;
  url: string;
  title: string;
  company: Company;
  location?: string;
  location_type?: LocationType;
  salary_min?: number;
  salary_max?: number;
  salary_currency: string;
  salary_text?: string;
  description: string;
  requirements: string[];
  posted_date?: string;
  scraped_at: string;
  source: JobSource;
  is_active: boolean;
  match_score?: number;
  match_quality?: MatchQuality;
  matched_skills: string[];
  missing_skills: string[];
  application_status?: ApplicationStatus;
}

// ============== Search ==============

export interface JobFilters {
  keywords?: string[];
  location?: string;
  location_type?: LocationType[];
  salary_min?: number;
  salary_max?: number;
  company_size?: CompanySize[];
  sources?: JobSource[];
  posted_within_days?: number;
  experience_level?: string;
  industry?: string;
  // Google dorking filters
  dork_id?: string;
  dork_category?: string;
}

export interface JobSearchRequest {
  query?: string;
  filters?: JobFilters;
  include_match_scores?: boolean;
  page?: number;
  limit?: number;
  sort_by?: 'match_score' | 'posted_date' | 'salary';
  sort_order?: 'asc' | 'desc';
}

export interface JobSearchResponse {
  jobs: JobListingBrief[];
  total: number;
  page: number;
  pages: number;
  limit: number;
  search_id?: string;
  cached: boolean;
  scrape_status: ScrapeStatus;
  filters_applied?: JobFilters;
}

// ============== Applications ==============

export interface ApplicationTimelineEntry {
  old_status?: ApplicationStatus;
  new_status: ApplicationStatus;
  changed_at: string;
  notes?: string;
}

export interface Application {
  id: string;
  job: JobListingBrief;
  status: ApplicationStatus;
  applied_date?: string;
  notes?: string;
  resume_version?: string;
  cover_letter?: string;
  reminder_date?: string;
  last_updated: string;
  timeline: ApplicationTimelineEntry[];
}

export interface ApplicationCreate {
  job_id: string;
  status?: ApplicationStatus;
  notes?: string;
  resume_version?: string;
  reminder_date?: string;
}

export interface ApplicationUpdate {
  status?: ApplicationStatus;
  notes?: string;
  cover_letter?: string;
  reminder_date?: string;
}

export interface ApplicationListResponse {
  applications: Application[];
  total: number;
  by_status: Record<string, number>;
}

// ============== Saved Searches ==============

export interface SavedSearch {
  id: string;
  name: string;
  query?: string;
  filters: JobFilters;
  created_at: string;
  last_run_at?: string;
  notification_enabled: boolean;
  result_count?: number;
}

export interface SavedSearchCreate {
  name: string;
  query?: string;
  filters?: JobFilters;
  notification_enabled?: boolean;
}

// ============== AI Features ==============

export interface JobRecommendation {
  job: JobListingBrief;
  recommendation_reason: string;
  relevance_score: number;
}

export interface CoverLetterRequest {
  job_id: string;
  custom_prompt?: string;
  tone?: 'professional' | 'casual' | 'enthusiastic';
  max_words?: number;
}

export interface CoverLetterResponse {
  job_id: string;
  cover_letter: string;
  word_count: number;
  highlights_used: string[];
}

// ============== Google Dorking ==============

export interface DorkQuery {
  id: string;
  name: string;
  description: string;
  query_preview: string;
}

export interface DorkCategory {
  id: string;
  name: string;
  icon: string;
  description: string;
}

export interface DorkStrategies {
  categories: Record<string, { name: string; icon: string; description: string }>;
  queries: Record<string, DorkQuery[]>;
}

// ============== Statistics ==============

export interface JobSearchStats {
  total_jobs_indexed: number;
  jobs_by_source: Record<string, number>;
  jobs_by_location_type: Record<string, number>;
  average_salary?: number;
  last_scrape_at?: string;
}

export interface ApplicationStats {
  total_applications: number;
  by_status: Record<string, number>;
  response_rate?: number;
  average_time_to_response?: number;
  top_matched_skills: string[];
  top_missing_skills: string[];
}

// ============== API Functions ==============

const BASE_PATH = '/job-list';

/**
 * Search for jobs with natural language and filters
 */
export async function searchJobs(request: JobSearchRequest): Promise<JobSearchResponse> {
  return post<JobSearchResponse, JobSearchRequest>(`${BASE_PATH}/search`, request);
}

/**
 * Get paginated list of cached jobs
 */
export async function getJobs(params?: {
  page?: number;
  limit?: number;
  sort_by?: string;
  sort_order?: string;
  location_type?: string;
  source?: string;
}): Promise<JobSearchResponse> {
  const searchParams = new URLSearchParams();
  if (params?.page) searchParams.set('page', String(params.page));
  if (params?.limit) searchParams.set('limit', String(params.limit));
  if (params?.sort_by) searchParams.set('sort_by', params.sort_by);
  if (params?.sort_order) searchParams.set('sort_order', params.sort_order);
  if (params?.location_type) searchParams.set('location_type', params.location_type);
  if (params?.source) searchParams.set('source', params.source);

  const query = searchParams.toString();
  return get<JobSearchResponse>(`${BASE_PATH}/jobs${query ? `?${query}` : ''}`);
}

/**
 * Get full job details with match analysis
 */
export async function getJobDetails(jobId: string): Promise<JobListing> {
  return get<JobListing>(`${BASE_PATH}/jobs/${jobId}`);
}

/**
 * Get AI-recommended jobs based on resume
 */
export async function getRecommendations(limit = 10): Promise<JobRecommendation[]> {
  return get<JobRecommendation[]>(`${BASE_PATH}/recommendations?limit=${limit}`);
}

// ============== Application Tracking ==============

/**
 * Get all tracked applications
 */
export async function getApplications(params?: {
  status?: ApplicationStatus;
  limit?: number;
  offset?: number;
}): Promise<ApplicationListResponse> {
  const searchParams = new URLSearchParams();
  if (params?.status) searchParams.set('status', params.status);
  if (params?.limit) searchParams.set('limit', String(params.limit));
  if (params?.offset) searchParams.set('offset', String(params.offset));

  const query = searchParams.toString();
  return get<ApplicationListResponse>(`${BASE_PATH}/applications${query ? `?${query}` : ''}`);
}

/**
 * Create or update application tracking
 */
export async function createApplication(data: ApplicationCreate): Promise<Application> {
  return post<Application, ApplicationCreate>(`${BASE_PATH}/applications`, data);
}

/**
 * Get application details
 */
export async function getApplication(appId: string): Promise<Application> {
  return get<Application>(`${BASE_PATH}/applications/${appId}`);
}

/**
 * Update application status or details
 */
export async function updateApplication(appId: string, data: ApplicationUpdate): Promise<Application> {
  return put<Application, ApplicationUpdate>(`${BASE_PATH}/applications/${appId}`, data);
}

/**
 * Delete application tracking
 */
export async function deleteApplication(appId: string): Promise<{ success: boolean; message: string }> {
  return del<{ success: boolean; message: string }>(`${BASE_PATH}/applications/${appId}`);
}

/**
 * Get applications with due reminders
 */
export async function getDueReminders(): Promise<Application[]> {
  return get<Application[]>(`${BASE_PATH}/applications/reminders/due`);
}

// ============== Cover Letter ==============

/**
 * Generate a cover letter for a job
 */
export async function generateCoverLetter(
  jobId: string,
  options?: { custom_prompt?: string; tone?: 'professional' | 'casual' | 'enthusiastic'; max_words?: number }
): Promise<CoverLetterResponse> {
  return post<CoverLetterResponse, CoverLetterRequest>(`${BASE_PATH}/jobs/${jobId}/cover-letter`, {
    job_id: jobId,
    ...options,
  });
}

// ============== Saved Searches ==============

/**
 * Get all saved searches
 */
export async function getSavedSearches(): Promise<SavedSearch[]> {
  return get<SavedSearch[]>(`${BASE_PATH}/saved-searches`);
}

/**
 * Save a search preset
 */
export async function saveSearch(data: SavedSearchCreate): Promise<SavedSearch> {
  return post<SavedSearch, SavedSearchCreate>(`${BASE_PATH}/saved-searches`, data);
}

/**
 * Delete a saved search
 */
export async function deleteSavedSearch(searchId: string): Promise<{ success: boolean; message: string }> {
  return del<{ success: boolean; message: string }>(`${BASE_PATH}/saved-searches/${searchId}`);
}

// ============== Scraping ==============

/**
 * Trigger job scraping
 */
export async function triggerScrape(
  keywords: string[],
  location?: string,
  sources?: string[]
): Promise<{ task_id: string; status: string; message: string }> {
  const params = new URLSearchParams();
  keywords.forEach(kw => params.append('keywords', kw));
  if (location) params.set('location', location);
  if (sources) sources.forEach(s => params.append('sources', s));

  return post<{ task_id: string; status: string; message: string }, undefined>(
    `${BASE_PATH}/scrape?${params.toString()}`,
    undefined
  );
}

/**
 * Get scrape task status
 */
export async function getScrapeStatus(taskId: string): Promise<{ task_id: string; status: ScrapeStatus }> {
  return get<{ task_id: string; status: ScrapeStatus }>(`${BASE_PATH}/scrape/status/${taskId}`);
}

// ============== Statistics ==============

/**
 * Get job statistics
 */
export async function getJobStats(): Promise<JobSearchStats> {
  return get<JobSearchStats>(`${BASE_PATH}/stats/jobs`);
}

/**
 * Get application statistics
 */
export async function getApplicationStats(): Promise<ApplicationStats> {
  return get<ApplicationStats>(`${BASE_PATH}/stats/applications`);
}

// ============== Google Dorking ==============

/**
 * Get available dork strategies
 */
export async function getDorkStrategies(): Promise<DorkStrategies> {
  return get<DorkStrategies>(`${BASE_PATH}/dork-strategies`);
}

/**
 * Get dork categories for dropdown
 */
export async function getDorkCategories(): Promise<DorkCategory[]> {
  return get<DorkCategory[]>(`${BASE_PATH}/dork-categories`);
}
