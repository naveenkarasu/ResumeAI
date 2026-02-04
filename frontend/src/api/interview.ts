// Interview API functions

import { get, post } from './client';

export interface InterviewQuestion {
  id: string;
  question: string;
  category: string;
  role_types: string[];
  difficulty: string;
  tips?: string;
}

export interface StarStory {
  situation: string;
  task: string;
  action: string;
  result: string;
  question_fit?: string[];
}

export interface PracticeFeedback {
  score: number;
  relevance_feedback: string;
  structure_feedback: string;
  specificity_feedback: string;
  improvements: string[];
  strengths: string[];
}

export interface Category {
  id: string;
  name: string;
  description: string;
}

export interface RoleType {
  id: string;
  name: string;
  description: string;
}

export async function getQuestions(params?: {
  category?: string;
  role_type?: string;
  difficulty?: string;
  limit?: number;
}): Promise<InterviewQuestion[]> {
  const searchParams = new URLSearchParams();
  if (params?.category) searchParams.set('category', params.category);
  if (params?.role_type) searchParams.set('role_type', params.role_type);
  if (params?.difficulty) searchParams.set('difficulty', params.difficulty);
  if (params?.limit) searchParams.set('limit', params.limit.toString());

  const query = searchParams.toString();
  return get<InterviewQuestion[]>(`/interview/questions${query ? '?' + query : ''}`);
}

export async function getCategories(): Promise<Category[]> {
  return get<Category[]>('/interview/categories');
}

export async function getRoleTypes(): Promise<RoleType[]> {
  return get<RoleType[]>('/interview/roles');
}

export async function generateStar(situation: string, questionContext?: string): Promise<StarStory> {
  return post<StarStory, { situation: string; question_context?: string }>('/interview/star', {
    situation,
    question_context: questionContext,
  });
}

export async function evaluatePractice(
  questionId: string,
  questionText: string,
  userAnswer: string
): Promise<PracticeFeedback> {
  return post<PracticeFeedback, { question_id: string; question_text: string; user_answer: string }>(
    '/interview/practice',
    {
      question_id: questionId,
      question_text: questionText,
      user_answer: userAnswer,
    }
  );
}

export async function researchCompany(companyName: string): Promise<{ company: string; suggestions: string[] }> {
  return get<{ company: string; suggestions: string[] }>(`/interview/company/${encodeURIComponent(companyName)}`);
}
