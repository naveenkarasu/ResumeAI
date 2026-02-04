import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { getSettings, updateSettings, getStatus } from '../api/settings';
import type { SettingsUpdateRequest } from '../types';
import { useToast } from '../components/ui';

export function SettingsPage() {
  const queryClient = useQueryClient();
  const toast = useToast();

  const { data: settings, isLoading: settingsLoading } = useQuery({
    queryKey: ['settings'],
    queryFn: getSettings,
  });

  const { data: status, isLoading: statusLoading } = useQuery({
    queryKey: ['status'],
    queryFn: getStatus,
  });

  const mutation = useMutation({
    mutationFn: (data: SettingsUpdateRequest) => updateSettings(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['settings'] });
      queryClient.invalidateQueries({ queryKey: ['status'] });
      toast.success('Settings updated');
    },
    onError: () => {
      toast.error('Failed to update settings');
    },
  });

  const handleBackendChange = (backend: string) => {
    mutation.mutate({ backend });
  };

  const handleToggle = (key: keyof SettingsUpdateRequest, value: boolean) => {
    mutation.mutate({ [key]: value });
  };

  if (settingsLoading || statusLoading) {
    return (
      <div className="h-full flex items-center justify-center">
        <div className="text-gray-500">Loading settings...</div>
      </div>
    );
  }

  return (
    <div className="h-full overflow-y-auto">
      {/* Header */}
      <div className="mb-4 md:mb-6">
        <h1 className="text-xl md:text-2xl font-bold text-gray-900">Settings</h1>
        <p className="text-sm text-gray-500 hidden sm:block">Configure your Resume RAG Platform</p>
      </div>

      <div className="space-y-4 md:space-y-6 max-w-2xl">
        {/* System Status */}
        <div className="bg-white rounded-lg border border-gray-200 p-6">
          <h2 className="text-lg font-semibold text-gray-900 mb-4">System Status</h2>
          <div className="grid grid-cols-2 gap-4">
            <div>
              <div className="text-sm text-gray-500">Status</div>
              <div className="flex items-center gap-2 mt-1">
                <span
                  className={`w-2 h-2 rounded-full ${
                    status?.status === 'healthy'
                      ? 'bg-green-500'
                      : status?.status === 'degraded'
                      ? 'bg-yellow-500'
                      : 'bg-red-500'
                  }`}
                />
                <span className="font-medium capitalize">{status?.status || 'Unknown'}</span>
              </div>
            </div>
            <div>
              <div className="text-sm text-gray-500">Version</div>
              <div className="font-medium mt-1">{status?.version || 'N/A'}</div>
            </div>
            <div>
              <div className="text-sm text-gray-500">Indexed Documents</div>
              <div className="font-medium mt-1">{status?.indexed_documents || 0}</div>
            </div>
            <div>
              <div className="text-sm text-gray-500">Active Backend</div>
              <div className="font-medium mt-1">{status?.active_backend || 'None'}</div>
            </div>
          </div>
        </div>

        {/* LLM Backend */}
        <div className="bg-white rounded-lg border border-gray-200 p-6">
          <h2 className="text-lg font-semibold text-gray-900 mb-4">LLM Backend</h2>
          <div className="space-y-3">
            {settings?.available_backends.map((backend) => (
              <label
                key={backend.name}
                className={`flex items-center gap-3 p-3 rounded-lg border cursor-pointer transition-colors ${
                  backend.is_active
                    ? 'border-primary-500 bg-primary-50'
                    : 'border-gray-200 hover:bg-gray-50'
                }`}
              >
                <input
                  type="radio"
                  name="backend"
                  value={backend.name}
                  checked={backend.is_active}
                  onChange={() => handleBackendChange(backend.name)}
                  disabled={mutation.isPending || backend.status !== 'available'}
                  className="text-primary-600"
                />
                <div className="flex-1">
                  <div className="font-medium">{backend.name}</div>
                  <div className="text-sm text-gray-500">{backend.model}</div>
                </div>
                <span
                  className={`px-2 py-0.5 rounded text-xs ${
                    backend.status === 'available'
                      ? 'bg-green-100 text-green-700'
                      : 'bg-red-100 text-red-700'
                  }`}
                >
                  {backend.status === 'available' ? 'Available' : 'Unavailable'}
                </span>
              </label>
            ))}
          </div>
        </div>

        {/* RAG Features */}
        <div className="bg-white rounded-lg border border-gray-200 p-6">
          <h2 className="text-lg font-semibold text-gray-900 mb-4">RAG Features</h2>
          <div className="space-y-4">
            <Toggle
              label="Hybrid Search"
              description="Combine BM25 keyword search with vector semantic search"
              checked={settings?.use_hybrid_search || false}
              onChange={(v) => handleToggle('use_hybrid_search', v)}
              disabled={mutation.isPending}
            />
            <Toggle
              label="HyDE Query Enhancement"
              description="Generate hypothetical documents for better retrieval"
              checked={settings?.use_hyde || false}
              onChange={(v) => handleToggle('use_hyde', v)}
              disabled={mutation.isPending}
            />
            <Toggle
              label="Reranking"
              description="Use cross-encoder to rerank search results"
              checked={settings?.use_reranking || false}
              onChange={(v) => handleToggle('use_reranking', v)}
              disabled={mutation.isPending}
            />
            <Toggle
              label="Grounding"
              description="Verify responses against source documents"
              checked={settings?.use_grounding || false}
              onChange={(v) => handleToggle('use_grounding', v)}
              disabled={mutation.isPending}
            />
          </div>
        </div>
      </div>
    </div>
  );
}

interface ToggleProps {
  label: string;
  description: string;
  checked: boolean;
  onChange: (checked: boolean) => void;
  disabled?: boolean;
}

function Toggle({ label, description, checked, onChange, disabled }: ToggleProps) {
  return (
    <label className="flex items-center justify-between cursor-pointer">
      <div>
        <div className="font-medium text-gray-900">{label}</div>
        <div className="text-sm text-gray-500">{description}</div>
      </div>
      <button
        type="button"
        role="switch"
        aria-checked={checked}
        onClick={() => onChange(!checked)}
        disabled={disabled}
        className={`relative inline-flex h-6 w-11 items-center rounded-full transition-colors ${
          checked ? 'bg-primary-600' : 'bg-gray-200'
        } ${disabled ? 'opacity-50 cursor-not-allowed' : ''}`}
      >
        <span
          className={`inline-block h-4 w-4 transform rounded-full bg-white transition-transform ${
            checked ? 'translate-x-6' : 'translate-x-1'
          }`}
        />
      </button>
    </label>
  );
}
