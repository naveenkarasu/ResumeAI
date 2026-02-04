/**
 * Job Table View Component
 *
 * Displays jobs in a sortable table format with key columns
 */

import React, { useState } from 'react';
import type {
  JobListingBrief,
  ApplicationStatus,
  MatchQuality,
  LocationType,
} from '../../api/jobList';

// ============== Helper Components ==============

const MatchScoreBadge: React.FC<{ score?: number; quality?: MatchQuality }> = ({ score, quality }) => {
  if (score === undefined || score === null) return <span className="text-gray-400">-</span>;

  const colors: Record<MatchQuality, string> = {
    excellent: 'bg-green-100 text-green-800',
    good: 'bg-blue-100 text-blue-800',
    fair: 'bg-yellow-100 text-yellow-800',
    poor: 'bg-red-100 text-red-800',
  };

  const colorClass = quality ? colors[quality] : colors.fair;

  return (
    <span className={`inline-flex items-center px-2 py-0.5 rounded text-xs font-medium ${colorClass}`}>
      {Math.round(score)}%
    </span>
  );
};

const LocationBadge: React.FC<{ type?: LocationType }> = ({ type }) => {
  if (!type) return <span className="text-gray-400">-</span>;

  const colors: Record<LocationType, string> = {
    remote: 'bg-green-50 text-green-700',
    hybrid: 'bg-blue-50 text-blue-700',
    onsite: 'bg-gray-100 text-gray-700',
  };

  const labels: Record<LocationType, string> = {
    remote: 'Remote',
    hybrid: 'Hybrid',
    onsite: 'On-site',
  };

  return (
    <span className={`inline-flex items-center px-2 py-0.5 rounded text-xs ${colors[type]}`}>
      {labels[type]}
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

// ============== Table Header ==============

type SortField = 'title' | 'company_name' | 'match_score' | 'posted_date' | 'salary_text';
type SortOrder = 'asc' | 'desc';

interface SortConfig {
  field: SortField;
  order: SortOrder;
}

interface TableHeaderProps {
  label: string;
  field?: SortField;
  sortConfig?: SortConfig;
  onSort?: (field: SortField) => void;
  className?: string;
}

const TableHeader: React.FC<TableHeaderProps> = ({ label, field, sortConfig, onSort, className = '' }) => {
  const isSorted = sortConfig && field === sortConfig.field;

  if (!field || !onSort) {
    return (
      <th className={`px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider ${className}`}>
        {label}
      </th>
    );
  }

  return (
    <th
      className={`px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider cursor-pointer hover:bg-gray-100 select-none ${className}`}
      onClick={() => onSort(field)}
    >
      <div className="flex items-center gap-1">
        {label}
        <span className="text-gray-400">
          {isSorted ? (
            sortConfig.order === 'asc' ? '↑' : '↓'
          ) : (
            <span className="opacity-0 group-hover:opacity-50">↕</span>
          )}
        </span>
      </div>
    </th>
  );
};

// ============== Main Table Component ==============

interface JobTableViewProps {
  jobs: JobListingBrief[];
  selectedJobId?: string | null;
  onSelectJob: (id: string) => void;
  onSaveJob: (id: string) => void;
  isLoading?: boolean;
}

const JobTableView: React.FC<JobTableViewProps> = ({
  jobs,
  selectedJobId,
  onSelectJob,
  onSaveJob,
  isLoading,
}) => {
  const [sortConfig, setSortConfig] = useState<SortConfig>({
    field: 'match_score',
    order: 'desc',
  });

  const handleSort = (field: SortField) => {
    setSortConfig((prev) => ({
      field,
      order: prev.field === field && prev.order === 'desc' ? 'asc' : 'desc',
    }));
  };

  // Sort jobs locally
  const sortedJobs = [...jobs].sort((a, b) => {
    const { field, order } = sortConfig;
    let aVal: string | number | undefined;
    let bVal: string | number | undefined;

    switch (field) {
      case 'title':
        aVal = a.title.toLowerCase();
        bVal = b.title.toLowerCase();
        break;
      case 'company_name':
        aVal = a.company_name.toLowerCase();
        bVal = b.company_name.toLowerCase();
        break;
      case 'match_score':
        aVal = a.match_score ?? 0;
        bVal = b.match_score ?? 0;
        break;
      case 'posted_date':
        aVal = a.posted_date ?? '';
        bVal = b.posted_date ?? '';
        break;
      case 'salary_text':
        aVal = a.salary_text ?? '';
        bVal = b.salary_text ?? '';
        break;
    }

    if (aVal === undefined || bVal === undefined) return 0;
    if (aVal < bVal) return order === 'asc' ? -1 : 1;
    if (aVal > bVal) return order === 'asc' ? 1 : -1;
    return 0;
  });

  if (isLoading) {
    return (
      <div className="bg-white rounded-lg border border-gray-200 overflow-hidden">
        <div className="animate-pulse">
          <div className="h-12 bg-gray-100 border-b"></div>
          {[...Array(5)].map((_, i) => (
            <div key={i} className="h-16 border-b last:border-0 flex items-center px-4 gap-4">
              <div className="h-4 bg-gray-200 rounded w-1/4"></div>
              <div className="h-4 bg-gray-200 rounded w-1/6"></div>
              <div className="h-4 bg-gray-200 rounded w-1/6"></div>
              <div className="h-4 bg-gray-200 rounded w-1/8"></div>
            </div>
          ))}
        </div>
      </div>
    );
  }

  if (jobs.length === 0) {
    return (
      <div className="bg-white rounded-lg border border-gray-200 p-8 text-center text-gray-500">
        No jobs found
      </div>
    );
  }

  return (
    <div className="bg-white rounded-lg border border-gray-200 overflow-hidden">
      <div className="overflow-x-auto">
        <table className="min-w-full divide-y divide-gray-200">
          <thead className="bg-gray-50">
            <tr>
              <TableHeader label="Job Title" field="title" sortConfig={sortConfig} onSort={handleSort} className="min-w-[200px]" />
              <TableHeader label="Company" field="company_name" sortConfig={sortConfig} onSort={handleSort} className="min-w-[150px]" />
              <TableHeader label="Location" />
              <TableHeader label="Type" />
              <TableHeader label="Salary" field="salary_text" sortConfig={sortConfig} onSort={handleSort} />
              <TableHeader label="Match" field="match_score" sortConfig={sortConfig} onSort={handleSort} />
              <TableHeader label="Posted" field="posted_date" sortConfig={sortConfig} onSort={handleSort} />
              <TableHeader label="Status" />
              <TableHeader label="" className="w-12" />
            </tr>
          </thead>
          <tbody className="bg-white divide-y divide-gray-200">
            {sortedJobs.map((job) => (
              <tr
                key={job.id}
                className={`hover:bg-gray-50 cursor-pointer transition-colors ${
                  selectedJobId === job.id ? 'bg-blue-50 hover:bg-blue-50' : ''
                }`}
                onClick={() => onSelectJob(job.id)}
              >
                {/* Title */}
                <td className="px-4 py-3">
                  <div className="flex items-center gap-3">
                    <div className="w-8 h-8 rounded bg-gray-100 flex items-center justify-center flex-shrink-0">
                      {job.company_logo ? (
                        <img src={job.company_logo} alt="" className="w-full h-full object-contain rounded" />
                      ) : (
                        <span className="text-gray-400 text-xs font-bold">
                          {job.company_name.charAt(0).toUpperCase()}
                        </span>
                      )}
                    </div>
                    <div className="min-w-0">
                      <p className="text-sm font-medium text-gray-900 truncate max-w-[200px]" title={job.title}>
                        {job.title}
                      </p>
                      <p className="text-xs text-gray-500">{job.source}</p>
                    </div>
                  </div>
                </td>

                {/* Company */}
                <td className="px-4 py-3">
                  <span className="text-sm text-gray-900 truncate block max-w-[150px]" title={job.company_name}>
                    {job.company_name}
                  </span>
                </td>

                {/* Location */}
                <td className="px-4 py-3">
                  <span className="text-sm text-gray-600 truncate block max-w-[120px]" title={job.location}>
                    {job.location || '-'}
                  </span>
                </td>

                {/* Location Type */}
                <td className="px-4 py-3">
                  <LocationBadge type={job.location_type} />
                </td>

                {/* Salary */}
                <td className="px-4 py-3">
                  <span className="text-sm text-green-600 font-medium">
                    {job.salary_text || '-'}
                  </span>
                </td>

                {/* Match Score */}
                <td className="px-4 py-3">
                  <MatchScoreBadge score={job.match_score} quality={job.match_quality} />
                </td>

                {/* Posted Date */}
                <td className="px-4 py-3">
                  <span className="text-sm text-gray-500">
                    {job.posted_date
                      ? new Date(job.posted_date).toLocaleDateString('en-US', { month: 'short', day: 'numeric' })
                      : '-'}
                  </span>
                </td>

                {/* Status */}
                <td className="px-4 py-3">
                  {job.application_status ? (
                    <StatusBadge status={job.application_status} />
                  ) : (
                    <span className="text-gray-400 text-xs">-</span>
                  )}
                </td>

                {/* Actions */}
                <td className="px-4 py-3">
                  {!job.application_status && (
                    <button
                      onClick={(e) => {
                        e.stopPropagation();
                        onSaveJob(job.id);
                      }}
                      className="text-gray-400 hover:text-blue-500 transition-colors p-1"
                      title="Save job"
                    >
                      <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 5a2 2 0 012-2h10a2 2 0 012 2v16l-7-3.5L5 21V5z" />
                      </svg>
                    </button>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
};

export default JobTableView;
