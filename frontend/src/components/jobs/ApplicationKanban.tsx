/**
 * Application Kanban Board Component
 *
 * Displays job applications in a kanban board with drag-and-drop support
 */

import React, { useState, useCallback } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
  getApplications,
  updateApplication,
  type Application,
  type ApplicationStatus,
  type MatchQuality,
} from '../../api/jobList';

// ============== Constants ==============

const KANBAN_COLUMNS: { status: ApplicationStatus; label: string; color: string }[] = [
  { status: 'saved', label: 'Saved', color: 'bg-gray-100 border-gray-300' },
  { status: 'applied', label: 'Applied', color: 'bg-blue-50 border-blue-300' },
  { status: 'screening', label: 'Screening', color: 'bg-yellow-50 border-yellow-300' },
  { status: 'interview', label: 'Interview', color: 'bg-purple-50 border-purple-300' },
  { status: 'offer', label: 'Offer', color: 'bg-green-50 border-green-300' },
  { status: 'accepted', label: 'Accepted', color: 'bg-green-100 border-green-400' },
  { status: 'rejected', label: 'Rejected', color: 'bg-red-50 border-red-300' },
];

// ============== Helper Components ==============

const MatchScoreBadge: React.FC<{ score?: number; quality?: MatchQuality }> = ({ score, quality }) => {
  if (score === undefined) return null;

  const colors: Record<MatchQuality, string> = {
    excellent: 'bg-green-100 text-green-700',
    good: 'bg-blue-100 text-blue-700',
    fair: 'bg-yellow-100 text-yellow-700',
    poor: 'bg-red-100 text-red-700',
  };

  return (
    <span className={`text-xs px-1.5 py-0.5 rounded ${quality ? colors[quality] : 'bg-gray-100 text-gray-600'}`}>
      {Math.round(score)}%
    </span>
  );
};

// ============== Kanban Card ==============

interface KanbanCardProps {
  application: Application;
  onDragStart: (e: React.DragEvent, app: Application) => void;
  onClick: (app: Application) => void;
}

const KanbanCard: React.FC<KanbanCardProps> = ({ application, onDragStart, onClick }) => {
  const { job } = application;

  return (
    <div
      draggable
      onDragStart={(e) => onDragStart(e, application)}
      onClick={() => onClick(application)}
      className="bg-white rounded-lg border border-gray-200 p-3 shadow-sm hover:shadow-md transition-shadow cursor-pointer group"
    >
      {/* Header */}
      <div className="flex items-start gap-2">
        <div className="w-8 h-8 rounded bg-gray-100 flex items-center justify-center flex-shrink-0">
          {job.company_logo ? (
            <img src={job.company_logo} alt="" className="w-full h-full object-contain rounded" />
          ) : (
            <span className="text-gray-400 text-xs font-bold">
              {job.company_name.charAt(0).toUpperCase()}
            </span>
          )}
        </div>
        <div className="min-w-0 flex-1">
          <p className="text-sm font-medium text-gray-900 truncate" title={job.title}>
            {job.title}
          </p>
          <p className="text-xs text-gray-500 truncate">{job.company_name}</p>
        </div>
      </div>

      {/* Details */}
      <div className="mt-2 flex flex-wrap items-center gap-2">
        <MatchScoreBadge score={job.match_score} quality={job.match_quality} />
        {job.location_type && (
          <span className="text-xs text-gray-500">
            {job.location_type === 'remote' ? '🌍' : job.location_type === 'hybrid' ? '🏢' : '📍'}
          </span>
        )}
        {job.salary_text && (
          <span className="text-xs text-green-600">{job.salary_text}</span>
        )}
      </div>

      {/* Footer */}
      <div className="mt-2 flex items-center justify-between text-xs text-gray-400">
        <span>{job.source}</span>
        {application.applied_date && (
          <span>Applied {new Date(application.applied_date).toLocaleDateString('en-US', { month: 'short', day: 'numeric' })}</span>
        )}
      </div>

      {/* Notes indicator */}
      {application.notes && (
        <div className="mt-2 text-xs text-gray-500 truncate" title={application.notes}>
          📝 {application.notes}
        </div>
      )}

      {/* Reminder indicator */}
      {application.reminder_date && new Date(application.reminder_date) > new Date() && (
        <div className="mt-1 text-xs text-orange-500">
          ⏰ {new Date(application.reminder_date).toLocaleDateString()}
        </div>
      )}

      {/* Drag handle indicator */}
      <div className="absolute top-2 right-2 opacity-0 group-hover:opacity-50 transition-opacity">
        <svg className="w-4 h-4 text-gray-400" fill="currentColor" viewBox="0 0 24 24">
          <path d="M8 6a2 2 0 1 1-4 0 2 2 0 0 1 4 0ZM8 12a2 2 0 1 1-4 0 2 2 0 0 1 4 0ZM8 18a2 2 0 1 1-4 0 2 2 0 0 1 4 0ZM14 6a2 2 0 1 1-4 0 2 2 0 0 1 4 0ZM14 12a2 2 0 1 1-4 0 2 2 0 0 1 4 0ZM14 18a2 2 0 1 1-4 0 2 2 0 0 1 4 0Z" />
        </svg>
      </div>
    </div>
  );
};

