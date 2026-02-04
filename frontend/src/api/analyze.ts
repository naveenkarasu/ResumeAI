// Analyzer API functions

import { post } from './client';

export interface MatchResult {
  item: string;
  matched: boolean;
  resume_evidence?: string;
}

export interface GapAnalysis {
  requirement: string;
  status: 'met' | 'partial' | 'missing';
  suggestion?: string;
}

export interface AnalysisResponse {
  match_score: number;
  matching_skills: MatchResult[];
  gaps: GapAnalysis[];
  keywords_to_add: string[];
  suggestions: string[];
  summary: string;
  processing_time_ms?: number;
}

export interface AnalyzeRequest {
  job_description: string;
  focus_areas?: string[];
}

export async function analyzeJob(request: AnalyzeRequest): Promise<AnalysisResponse> {
  return post<AnalysisResponse, AnalyzeRequest>('/analyze/job', request);
}

export async function extractKeywords(job_description: string): Promise<string[]> {
  return post<string[], AnalyzeRequest>('/analyze/keywords', { job_description });
}
