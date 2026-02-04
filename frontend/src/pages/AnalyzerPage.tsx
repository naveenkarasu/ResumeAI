import { useState } from 'react';
import { useMutation } from '@tanstack/react-query';
import { analyzeJob, MatchResult, GapAnalysis } from '../api/analyze';
import { useToast } from '../components/ui';

function MatchScore({ score }: { score: number }) {
  const getColor = (s: number) => {
    if (s >= 80) return 'text-green-600';
    if (s >= 60) return 'text-yellow-600';
    if (s >= 40) return 'text-orange-600';
    return 'text-red-600';
  };

  const getBgColor = (s: number) => {
    if (s >= 80) return 'bg-green-100';
    if (s >= 60) return 'bg-yellow-100';
    if (s >= 40) return 'bg-orange-100';
    return 'bg-red-100';
  };

  return (
    <div className={`rounded-xl p-6 ${getBgColor(score)} text-center`}>
      <div className={`text-5xl font-bold ${getColor(score)}`}>
        {Math.round(score)}%
      </div>
      <div className="text-gray-600 mt-2">Match Score</div>
    </div>
  );
}

function SkillsList({ skills }: { skills: MatchResult[] }) {
  const matched = skills.filter(s => s.matched);
  const missing = skills.filter(s => !s.matched);

  return (
    <div className="space-y-4">
      {matched.length > 0 && (
        <div>
          <h4 className="font-medium text-green-700 mb-2">Matched Skills ({matched.length})</h4>
          <div className="flex flex-wrap gap-2">
            {matched.map((skill, idx) => (
              <span
                key={idx}
                className="px-3 py-1 bg-green-100 text-green-700 rounded-full text-sm"
                title={skill.resume_evidence || ''}
              >
                {skill.item}
              </span>
            ))}
          </div>
        </div>
      )}
      {missing.length > 0 && (
        <div>
          <h4 className="font-medium text-red-700 mb-2">Missing Skills ({missing.length})</h4>
          <div className="flex flex-wrap gap-2">
            {missing.map((skill, idx) => (
              <span
                key={idx}
                className="px-3 py-1 bg-red-100 text-red-700 rounded-full text-sm"
              >
                {skill.item}
              </span>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

function GapsList({ gaps }: { gaps: GapAnalysis[] }) {
  const statusColors = {
    met: { bg: 'bg-green-50', border: 'border-green-200', text: 'text-green-700', badge: 'bg-green-100' },
    partial: { bg: 'bg-yellow-50', border: 'border-yellow-200', text: 'text-yellow-700', badge: 'bg-yellow-100' },
    missing: { bg: 'bg-red-50', border: 'border-red-200', text: 'text-red-700', badge: 'bg-red-100' },
  };

  return (
    <div className="space-y-3">
      {gaps.map((gap, idx) => {
        const colors = statusColors[gap.status];
        return (
          <div key={idx} className={`p-3 rounded-lg border ${colors.bg} ${colors.border}`}>
            <div className="flex items-start justify-between gap-2">
              <p className="text-sm text-gray-700">{gap.requirement}</p>
              <span className={`px-2 py-0.5 rounded text-xs font-medium ${colors.badge} ${colors.text}`}>
                {gap.status}
              </span>
            </div>
            {gap.suggestion && (
              <p className="mt-2 text-xs text-gray-600 italic">{gap.suggestion}</p>
            )}
          </div>
        );
      })}
    </div>
  );
}

function SuggestionsList({ suggestions }: { suggestions: string[] }) {
  return (
    <ul className="space-y-2">
      {suggestions.map((suggestion, idx) => (
        <li key={idx} className="flex items-start gap-2 text-sm">
          <span className="text-primary-500 mt-0.5">→</span>
          <span>{suggestion}</span>
        </li>
      ))}
    </ul>
  );
}

export function AnalyzerPage() {
  const [jobDescription, setJobDescription] = useState('');
  const toast = useToast();

  const mutation = useMutation({
    mutationFn: (jd: string) => analyzeJob({ job_description: jd }),
    onSuccess: (data) => {
      toast.success(`Analysis complete: ${Math.round(data.match_score)}% match`);
    },
    onError: () => {
      toast.error('Analysis failed. Please try again.');
    },
  });

  const handleAnalyze = () => {
    if (jobDescription.trim().length >= 50) {
      mutation.mutate(jobDescription);
    }
  };

  const handleCopyResults = () => {
    if (mutation.data) {
      const text = `Match Score: ${mutation.data.match_score}%\n\n${mutation.data.summary}\n\nSuggestions:\n${mutation.data.suggestions.join('\n')}`;
      navigator.clipboard.writeText(text);
      toast.success('Results copied to clipboard');
    }
  };

  const result = mutation.data;

  return (
    <div className="h-full flex flex-col">
      {/* Header */}
      <div className="mb-4 md:mb-6">
        <h1 className="text-xl md:text-2xl font-bold text-gray-900">Job Analyzer</h1>
        <p className="text-sm text-gray-500 hidden sm:block">Analyze job descriptions against your resume</p>
      </div>

      <div className="flex-1 grid grid-cols-1 lg:grid-cols-2 gap-4 md:gap-6 overflow-hidden">
        {/* Left: Input */}
        <div className="flex flex-col min-h-0">
          <label className="block text-sm font-medium text-gray-700 mb-2">
            Job Description
          </label>
          <textarea
            value={jobDescription}
            onChange={(e) => setJobDescription(e.target.value)}
            placeholder="Paste the complete job description here..."
            className="flex-1 min-h-[200px] md:min-h-[300px] p-3 md:p-4 border border-gray-300 rounded-lg resize-none focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-transparent text-sm md:text-base"
          />
          <div className="mt-3 md:mt-4 flex items-center justify-between">
            <span className="text-xs md:text-sm text-gray-500">
              {jobDescription.length} chars (min 50)
            </span>
            <button
              onClick={handleAnalyze}
              disabled={jobDescription.trim().length < 50 || mutation.isPending}
              className="px-4 md:px-6 py-2 bg-primary-600 text-white text-sm md:text-base rounded-lg hover:bg-primary-700 disabled:bg-gray-300 disabled:cursor-not-allowed transition-colors"
            >
              {mutation.isPending ? (
                <span className="flex items-center gap-2">
                  <svg className="animate-spin h-4 w-4" viewBox="0 0 24 24">
                    <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" fill="none" />
                    <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
                  </svg>
                  <span className="hidden sm:inline">Analyzing...</span>
                </span>
              ) : (
                'Analyze'
              )}
            </button>
          </div>
        </div>

        {/* Right: Results */}
        <div className="overflow-y-auto">
          {mutation.error && (
            <div className="p-4 bg-red-50 border border-red-200 rounded-lg text-red-700">
              Error: {mutation.error instanceof Error ? mutation.error.message : 'Analysis failed'}
            </div>
          )}

          {!result && !mutation.isPending && !mutation.error && (
            <div className="h-full flex items-center justify-center text-center text-gray-500">
              <div>
                <div className="text-4xl mb-4">🔍</div>
                <p>Paste a job description and click Analyze</p>
                <p className="text-sm mt-1">to see how well your resume matches</p>
              </div>
            </div>
          )}

          {result && (
            <div className="space-y-4 md:space-y-6">
              {/* Match Score with Copy */}
              <div className="flex items-start gap-3">
                <div className="flex-1">
                  <MatchScore score={result.match_score} />
                </div>
                <button
                  onClick={handleCopyResults}
                  className="p-2 text-gray-400 hover:text-gray-600 hover:bg-gray-100 rounded-lg transition-colors"
                  title="Copy results"
                >
                  <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 16H6a2 2 0 01-2-2V6a2 2 0 012-2h8a2 2 0 012 2v2m-6 12h8a2 2 0 002-2v-8a2 2 0 00-2-2h-8a2 2 0 00-2 2v8a2 2 0 002 2z" />
                  </svg>
                </button>
              </div>

              {/* Summary */}
              <div className="bg-white rounded-lg border border-gray-200 p-4">
                <h3 className="font-semibold text-gray-900 mb-2">Summary</h3>
                <p className="text-gray-700">{result.summary}</p>
                {result.processing_time_ms && (
                  <p className="text-xs text-gray-400 mt-2">
                    Analyzed in {result.processing_time_ms}ms
                  </p>
                )}
              </div>

              {/* Skills */}
              <div className="bg-white rounded-lg border border-gray-200 p-4">
                <h3 className="font-semibold text-gray-900 mb-3">Skills Match</h3>
                <SkillsList skills={result.matching_skills} />
              </div>

              {/* Gaps */}
              {result.gaps.length > 0 && (
                <div className="bg-white rounded-lg border border-gray-200 p-4">
                  <h3 className="font-semibold text-gray-900 mb-3">Requirements Analysis</h3>
                  <GapsList gaps={result.gaps} />
                </div>
              )}

              {/* Keywords */}
              {result.keywords_to_add.length > 0 && (
                <div className="bg-white rounded-lg border border-gray-200 p-4">
                  <h3 className="font-semibold text-gray-900 mb-3">Keywords to Add</h3>
                  <div className="flex flex-wrap gap-2">
                    {result.keywords_to_add.map((kw, idx) => (
                      <span key={idx} className="px-3 py-1 bg-blue-100 text-blue-700 rounded-full text-sm">
                        {kw}
                      </span>
                    ))}
                  </div>
                </div>
              )}

              {/* Suggestions */}
              {result.suggestions.length > 0 && (
                <div className="bg-white rounded-lg border border-gray-200 p-4">
                  <h3 className="font-semibold text-gray-900 mb-3">Suggestions</h3>
                  <SuggestionsList suggestions={result.suggestions} />
                </div>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