// ============== Kanban Column ==============

interface KanbanColumnProps {
  status: ApplicationStatus;
  label: string;
  color: string;
  applications: Application[];
  onDragStart: (e: React.DragEvent, app: Application) => void;
  onDragOver: (e: React.DragEvent) => void;
  onDrop: (e: React.DragEvent, status: ApplicationStatus) => void;
  onCardClick: (app: Application) => void;
  isDropTarget: boolean;
}

const KanbanColumn: React.FC<KanbanColumnProps> = ({
  status,
  label,
  color,
  applications,
  onDragStart,
  onDragOver,
  onDrop,
  onCardClick,
  isDropTarget,
}) => {
  return (
    <div
      className={`flex-shrink-0 w-72 flex flex-col rounded-lg border-2 ${color} ${
        isDropTarget ? 'ring-2 ring-blue-400 ring-offset-2' : ''
      }`}
      onDragOver={onDragOver}
      onDrop={(e) => onDrop(e, status)}
    >
      {/* Column Header */}
      <div className="px-3 py-2 border-b border-gray-200 bg-white/50 rounded-t-lg">
        <div className="flex items-center justify-between">
          <h3 className="font-medium text-gray-900">{label}</h3>
          <span className="text-sm text-gray-500 bg-white px-2 py-0.5 rounded-full">
            {applications.length}
          </span>
        </div>
      </div>

      {/* Cards */}
      <div className="flex-1 p-2 space-y-2 overflow-y-auto min-h-[200px] max-h-[calc(100vh-300px)]">
        {applications.length === 0 ? (
          <div className="text-center py-8 text-gray-400 text-sm">
            Drop jobs here
          </div>
        ) : (
          applications.map((app) => (
            <KanbanCard
              key={app.id}
              application={app}
              onDragStart={onDragStart}
              onClick={onCardClick}
            />
          ))
        )}
      </div>
    </div>
  );
};

// ============== Application Detail Modal ==============

interface ApplicationModalProps {
  application: Application;
  onClose: () => void;
  onUpdateStatus: (status: ApplicationStatus) => void;
  onUpdateNotes: (notes: string) => void;
}

