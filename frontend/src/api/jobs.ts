// Job Matching API functions

import { get, post, del } from './client';

// === Types ===

export type SkillImportance = 'required' | 'preferred' | 'nice-to-have';
export type MatchQuality = 'excellent' | 'good' | 'fair' | 'poor';

export interface MatchedSkill {
  skill: string;
  source: string;
  relevance: number;
  context?: string;
}

export interface MissingSkill {
  skill: string;
  importance: SkillImportance;
  suggestion: string;
  related_skills?: string[];
}

export interface Recommendation {
  title: string;
  description: string;
  priority: number;
  category: string;
}

export interface ScoreBreakdown {
  skills_match: number;
  experience_match: number;
  education_match: number;
  keywords_match: number;
}

export interface ExtractedRequirements {
  required_skills: string[];
  preferred_skills: string[];
  experience_years?: number;
  experience_level?: string;
  education?: string;
  keywords: string[];
  responsibilities: string[];
}

export interface JobMatchResponse {
  match_id: string;
  overall_score: number;
  quality: MatchQuality;
  scores: ScoreBreakdown;
  requirements: ExtractedRequirements;
  matched_skills: MatchedSkill[];
  missing_skills: MissingSkill[];
  recommendations: Recommendation[];
  job_title?: string;
  company?: string;
  job_url?: string;
  analyzed_at: string;
  resume_used?: string;
}

export interface BatchJobMatchResponse {
  results: JobMatchResponse[];
  total_jobs: number;
  average_score: number;
  best_match?: JobMatchResponse;
}

export interface JobHistoryItem {
  match_id: string;
  job_title?: string;
  company?: string;
  overall_score: number;
  quality: MatchQuality;
  analyzed_at: string;
  job_url?: string;
  notes?: string;
  status: string;
}

export interface JobHistoryResponse {
  items: JobHistoryItem[];
  total_count: number;
  average_score: number;
  best_score: number;
  worst_score: number;
}

export interface SkillFrequency {
  skill: string;
  times_required: number;
  times_matched: number;
  match_rate: number;
}

export interface SkillsAnalytics {
  strongest_skills: SkillFrequency[];
  weakest_skills: SkillFrequency[];
  most_requested: SkillFrequency[];
  improvement_areas: string[];
}

// === Request Types ===

export interface JobMatchRequest {
  job_description: string;
  job_title?: string;
  company?: string;
  job_url?: string;
  resume_id?: string;
}

export interface BatchJobMatchRequest {
  jobs: JobMatchRequest[];
}

// === API Functions ===

export async function matchJob(request: JobMatchRequest): Promise<JobMatchResponse> {
  return post<JobMatchResponse, JobMatchRequest>('/jobs/match', request);
}

export async function batchMatchJobs(request: BatchJobMatchRequest): Promise<BatchJobMatchResponse> {
  return post<BatchJobMatchResponse, BatchJobMatchRequest>('/jobs/batch', request);
}

export async function getJobHistory(limit: number = 50): Promise<JobHistoryResponse> {
  return get<JobHistoryResponse>(`/jobs/history?limit=${limit}`);
}

export async function getJobMatch(matchId: string): Promise<JobMatchResponse> {
  return get<JobMatchResponse>(`/jobs/history/${matchId}`);
}

export async function getSkillsAnalytics(): Promise<SkillsAnalytics> {
  return get<SkillsAnalytics>('/jobs/analytics');
}

export async function clearJobHistory(): Promise<{ message: string }> {
  return del<{ message: string }>('/jobs/history');
}
