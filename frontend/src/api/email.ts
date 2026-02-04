// Email API functions

import { post } from './client';

export interface EmailResponse {
  subject: string;
  body: string;
  email_type: string;
  variations?: string[];
}

export interface EmailRequest {
  email_type: 'application' | 'followup' | 'thankyou';
  job_description: string;
  company_name?: string;
  recipient_name?: string;
  tone: 'professional' | 'conversational' | 'enthusiastic';
  length: 'brief' | 'standard' | 'detailed';
  focus?: 'technical' | 'leadership' | 'culture';
}

export async function generateEmail(request: EmailRequest): Promise<EmailResponse> {
  return post<EmailResponse, EmailRequest>('/email/generate', request);
}

export async function generateApplicationEmail(request: EmailRequest): Promise<EmailResponse> {
  return post<EmailResponse, EmailRequest>('/email/application', { ...request, email_type: 'application' });
}

export async function generateFollowupEmail(request: EmailRequest): Promise<EmailResponse> {
  return post<EmailResponse, EmailRequest>('/email/followup', { ...request, email_type: 'followup' });
}

export async function generateThankyouEmail(request: EmailRequest): Promise<EmailResponse> {
  return post<EmailResponse, EmailRequest>('/email/thankyou', { ...request, email_type: 'thankyou' });
}