const ApplicationModal: React.FC<ApplicationModalProps> = ({
  application,
  onClose,
  onUpdateStatus,
  onUpdateNotes,
}) => {
  const [notes, setNotes] = useState(application.notes || '');
  const [isEditingNotes, setIsEditingNotes] = useState(false);

  const handleSaveNotes = () => {
    onUpdateNotes(notes);
    setIsEditingNotes(false);
  };

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4" onClick={onClose}>
      <div
        className="bg-white rounded-xl shadow-xl max-w-lg w-full max-h-[90vh] overflow-hidden"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header */}
        <div className="p-4 border-b border-gray-200">
          <div className="flex items-start justify-between">
            <div className="flex items-start gap-3">
              <div className="w-12 h-12 rounded-lg bg-gray-100 flex items-center justify-center">
                {application.job.company_logo ? (
                  <img src={application.job.company_logo} alt="" className="w-full h-full object-contain rounded-lg" />
                ) : (
                  <span className="text-gray-400 text-lg font-bold">
                    {application.job.company_name.charAt(0)}
                  </span>
                )}
              </div>
              <div>
                <h2 className="text-lg font-semibold text-gray-900">{application.job.title}</h2>
                <p className="text-gray-600">{application.job.company_name}</p>
              </div>
            </div>
            <button onClick={onClose} className="text-gray-400 hover:text-gray-600">
              <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
              </svg>
            </button>
          </div>
        </div>

        {/* Content */}
        <div className="p-4 space-y-4 overflow-y-auto max-h-[60vh]">
          {/* Status */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">Status</label>
            <div className="flex flex-wrap gap-2">
              {KANBAN_COLUMNS.map(({ status, label }) => (
                <button
                  key={status}
                  onClick={() => onUpdateStatus(status)}
                  className={`px-3 py-1 rounded-full text-sm font-medium transition-colors ${
                    application.status === status
                      ? 'bg-blue-600 text-white'
                      : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
                  }`}
                >
                  {label}
                </button>
              ))}
            </div>
          </div>

          {/* Timeline */}
          {application.timeline.length > 0 && (
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">Timeline</label>
              <div className="space-y-2">
                {application.timeline.map((entry, i) => (
                  <div key={i} className="flex items-center gap-2 text-sm">
                    <span className="text-gray-400">
                      {new Date(entry.changed_at).toLocaleDateString()}
                    </span>
                    <span className="text-gray-600">
                      {entry.old_status ? `${entry.old_status} → ` : ''}{entry.new_status}
                    </span>
                    {entry.notes && <span className="text-gray-500">({entry.notes})</span>}
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Notes */}
          <div>
            <div className="flex items-center justify-between mb-2">
              <label className="block text-sm font-medium text-gray-700">Notes</label>
              {!isEditingNotes && (
                <button
                  onClick={() => setIsEditingNotes(true)}
                  className="text-sm text-blue-600 hover:text-blue-700"
                >
                  Edit
                </button>
              )}
            </div>
            {isEditingNotes ? (
              <div className="space-y-2">
                <textarea
                  value={notes}
                  onChange={(e) => setNotes(e.target.value)}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent resize-none"
                  rows={4}
                  placeholder="Add notes about this application..."
                />
                <div className="flex gap-2">
                  <button
                    onClick={handleSaveNotes}
                    className="px-3 py-1 bg-blue-600 text-white rounded text-sm hover:bg-blue-700"
                  >
                    Save
                  </button>
                  <button
                    onClick={() => {
                      setNotes(application.notes || '');
                      setIsEditingNotes(false);
                    }}
                    className="px-3 py-1 border border-gray-300 rounded text-sm hover:bg-gray-50"
                  >
                    Cancel
                  </button>
                </div>
              </div>
            ) : (
              <p className="text-sm text-gray-600 bg-gray-50 rounded-lg p-3">
                {application.notes || 'No notes yet'}
              </p>
            )}
          </div>

          {/* Details */}
          <div className="grid grid-cols-2 gap-4 text-sm">
            {application.applied_date && (
              <div>
                <span className="text-gray-500">Applied:</span>
                <span className="ml-2 text-gray-900">
                  {new Date(application.applied_date).toLocaleDateString()}
                </span>
              </div>
            )}
            {application.reminder_date && (
              <div>
                <span className="text-gray-500">Reminder:</span>
                <span className="ml-2 text-gray-900">
                  {new Date(application.reminder_date).toLocaleDateString()}
                </span>
              </div>
            )}
            <div>
              <span className="text-gray-500">Match:</span>
              <span className="ml-2">
                <MatchScoreBadge score={application.job.match_score} quality={application.job.match_quality} />
              </span>
            </div>
            <div>
              <span className="text-gray-500">Source:</span>
              <span className="ml-2 text-gray-900">{application.job.source}</span>
            </div>
          </div>
        </div>

        {/* Footer */}
        <div className="p-4 border-t border-gray-200 bg-gray-50 flex justify-end">
          <button
            onClick={onClose}
            className="px-4 py-2 bg-gray-200 text-gray-700 rounded-lg hover:bg-gray-300 transition-colors"
          >
            Close
          </button>
        </div>
      </div>
    </div>
  );
};

// ============== Main Kanban Component ==============

interface ApplicationKanbanProps {
  onSelectJob?: (jobId: string) => void;
}

const ApplicationKanban: React.FC<ApplicationKanbanProps> = ({ onSelectJob: _onSelectJob }) => {
  const queryClient = useQueryClient();
  const [draggedApp, setDraggedApp] = useState<Application | null>(null);
  const [dropTarget, setDropTarget] = useState<ApplicationStatus | null>(null);
  const [selectedApp, setSelectedApp] = useState<Application | null>(null);

  // Fetch applications
  const { data: applicationsData, isLoading } = useQuery({
    queryKey: ['applications'],
    queryFn: () => getApplications({ limit: 100 }),
  });

  // Update mutation
  const updateMutation = useMutation({
    mutationFn: ({ id, data }: { id: string; data: { status?: ApplicationStatus; notes?: string } }) =>
      updateApplication(id, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['applications'] });
    },
  });

  const handleDragStart = useCallback((e: React.DragEvent, app: Application) => {
    setDraggedApp(app);
    e.dataTransfer.effectAllowed = 'move';
  }, []);

  const handleDragOver = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    e.dataTransfer.dropEffect = 'move';
  }, []);

  const handleDrop = useCallback(
    (e: React.DragEvent, status: ApplicationStatus) => {
      e.preventDefault();
      setDropTarget(null);

      if (draggedApp && draggedApp.status !== status) {
        updateMutation.mutate({
          id: draggedApp.id,
          data: { status },
        });
      }
      setDraggedApp(null);
    },
    [draggedApp, updateMutation]
  );

  const handleDragEnter = useCallback((status: ApplicationStatus) => {
    setDropTarget(status);
  }, []);

  const handleDragLeave = useCallback(() => {
    setDropTarget(null);
  }, []);

  const handleCardClick = useCallback((app: Application) => {
    setSelectedApp(app);
  }, []);

  const handleUpdateStatus = useCallback(
    (status: ApplicationStatus) => {
      if (selectedApp) {
        updateMutation.mutate(
          { id: selectedApp.id, data: { status } },
          {
            onSuccess: () => {
              setSelectedApp((prev) => (prev ? { ...prev, status } : null));
            },
          }
        );
      }
    },
    [selectedApp, updateMutation]
  );

  const handleUpdateNotes = useCallback(
    (notes: string) => {
      if (selectedApp) {
        updateMutation.mutate(
          { id: selectedApp.id, data: { notes } },
          {
            onSuccess: () => {
              setSelectedApp((prev) => (prev ? { ...prev, notes } : null));
            },
          }
        );
      }
    },
    [selectedApp, updateMutation]
  );

  // Group applications by status
  const applicationsByStatus = KANBAN_COLUMNS.reduce(
    (acc, { status }) => {
      acc[status] = applicationsData?.applications.filter((app) => app.status === status) || [];
      return acc;
    },
    {} as Record<ApplicationStatus, Application[]>
  );

  if (isLoading) {
    return (
      <div className="flex gap-4 overflow-x-auto pb-4">
        {KANBAN_COLUMNS.slice(0, 5).map(({ status, color }) => (
          <div key={status} className={`flex-shrink-0 w-72 rounded-lg border-2 ${color} animate-pulse`}>
            <div className="px-3 py-2 border-b border-gray-200 bg-white/50">
              <div className="h-5 bg-gray-200 rounded w-20"></div>
            </div>
            <div className="p-2 space-y-2">
              {[1, 2].map((i) => (
                <div key={i} className="bg-white rounded-lg border border-gray-200 p-3">
                  <div className="h-4 bg-gray-200 rounded w-3/4 mb-2"></div>
                  <div className="h-3 bg-gray-200 rounded w-1/2"></div>
                </div>
              ))}
            </div>
          </div>
        ))}
      </div>
    );
  }

  const totalApplications = applicationsData?.applications.length || 0;

  return (
    <div>
      {/* Stats Header */}
      <div className="mb-4 flex items-center justify-between">
        <div className="flex items-center gap-4">
          <h2 className="text-lg font-semibold text-gray-900">Applications</h2>
          <span className="text-sm text-gray-500">{totalApplications} total</span>
        </div>
        {applicationsData?.by_status && (
          <div className="flex items-center gap-2 text-sm">
            {Object.entries(applicationsData.by_status).map(([status, count]) => (
              <span key={status} className="px-2 py-1 bg-gray-100 rounded text-gray-600">
                {status}: {count}
              </span>
            ))}
          </div>
        )}
      </div>

      {/* Kanban Board */}
      <div className="flex gap-4 overflow-x-auto pb-4">
        {KANBAN_COLUMNS.map(({ status, label, color }) => (
          <div
            key={status}
            onDragEnter={() => handleDragEnter(status)}
            onDragLeave={handleDragLeave}
          >
            <KanbanColumn
              status={status}
              label={label}
              color={color}
              applications={applicationsByStatus[status]}
              onDragStart={handleDragStart}
              onDragOver={handleDragOver}
              onDrop={handleDrop}
              onCardClick={handleCardClick}
              isDropTarget={dropTarget === status}
            />
          </div>
        ))}
      </div>

      {/* Detail Modal */}
      {selectedApp && (
        <ApplicationModal
          application={selectedApp}
          onClose={() => setSelectedApp(null)}
          onUpdateStatus={handleUpdateStatus}
          onUpdateNotes={handleUpdateNotes}
        />
      )}
    </div>
  );
};

export default ApplicationKanban;
