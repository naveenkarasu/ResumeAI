import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { getStatus, restartServer } from '../../api/settings';

interface HeaderProps {
  onMenuClick?: () => void;
}

export function Header({ onMenuClick }: HeaderProps) {
  const [isRestarting, setIsRestarting] = useState(false);

  const { data: status } = useQuery({
    queryKey: ['status'],
    queryFn: getStatus,
    refetchInterval: 30000,
  });

  const handleRestart = async () => {
    if (isRestarting) return;

    const confirmed = window.confirm('Restart the backend server? The page will reload shortly.');
    if (!confirmed) return;

    setIsRestarting(true);
    try {
      await restartServer();
      // Wait a bit for server to restart, then reload the page
      setTimeout(() => {
        window.location.reload();
      }, 2000);
    } catch (error) {
      console.error('Failed to restart server:', error);
      setIsRestarting(false);
      alert('Failed to restart server. Check console for details.');
    }
  };

  const statusColor = {
    healthy: 'bg-green-500',
    degraded: 'bg-yellow-500',
    unhealthy: 'bg-red-500',
  }[status?.status || 'unhealthy'];

  return (
    <header className="h-14 bg-white border-b border-gray-200 flex items-center justify-between px-4 md:px-6">
      <div className="flex items-center gap-3">
        {/* Hamburger menu for mobile */}
        <button
          onClick={onMenuClick}
          className="lg:hidden p-2 -ml-2 text-gray-500 hover:text-gray-700"
        >
          <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 6h16M4 12h16M4 18h16" />
          </svg>
        </button>
      </div>

      <div className="flex items-center gap-2 md:gap-4">
        {/* Restart button */}
        <button
          onClick={handleRestart}
          disabled={isRestarting}
          className={`px-2 py-1 text-xs rounded transition-colors ${
            isRestarting
              ? 'bg-yellow-100 text-yellow-700 cursor-wait'
              : 'bg-gray-100 hover:bg-gray-200 text-gray-600'
          }`}
          title="Restart backend server"
        >
          {isRestarting ? (
            <span className="flex items-center gap-1">
              <svg className="w-3 h-3 animate-spin" viewBox="0 0 24 24">
                <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" fill="none" />
                <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
              </svg>
              Restarting...
            </span>
          ) : (
            <span className="flex items-center gap-1">
              <svg className="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
              </svg>
              Restart
            </span>
          )}
        </button>

        {/* Status indicator */}
        <div className="flex items-center gap-2 text-xs md:text-sm text-gray-600">
          <span
            className={`w-2 h-2 rounded-full ${statusColor}`}
            title={`Status: ${status?.status || 'unknown'}`}
          />
          <span className="hidden sm:inline">{status?.indexed_documents || 0} docs</span>
        </div>

        {/* Backend indicator */}
        {status?.active_backend && (
          <div className="hidden md:block px-2 py-1 bg-gray-100 rounded text-xs text-gray-600">
            {status.active_backend}
          </div>
        )}
      </div>
    </header>
  );
}
