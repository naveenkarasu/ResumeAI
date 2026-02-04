/**
 * Job List Page
 *
 * Main page for job search, browsing, and application tracking
 */

import React, { useState, useCallback } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
  searchJobs,
  getJobs,
  getJobDetails,
  createApplication,
  getRecommendations,
  generateCoverLetter,
  getDorkStrategies,
  type JobSearchRequest,
  type JobSearchResponse,
  type JobListingBrief,
  type ApplicationStatus,
  type MatchQuality,
  type LocationType,
  type DorkStrategies,
  type DorkQuery,
} from '../api/jobList';
import { JobTableView, ApplicationKanban, ViewModeToggle, type ViewMode } from '../components/jobs';

// ============== Helper Components ==============

const MatchScoreBadge: React.FC<{ score?: number; quality?: MatchQuality }> = ({ score, quality }) => {
  if (score === undefined || score === null) return null;

  const colors: Record<MatchQuality, string> = {
    excellent: 'bg-green-100 text-green-800 border-green-300',
    good: 'bg-blue-100 text-blue-800 border-blue-300',
    fair: 'bg-yellow-100 text-yellow-800 border-yellow-300',
    poor: 'bg-red-100 text-red-800 border-red-300',
  };

  const colorClass = quality ? colors[quality] : colors.fair;

  return (
    <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium border ${colorClass}`}>
      {Math.round(score)}% Match
    </span>
  );
};

const LocationBadge: React.FC<{ type?: LocationType }> = ({ type }) => {
  if (!type) return null;

  const icons: Record<LocationType, string> = {
    remote: '🌍',
    hybrid: '🏢',
    onsite: '📍',
  };

  const labels: Record<LocationType, string> = {
    remote: 'Remote',
    hybrid: 'Hybrid',
    onsite: 'On-site',
  };

  return (
    <span className="inline-flex items-center gap-1 px-2 py-0.5 bg-gray-100 rounded text-xs text-gray-600">
      {icons[type]} {labels[type]}
    </span>
  );
};

const SourceBadge: React.FC<{ source: string }> = ({ source }) => {
  const colors: Record<string, string> = {
    indeed: 'bg-blue-50 text-blue-700',
    linkedin: 'bg-sky-50 text-sky-700',
    ycombinator: 'bg-orange-50 text-orange-700',
    builtin: 'bg-purple-50 text-purple-700',
    wellfound: 'bg-pink-50 text-pink-700',
    dice: 'bg-red-50 text-red-700',
    github: 'bg-gray-800 text-white',
    simplify: 'bg-indigo-50 text-indigo-700',
    jobright: 'bg-emerald-50 text-emerald-700',
    remoteok: 'bg-teal-50 text-teal-700',
    hackernews: 'bg-orange-100 text-orange-800',
    weworkremotely: 'bg-cyan-50 text-cyan-700',
    google_dork: 'bg-gradient-to-r from-blue-50 to-green-50 text-green-800 border border-green-200',
  };

  // Handle dork_* sources (they come as dork_cyber, dork_swe, etc.)
  const displayName = source.startsWith('dork_') ? 'Web Search' : source;
  const colorKey = source.startsWith('dork_') ? 'google_dork' : source;

  return (
    <span className={`inline-flex items-center px-2 py-0.5 rounded text-xs ${colors[colorKey] || 'bg-gray-50 text-gray-700'}`}>
      {displayName}
    </span>
  );
};

const StatusBadge: React.FC<{ status?: ApplicationStatus }> = ({ status }) => {
  if (!status) return null;

  const colors: Record<ApplicationStatus, string> = {
    saved: 'bg-gray-100 text-gray-700',
    applied: 'bg-blue-100 text-blue-700',
    screening: 'bg-yellow-100 text-yellow-700',
    interview: 'bg-purple-100 text-purple-700',
    offer: 'bg-green-100 text-green-700',
    rejected: 'bg-red-100 text-red-700',
    withdrawn: 'bg-gray-100 text-gray-500',
    accepted: 'bg-green-200 text-green-800',
  };

  return (
    <span className={`inline-flex items-center px-2 py-0.5 rounded text-xs font-medium ${colors[status]}`}>
      {status.charAt(0).toUpperCase() + status.slice(1)}
    </span>
  );
};

// ============== Cover Letter Modal ==============

interface CoverLetterModalProps {
  isOpen: boolean;
  onClose: () => void;
  coverLetter: string;
  wordCount: number;
  highlightsUsed: string[];
  jobTitle?: string;
  companyName?: string;
  isLoading?: boolean;
}

const CoverLetterModal: React.FC<CoverLetterModalProps> = ({
  isOpen,
  onClose,
  coverLetter,
  wordCount,
  highlightsUsed,
  jobTitle,
  companyName,
  isLoading,
}) => {
  const [copied, setCopied] = useState(false);

  const handleCopy = async () => {
    try {
      await navigator.clipboard.writeText(coverLetter);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch (err) {
      console.error('Failed to copy:', err);
    }
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 bg-black/50 z-50 flex items-center justify-center p-4" onClick={onClose}>
      <div
        className="bg-white rounded-lg shadow-xl w-full max-w-3xl max-h-[90vh] flex flex-col"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header */}
        <div className="flex items-center justify-between p-4 border-b border-gray-200">
          <div>
            <h2 className="text-lg font-semibold text-gray-900">Cover Letter</h2>
            {jobTitle && companyName && (
              <p className="text-sm text-gray-500">
                For: {jobTitle} at {companyName}
              </p>
            )}
          </div>
          <button onClick={onClose} className="text-gray-400 hover:text-gray-600">
            <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>

        {/* Content */}
        <div className="flex-1 overflow-y-auto p-6">
          {isLoading ? (
            <div className="flex items-center justify-center h-48">
              <div className="flex items-center gap-3 text-gray-500">
                <svg className="w-6 h-6 animate-spin" viewBox="0 0 24 24">
                  <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" fill="none" />
                  <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
                </svg>
                Generating cover letter...
              </div>
            </div>
          ) : (
            <>
              {/* Cover Letter Text */}
              <div className="prose prose-sm max-w-none text-gray-700 whitespace-pre-wrap leading-relaxed">
                {coverLetter}
              </div>

              {/* Highlights Used */}
              {highlightsUsed.length > 0 && (
                <div className="mt-6 pt-4 border-t border-gray-200">
                  <h3 className="text-sm font-medium text-gray-700 mb-2">Resume Highlights Used</h3>
                  <div className="flex flex-wrap gap-2">
                    {highlightsUsed.map((highlight, idx) => (
                      <span
                        key={idx}
                        className="px-2 py-1 bg-blue-50 text-blue-700 rounded text-xs"
                      >
                        {highlight}
                      </span>
                    ))}
                  </div>
                </div>
              )}
            </>
          )}
        </div>

        {/* Footer */}
        <div className="flex items-center justify-between p-4 border-t border-gray-200 bg-gray-50">
          <span className="text-sm text-gray-500">
            {wordCount > 0 && `${wordCount} words`}
          </span>
          <div className="flex gap-2">
            <button
              onClick={handleCopy}
              disabled={isLoading}
              className="px-4 py-2 text-sm bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50 transition-colors flex items-center gap-2"
            >
              {copied ? (
                <>
                  <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                  </svg>
                  Copied!
                </>
              ) : (
                <>
                  <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 16H6a2 2 0 01-2-2V6a2 2 0 012-2h8a2 2 0 012 2v2m-6 12h8a2 2 0 002-2v-8a2 2 0 00-2-2h-8a2 2 0 00-2 2v8a2 2 0 002 2z" />
                  </svg>
                  Copy to Clipboard
                </>
              )}
            </button>
            <button
              onClick={onClose}
              className="px-4 py-2 text-sm border border-gray-300 rounded-lg hover:bg-gray-100 transition-colors"
            >
              Close
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};

// ============== Timeline Filter ==============

type TimelineFilter = 'all' | '1h' | '6h' | '10h' | '24h' | '7d';

interface TimelineFilterProps {
  value: TimelineFilter;
  onChange: (value: TimelineFilter) => void;
}

const TimelineFilterSelect: React.FC<TimelineFilterProps> = ({ value, onChange }) => {
  const options: { value: TimelineFilter; label: string }[] = [
    { value: 'all', label: 'All Time' },
    { value: '1h', label: 'Last Hour' },
    { value: '6h', label: 'Last 6 Hours' },
    { value: '10h', label: 'Last 10 Hours' },
    { value: '24h', label: 'Last 24 Hours' },
    { value: '7d', label: 'Last 7 Days' },
  ];

  return (
    <select
      value={value}
      onChange={(e) => onChange(e.target.value as TimelineFilter)}
      className="px-3 py-2 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-blue-500"
    >
      {options.map((opt) => (
        <option key={opt.value} value={opt.value}>
          {opt.label}
        </option>
      ))}
    </select>
  );
};

// Helper to filter jobs by timeline
function filterJobsByTimeline(jobs: JobListingBrief[], timeline: TimelineFilter): JobListingBrief[] {
  if (timeline === 'all') return jobs;

  const now = new Date();
  const hoursMap: Record<TimelineFilter, number> = {
    all: Infinity,
    '1h': 1,
    '6h': 6,
    '10h': 10,
    '24h': 24,
    '7d': 24 * 7,
  };

  const maxHours = hoursMap[timeline];
  const cutoff = new Date(now.getTime() - maxHours * 60 * 60 * 1000);

  return jobs.filter((job) => {
    if (!job.posted_date) return false;
    const postedDate = new Date(job.posted_date);
    return postedDate >= cutoff;
  });
}

// Helper to format relative time
function getRelativeTime(dateStr: string): string {
  const date = new Date(dateStr);
  const now = new Date();
  const diffMs = now.getTime() - date.getTime();
  const diffMins = Math.floor(diffMs / 60000);
  const diffHours = Math.floor(diffMs / 3600000);
  const diffDays = Math.floor(diffMs / 86400000);

  if (diffMins < 1) return 'Just now';
  if (diffMins < 60) return `${diffMins}m ago`;
  if (diffHours < 24) return `${diffHours}h ago`;
  if (diffDays === 1) return 'Yesterday';
  if (diffDays < 7) return `${diffDays}d ago`;
  return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
}

// ============== Dork Strategy Selector ==============

interface DorkSelectorProps {
  strategies: DorkStrategies | undefined;
  selectedCategory: string;
  selectedDork: string;
  onCategoryChange: (category: string) => void;
  onDorkChange: (dorkId: string) => void;
  isLoading?: boolean;
}

const DorkSelector: React.FC<DorkSelectorProps> = ({
  strategies,
  selectedCategory,
  selectedDork,
  onCategoryChange,
  onDorkChange,
  isLoading,
}) => {
  if (!strategies) {
    return (
      <div className="flex items-center gap-2 px-3 py-2 bg-gray-100 rounded-lg text-sm text-gray-500">
        {isLoading ? 'Loading search modes...' : 'Web search unavailable'}
      </div>
    );
  }

  const categories = Object.entries(strategies.categories);
  const queriesForCategory = strategies.queries[selectedCategory] || [];

  return (
    <div className="flex flex-wrap items-center gap-2">
      {/* Category Pills */}
      <div className="flex items-center gap-1 p-1 bg-gray-100 rounded-lg">
        <button
          onClick={() => {
            onCategoryChange('');
            onDorkChange('');
          }}
          className={`px-3 py-1.5 text-xs font-medium rounded-md transition-colors ${
            !selectedCategory
              ? 'bg-white shadow-sm text-gray-900'
              : 'text-gray-600 hover:text-gray-900'
          }`}
        >
          All Sources
        </button>
        {categories.slice(0, 6).map(([id, cat]) => (
          <button
            key={id}
            onClick={() => {
              onCategoryChange(id);
              onDorkChange('');
            }}
            title={cat.description}
            className={`px-3 py-1.5 text-xs font-medium rounded-md transition-colors ${
              selectedCategory === id
                ? 'bg-white shadow-sm text-gray-900'
                : 'text-gray-600 hover:text-gray-900'
            }`}
          >
            {cat.icon} {cat.name}
          </button>
        ))}
        {/* More dropdown for remaining categories */}
        {categories.length > 6 && (
          <select
            value={categories.slice(6).some(([id]) => id === selectedCategory) ? selectedCategory : ''}
            onChange={(e) => {
              if (e.target.value) {
                onCategoryChange(e.target.value);
                onDorkChange('');
              }
            }}
            className={`px-2 py-1.5 text-xs font-medium rounded-md bg-transparent border-0 cursor-pointer ${
              categories.slice(6).some(([id]) => id === selectedCategory)
                ? 'text-gray-900'
                : 'text-gray-600'
            }`}
          >
            <option value="">More...</option>
            {categories.slice(6).map(([id, cat]) => (
              <option key={id} value={id}>
                {cat.icon} {cat.name}
              </option>
            ))}
          </select>
        )}
      </div>

      {/* Specific Dork Query Selector */}
      {selectedCategory && queriesForCategory.length > 0 && (
        <select
          value={selectedDork}
          onChange={(e) => onDorkChange(e.target.value)}
          className="px-3 py-2 text-sm border border-blue-200 bg-blue-50 rounded-lg focus:ring-2 focus:ring-blue-500"
        >
          <option value="">Auto-detect best query</option>
          {queriesForCategory.map((query: DorkQuery) => (
            <option key={query.id} value={query.id} title={query.query_preview}>
              {query.name}
            </option>
          ))}
        </select>
      )}

      {/* Selected dork info */}
      {selectedDork && (
        <div className="flex items-center gap-1.5 px-2 py-1 bg-green-50 text-green-700 rounded text-xs">
          <svg className="w-3.5 h-3.5" fill="currentColor" viewBox="0 0 20 20">
            <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clipRule="evenodd" />
          </svg>
          Advanced web search active
        </div>
      )}
    </div>
  );
};

// Time badge with color based on recency
const TimeBadge: React.FC<{ date?: string }> = ({ date }) => {
  if (!date) return null;

  const relativeTime = getRelativeTime(date);
  const dateObj = new Date(date);
  const now = new Date();
  const diffHours = (now.getTime() - dateObj.getTime()) / 3600000;

  // Color based on recency
  let colorClass = 'bg-gray-100 text-gray-600';
  if (diffHours < 1) colorClass = 'bg-green-100 text-green-700';
  else if (diffHours < 6) colorClass = 'bg-blue-100 text-blue-700';
  else if (diffHours < 24) colorClass = 'bg-yellow-100 text-yellow-700';

  return (
    <span className={`inline-flex items-center gap-1 px-2 py-0.5 rounded text-xs ${colorClass}`}>
      <svg className="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
      </svg>
      {relativeTime}
    </span>
  );
};

// ============== Job Card Component ==============

interface JobCardProps {
  job: JobListingBrief;
  onSelect: (id: string) => void;
  onSave: (id: string) => void;
  isSelected?: boolean;
}

const JobCard: React.FC<JobCardProps> = ({ job, onSelect, onSave, isSelected }) => {
  return (
    <div
      className={`bg-white rounded-lg border p-4 hover:shadow-md transition-shadow cursor-pointer ${
        isSelected ? 'ring-2 ring-blue-500 border-blue-500' : 'border-gray-200'
      }`}
      onClick={() => onSelect(job.id)}
    >
      {/* Header */}
      <div className="flex items-start justify-between gap-3">
        <div className="flex items-start gap-3 flex-1 min-w-0">
          {/* Company Logo */}
          <div className="w-12 h-12 rounded-lg bg-gray-100 flex items-center justify-center flex-shrink-0 overflow-hidden">
            {job.company_logo ? (
              <img src={job.company_logo} alt={job.company_name} className="w-full h-full object-contain" />
            ) : (
              <span className="text-gray-400 text-lg font-bold">
                {job.company_name.charAt(0).toUpperCase()}
              </span>
            )}
          </div>

          {/* Title & Company */}
          <div className="flex-1 min-w-0">
            <h3 className="font-semibold text-gray-900 truncate" title={job.title}>
              {job.title}
            </h3>
            <p className="text-sm text-gray-600 truncate">{job.company_name}</p>
          </div>
        </div>

        {/* Match Score */}
        <MatchScoreBadge score={job.match_score} quality={job.match_quality} />
      </div>

      {/* Details */}
      <div className="mt-3 flex flex-wrap items-center gap-2 text-sm">
        {job.location && (
          <span className="text-gray-500 truncate max-w-[150px]" title={job.location}>
            {job.location}
          </span>
        )}
        <LocationBadge type={job.location_type} />
        {job.salary_text && (
          <span className="text-green-600 font-medium">{job.salary_text}</span>
        )}
      </div>

      {/* Footer */}
      <div className="mt-3 flex items-center justify-between">
        <div className="flex items-center gap-2">
          <SourceBadge source={job.source} />
          <TimeBadge date={job.posted_date} />
        </div>

        <div className="flex items-center gap-2">
          {job.application_status ? (
            <StatusBadge status={job.application_status} />
          ) : (
            <button
              onClick={(e) => {
                e.stopPropagation();
                onSave(job.id);
              }}
              className="text-gray-400 hover:text-blue-500 transition-colors"
              title="Save job"
            >
              <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 5a2 2 0 012-2h10a2 2 0 012 2v16l-7-3.5L5 21V5z" />
              </svg>
            </button>
          )}
        </div>
      </div>
    </div>
  );
};

// ============== Search Bar Component ==============

interface SearchBarProps {
  onSearch: (query: string) => void;
  isLoading?: boolean;
}

const SearchBar: React.FC<SearchBarProps> = ({ onSearch, isLoading }) => {
  const [query, setQuery] = useState('');

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (query.trim()) {
      onSearch(query.trim());
    }
  };

  return (
    <form onSubmit={handleSubmit} className="flex gap-2">
      <div className="relative flex-1">
        <input
          type="text"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder='Try: "remote ML engineer jobs $150k+ at startups"'
          className="w-full px-4 py-3 pl-10 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
          disabled={isLoading}
        />
        <svg
          className="absolute left-3 top-1/2 transform -translate-y-1/2 w-5 h-5 text-gray-400"
          fill="none"
          stroke="currentColor"
          viewBox="0 0 24 24"
        >
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
        </svg>
      </div>
      <button
        type="submit"
        disabled={isLoading || !query.trim()}
        className="px-6 py-3 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors font-medium"
      >
        {isLoading ? 'Searching...' : 'Search'}
      </button>
    </form>
  );
};

// ============== Filters Component ==============

interface JobFiltersState {
  location_type: string | undefined;
  source: string | undefined;
  sort_by: string;
  timeline: TimelineFilter;
}

interface FiltersProps {
  filters: JobFiltersState;
  onChange: (filters: JobFiltersState) => void;
}

const Filters: React.FC<FiltersProps> = ({ filters, onChange }) => {
  return (
    <div className="flex flex-wrap gap-4 items-center">
      {/* Timeline Filter */}
      <TimelineFilterSelect
        value={filters.timeline}
        onChange={(timeline) => onChange({ ...filters, timeline })}
      />

      {/* Location Type */}
      <select
        value={filters.location_type || ''}
        onChange={(e) => onChange({ ...filters, location_type: e.target.value || undefined })}
        className="px-3 py-2 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-blue-500"
      >
        <option value="">All Locations</option>
        <option value="remote">Remote</option>
        <option value="hybrid">Hybrid</option>
        <option value="onsite">On-site</option>
      </select>

      {/* Source */}
      <select
        value={filters.source || ''}
        onChange={(e) => onChange({ ...filters, source: e.target.value || undefined })}
        className="px-3 py-2 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-blue-500"
      >
        <option value="">All Sources</option>
        <option value="github">GitHub Jobs</option>
        <option value="simplify">Simplify</option>
        <option value="jobright">Jobright</option>
        <option value="remoteok">RemoteOK</option>
        <option value="hackernews">Hacker News</option>
        <option value="google_dork">Web Search (Dork)</option>
        <option value="indeed">Indeed</option>
        <option value="ycombinator">Y Combinator</option>
        <option value="builtin">BuiltIn</option>
        <option value="linkedin">LinkedIn</option>
        <option value="wellfound">Wellfound</option>
        <option value="dice">Dice</option>
      </select>

      {/* Sort */}
      <select
        value={filters.sort_by}
        onChange={(e) => onChange({ ...filters, sort_by: e.target.value })}
        className="px-3 py-2 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-blue-500"
      >
        <option value="match_score">Best Match</option>
        <option value="posted_date">Most Recent</option>
        <option value="salary">Highest Salary</option>
      </select>
    </div>
  );
};

// ============== Job Detail Panel ==============

interface JobDetailPanelProps {
  jobId: string;
  onClose: () => void;
  onSave: (id: string, status: ApplicationStatus) => void;
  onGenerateCoverLetter: (id: string) => void;
}

const JobDetailPanel: React.FC<JobDetailPanelProps> = ({ jobId, onClose, onSave, onGenerateCoverLetter }) => {
  const { data: job, isLoading } = useQuery({
    queryKey: ['job', jobId],
    queryFn: () => getJobDetails(jobId),
    enabled: !!jobId,
  });

  if (isLoading) {
    return (
      <div className="bg-white rounded-lg border border-gray-200 p-6 animate-pulse">
        <div className="h-6 bg-gray-200 rounded w-3/4 mb-4"></div>
        <div className="h-4 bg-gray-200 rounded w-1/2 mb-6"></div>
        <div className="space-y-3">
          <div className="h-4 bg-gray-200 rounded"></div>
          <div className="h-4 bg-gray-200 rounded"></div>
          <div className="h-4 bg-gray-200 rounded w-5/6"></div>
        </div>
      </div>
    );
  }

  if (!job) {
    return (
      <div className="bg-white rounded-lg border border-gray-200 p-6 text-center text-gray-500">
        Job not found
      </div>
    );
  }

  return (
    <div className="bg-white rounded-lg border border-gray-200 overflow-hidden">
      {/* Header */}
      <div className="p-6 border-b border-gray-200">
        <div className="flex items-start justify-between">
          <div className="flex items-start gap-4">
            <div className="w-16 h-16 rounded-lg bg-gray-100 flex items-center justify-center">
              {job.company.logo_url ? (
                <img src={job.company.logo_url} alt={job.company.name} className="w-full h-full object-contain rounded-lg" />
              ) : (
                <span className="text-gray-400 text-2xl font-bold">
                  {job.company.name.charAt(0).toUpperCase()}
                </span>
              )}
            </div>
            <div>
              <h2 className="text-xl font-bold text-gray-900">{job.title}</h2>
              <p className="text-gray-600">{job.company.name}</p>
              {job.company.rating && (
                <div className="flex items-center gap-1 mt-1">
                  <span className="text-yellow-500">★</span>
                  <span className="text-sm text-gray-600">{job.company.rating.toFixed(1)}</span>
                </div>
              )}
            </div>
          </div>
          <button onClick={onClose} className="text-gray-400 hover:text-gray-600">
            <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>

        {/* Meta */}
        <div className="mt-4 flex flex-wrap gap-3">
          {job.location && <span className="text-gray-600">{job.location}</span>}
          <LocationBadge type={job.location_type} />
          {job.salary_text && <span className="text-green-600 font-semibold">{job.salary_text}</span>}
          <SourceBadge source={job.source} />
        </div>

        {/* Match Info */}
        {job.match_score !== undefined && (
          <div className="mt-4 p-4 bg-gradient-to-r from-blue-50 to-green-50 rounded-lg border border-blue-100">
            <div className="flex items-center justify-between mb-3">
              <div className="flex items-center gap-2">
                <svg className="w-5 h-5 text-blue-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
                </svg>
                <span className="font-semibold text-gray-900">Resume Match Analysis</span>
              </div>
              <MatchScoreBadge score={job.match_score} quality={job.match_quality} />
            </div>

            {/* Match Progress Bar */}
            <div className="mb-3">
              <div className="w-full bg-gray-200 rounded-full h-2">
                <div
                  className={`h-2 rounded-full transition-all ${
                    job.match_quality === 'excellent' ? 'bg-green-500' :
                    job.match_quality === 'good' ? 'bg-blue-500' :
                    job.match_quality === 'fair' ? 'bg-yellow-500' : 'bg-red-500'
                  }`}
                  style={{ width: `${Math.min(100, job.match_score || 0)}%` }}
                />
              </div>
            </div>

            {job.matched_skills.length > 0 && (
              <div className="mt-3">
                <p className="text-xs font-medium text-green-700 mb-1.5 flex items-center gap-1">
                  <svg className="w-3.5 h-3.5" fill="currentColor" viewBox="0 0 20 20">
                    <path fillRule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clipRule="evenodd" />
                  </svg>
                  Matched from Your Resume ({job.matched_skills.length})
                </p>
                <div className="flex flex-wrap gap-1.5">
                  {job.matched_skills.map((skill) => (
                    <span key={skill} className="px-2 py-0.5 bg-green-100 text-green-800 rounded-full text-xs font-medium border border-green-200">
                      {skill}
                    </span>
                  ))}
                </div>
              </div>
            )}
            {job.missing_skills.length > 0 && (
              <div className="mt-3">
                <p className="text-xs font-medium text-yellow-700 mb-1.5 flex items-center gap-1">
                  <svg className="w-3.5 h-3.5" fill="currentColor" viewBox="0 0 20 20">
                    <path fillRule="evenodd" d="M8.257 3.099c.765-1.36 2.722-1.36 3.486 0l5.58 9.92c.75 1.334-.213 2.98-1.742 2.98H4.42c-1.53 0-2.493-1.646-1.743-2.98l5.58-9.92zM11 13a1 1 0 11-2 0 1 1 0 012 0zm-1-8a1 1 0 00-1 1v3a1 1 0 002 0V6a1 1 0 00-1-1z" clipRule="evenodd" />
                  </svg>
                  Skills to Highlight or Develop ({job.missing_skills.length})
                </p>
                <div className="flex flex-wrap gap-1.5">
                  {job.missing_skills.map((skill) => (
                    <span key={skill} className="px-2 py-0.5 bg-yellow-100 text-yellow-800 rounded-full text-xs font-medium border border-yellow-200">
                      {skill}
                    </span>
                  ))}
                </div>
              </div>
            )}

            {/* Resume Match Summary */}
            {job.matched_skills.length > 0 && (
              <div className="mt-3 pt-3 border-t border-blue-200/50">
                <p className="text-xs text-gray-600 italic">
                  Your resume matches {job.matched_skills.length} of {job.matched_skills.length + job.missing_skills.length} key requirements
                </p>
              </div>
            )}
          </div>
        )}
      </div>

      {/* Description */}
      <div className="p-6 max-h-[400px] overflow-y-auto">
        <h3 className="font-semibold text-gray-900 mb-3">Job Description</h3>
        <div className="prose prose-sm max-w-none text-gray-600 whitespace-pre-wrap">
          {job.description}
        </div>

        {job.requirements.length > 0 && (
          <div className="mt-6">
            <h3 className="font-semibold text-gray-900 mb-3">Requirements</h3>
            <ul className="list-disc list-inside space-y-1 text-gray-600 text-sm">
              {job.requirements.map((req, i) => (
                <li key={i}>{req}</li>
              ))}
            </ul>
          </div>
        )}
      </div>

      {/* Actions */}
      <div className="p-4 border-t border-gray-200 bg-gray-50 flex gap-3">
        <a
          href={job.url}
          target="_blank"
          rel="noopener noreferrer"
          className="flex-1 py-2 px-4 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors text-center font-medium"
        >
          Apply on {job.source}
        </a>
        <button
          onClick={() => onSave(job.id, 'saved')}
          className="py-2 px-4 border border-gray-300 rounded-lg hover:bg-gray-100 transition-colors"
        >
          Save
        </button>
        <button
          onClick={() => onGenerateCoverLetter(job.id)}
          className="py-2 px-4 border border-gray-300 rounded-lg hover:bg-gray-100 transition-colors"
        >
          Cover Letter
        </button>
      </div>
    </div>
  );
};

// ============== Main Page Component ==============

const JobListPage: React.FC = () => {
  const queryClient = useQueryClient();
  const [searchQuery, setSearchQuery] = useState<string>('');
  const [selectedJobId, setSelectedJobId] = useState<string | null>(null);
  const [viewMode, setViewMode] = useState<ViewMode>('card');
  const [filters, setFilters] = useState({
    location_type: undefined as string | undefined,
    source: undefined as string | undefined,
    sort_by: 'match_score',
    timeline: 'all' as TimelineFilter,
  });
  const [page, setPage] = useState(1);

  // Dork strategy state
  const [selectedDorkCategory, setSelectedDorkCategory] = useState<string>('');
  const [selectedDorkId, setSelectedDorkId] = useState<string>('');

  // Fetch dork strategies
  const { data: dorkStrategies, isLoading: dorkStrategiesLoading } = useQuery({
    queryKey: ['dork-strategies'],
    queryFn: getDorkStrategies,
    staleTime: 5 * 60 * 1000, // Cache for 5 minutes
  });

  // Cover letter modal state
  const [coverLetterModal, setCoverLetterModal] = useState<{
    isOpen: boolean;
    coverLetter: string;
    wordCount: number;
    highlightsUsed: string[];
    jobTitle?: string;
    companyName?: string;
    isLoading: boolean;
  }>({
    isOpen: false,
    coverLetter: '',
    wordCount: 0,
    highlightsUsed: [],
    isLoading: false,
  });

  // Build search request with optional dork parameters
  const searchRequest: JobSearchRequest | null = searchQuery
    ? {
        query: searchQuery,
        page,
        limit: 20,
        sort_by: filters.sort_by as 'match_score',
        sort_order: 'desc',
        // Include dork filters if selected
        filters: selectedDorkCategory || selectedDorkId ? {
          sources: ['google_dork' as const],
          dork_id: selectedDorkId || undefined,
          dork_category: selectedDorkCategory || undefined,
        } : undefined,
      }
    : null;

  // Fetch jobs
  const { data: searchResults, isLoading, isFetching } = useQuery<JobSearchResponse>({
    queryKey: ['jobs', searchQuery, filters, page, selectedDorkCategory, selectedDorkId],
    queryFn: async () => searchQuery && searchRequest
      ? searchJobs(searchRequest)
      : getJobs({ page, limit: 20, ...filters }),
  });

  // Fetch recommendations (when no search)
  const { data: recommendations } = useQuery({
    queryKey: ['job-recommendations'],
    queryFn: () => getRecommendations(5),
    enabled: !searchQuery && !searchResults?.jobs?.length,
  });

  // Save job mutation
  const saveMutation = useMutation({
    mutationFn: (data: { jobId: string; status: ApplicationStatus }) =>
      createApplication({ job_id: data.jobId, status: data.status }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['jobs'] });
    },
  });

  // Cover letter mutation
  const coverLetterMutation = useMutation({
    mutationFn: (jobId: string) => generateCoverLetter(jobId),
    onSuccess: (data) => {
      setCoverLetterModal((prev) => ({
        ...prev,
        isLoading: false,
        coverLetter: data.cover_letter,
        wordCount: data.word_count,
        highlightsUsed: data.highlights_used || [],
      }));
    },
    onError: (error) => {
      setCoverLetterModal((prev) => ({
        ...prev,
        isLoading: false,
        isOpen: false,
      }));
      alert(`Failed to generate cover letter: ${error}`);
    },
  });

  // Handler for generating cover letter with modal
  const handleGenerateCoverLetter = useCallback(async (jobId: string, jobTitle?: string, companyName?: string) => {
    setCoverLetterModal({
      isOpen: true,
      coverLetter: '',
      wordCount: 0,
      highlightsUsed: [],
      jobTitle,
      companyName,
      isLoading: true,
    });
    coverLetterMutation.mutate(jobId);
  }, [coverLetterMutation]);

  const handleSearch = useCallback((query: string) => {
    setSearchQuery(query);
    setPage(1);
  }, []);

  const handleSaveJob = useCallback((jobId: string, status: ApplicationStatus = 'saved') => {
    saveMutation.mutate({ jobId, status });
  }, [saveMutation]);

  const rawJobs = searchResults?.jobs || [];
  // Apply timeline filter on client side
  const jobs = filterJobsByTimeline(rawJobs, filters.timeline);
  const total = searchResults?.total || 0;
  const pages = searchResults?.pages || 1;

  // Get the current selected job details for the cover letter modal
  const { data: selectedJobData } = useQuery({
    queryKey: ['job', selectedJobId],
    queryFn: () => selectedJobId ? getJobDetails(selectedJobId) : null,
    enabled: !!selectedJobId,
  });

  return (
    <div className="h-full flex flex-col">
      {/* Header */}
      <div className="bg-white border-b border-gray-200 p-6">
        <div className="flex items-center justify-between mb-4">
          <h1 className="text-2xl font-bold text-gray-900">Find Jobs</h1>
          <ViewModeToggle mode={viewMode} onChange={setViewMode} />
        </div>
        {viewMode !== 'kanban' && (
          <>
            <SearchBar onSearch={handleSearch} isLoading={isLoading} />
            {/* Dork Strategy Selector */}
            <div className="mt-3">
              <DorkSelector
                strategies={dorkStrategies}
                selectedCategory={selectedDorkCategory}
                selectedDork={selectedDorkId}
                onCategoryChange={setSelectedDorkCategory}
                onDorkChange={setSelectedDorkId}
                isLoading={dorkStrategiesLoading}
              />
            </div>
            <div className="mt-4">
              <Filters filters={filters} onChange={setFilters} />
            </div>
          </>
        )}
      </div>

      {/* Content */}
      <div className="flex-1 overflow-hidden flex">
        {/* Kanban View */}
        {viewMode === 'kanban' ? (
          <div className="w-full overflow-auto p-6">
            <ApplicationKanban onSelectJob={setSelectedJobId} />
          </div>
        ) : (
          <>
            {/* Job List (Card or Table View) */}
            <div className={`overflow-y-auto p-6 border-r border-gray-200 ${viewMode === 'table' ? 'w-full' : 'w-full lg:w-1/2'}`}>
              {/* Results Header */}
              <div className="flex items-center justify-between mb-4">
                <p className="text-sm text-gray-600">
                  {isLoading ? 'Searching...' : (
                    filters.timeline !== 'all' && jobs.length !== rawJobs.length
                      ? `${jobs.length} of ${total} jobs (filtered by time)`
                      : `${jobs.length} jobs found`
                  )}
                  {searchResults?.cached && <span className="ml-2 text-gray-400">(cached)</span>}
                </p>
                {isFetching && !isLoading && (
                  <span className="text-sm text-blue-600">Updating...</span>
                )}
              </div>

              {/* No Results */}
              {!isLoading && jobs.length === 0 && (
                <div className="text-center py-12">
                  <svg className="w-16 h-16 mx-auto text-gray-300 mb-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1} d="M21 13.255A23.931 23.931 0 0112 15c-3.183 0-6.22-.62-9-1.745M16 6V4a2 2 0 00-2-2h-4a2 2 0 00-2 2v2m4 6h.01M5 20h14a2 2 0 002-2V8a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z" />
                  </svg>
                  <h3 className="text-lg font-medium text-gray-900 mb-2">No jobs found</h3>
                  <p className="text-gray-500">Try a different search or check back later</p>

                  {/* Show recommendations */}
                  {recommendations && recommendations.length > 0 && (
                    <div className="mt-8 text-left">
                      <h4 className="text-sm font-medium text-gray-900 mb-3">Recommended for you</h4>
                      <div className="space-y-3">
                        {recommendations.map((rec) => (
                          <JobCard
                            key={rec.job.id}
                            job={rec.job}
                            onSelect={setSelectedJobId}
                            onSave={(id) => handleSaveJob(id, 'saved')}
                            isSelected={selectedJobId === rec.job.id}
                          />
                        ))}
                      </div>
                    </div>
                  )}
                </div>
              )}

              {/* Table View */}
              {viewMode === 'table' && jobs.length > 0 && (
                <JobTableView
                  jobs={jobs}
                  selectedJobId={selectedJobId}
                  onSelectJob={setSelectedJobId}
                  onSaveJob={(id) => handleSaveJob(id, 'saved')}
                  isLoading={isLoading}
                />
              )}

              {/* Card View */}
              {viewMode === 'card' && jobs.length > 0 && (
                <div className="space-y-4">
                  {jobs.map((job) => (
                    <JobCard
                      key={job.id}
                      job={job}
                      onSelect={setSelectedJobId}
                      onSave={(id) => handleSaveJob(id, 'saved')}
                      isSelected={selectedJobId === job.id}
                    />
                  ))}
                </div>
              )}

              {/* Pagination */}
              {pages > 1 && (
                <div className="mt-6 flex items-center justify-center gap-2">
                  <button
                    onClick={() => setPage((p) => Math.max(1, p - 1))}
                    disabled={page === 1}
                    className="px-3 py-1 border rounded hover:bg-gray-50 disabled:opacity-50"
                  >
                    Previous
                  </button>
                  <span className="text-sm text-gray-600">
                    Page {page} of {pages}
                  </span>
                  <button
                    onClick={() => setPage((p) => Math.min(pages, p + 1))}
                    disabled={page === pages}
                    className="px-3 py-1 border rounded hover:bg-gray-50 disabled:opacity-50"
                  >
                    Next
                  </button>
                </div>
              )}
            </div>

            {/* Job Detail Panel (only show in card view on large screens) */}
            {viewMode === 'card' && (
              <div className="hidden lg:block w-1/2 overflow-y-auto p-6 bg-gray-50">
                {selectedJobId ? (
                  <JobDetailPanel
                    jobId={selectedJobId}
                    onClose={() => setSelectedJobId(null)}
                    onSave={handleSaveJob}
                    onGenerateCoverLetter={(id) => {
                      handleGenerateCoverLetter(
                        id,
                        selectedJobData?.title,
                        selectedJobData?.company.name
                      );
                    }}
                  />
                ) : (
                  <div className="h-full flex items-center justify-center text-gray-400">
                    <div className="text-center">
                      <svg className="w-16 h-16 mx-auto mb-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1} d="M15 15l-2 5L9 9l11 4-5 2zm0 0l5 5M7.188 2.239l.777 2.897M5.136 7.965l-2.898-.777M13.95 4.05l-2.122 2.122m-5.657 5.656l-2.12 2.122" />
                      </svg>
                      <p>Select a job to view details</p>
                    </div>
                  </div>
                )}
              </div>
            )}

            {/* Table view detail panel (shown as modal/sidebar) */}
            {viewMode === 'table' && selectedJobId && (
              <div className="fixed inset-0 bg-black/50 z-50 flex justify-end" onClick={() => setSelectedJobId(null)}>
                <div className="w-full max-w-lg bg-white shadow-xl overflow-y-auto" onClick={(e) => e.stopPropagation()}>
                  <JobDetailPanel
                    jobId={selectedJobId}
                    onClose={() => setSelectedJobId(null)}
                    onSave={handleSaveJob}
                    onGenerateCoverLetter={(id) => {
                      handleGenerateCoverLetter(
                        id,
                        selectedJobData?.title,
                        selectedJobData?.company.name
                      );
                    }}
                  />
                </div>
              </div>
            )}
          </>
        )}
      </div>

      {/* Cover Letter Modal */}
      <CoverLetterModal
        isOpen={coverLetterModal.isOpen}
        onClose={() => setCoverLetterModal((prev) => ({ ...prev, isOpen: false }))}
        coverLetter={coverLetterModal.coverLetter}
        wordCount={coverLetterModal.wordCount}
        highlightsUsed={coverLetterModal.highlightsUsed}
        jobTitle={coverLetterModal.jobTitle}
        companyName={coverLetterModal.companyName}
        isLoading={coverLetterModal.isLoading}
      />
    </div>
  );
};

export default JobListPage;
