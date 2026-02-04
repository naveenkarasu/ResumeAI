// Settings API functions

import { get, put, post } from './client';
import type { SettingsResponse, StatusResponse, SettingsUpdateRequest, BackendInfo } from '../types';

export async function getStatus(): Promise<StatusResponse> {
  return get<StatusResponse>('/status');
}

export async function getSettings(): Promise<SettingsResponse> {
  return get<SettingsResponse>('/settings');
}

export async function updateSettings(settings: SettingsUpdateRequest): Promise<SettingsResponse> {
  return put<SettingsResponse, SettingsUpdateRequest>('/settings', settings);
}

export async function getBackends(): Promise<BackendInfo[]> {
  return get<BackendInfo[]>('/settings/backends');
}

export async function restartServer(): Promise<{ status: string; message: string }> {
  return post<{ status: string; message: string }, object>('/restart', {});
}
