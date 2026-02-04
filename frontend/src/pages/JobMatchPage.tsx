import { useState } from 'react';
import { useMutation, useQuery } from '@tanstack/react-query';
import {
  matchJob,
  getJobHistory,
  getSkillsAnalytics,
  JobMatchRequest,
  MatchedSkill,
  MissingSkill,
  Recommendation,
  ScoreBreakdown,
  JobHistoryItem,
  MatchQuality,
  SkillsAnalytics,
} from '../api/jobs';
import { useToast } from '../components/ui';

// === Helper Components ===

function QualityBadge({ quality }: { quality: MatchQuality }) {
  const styles = {
    excellent: 'bg-green-100 text-green-800',
    good: 'bg-blue-100 text-blue-800',
    fair: 'bg-yellow-100 text-yellow-800',
    poor: 'bg-red-100 text-red-800',
  };

  return (
    <span className={`px-2 py-1 rounded-full text-xs font-medium ${styles[quality]}`}>
      {quality.charAt(0).toUpperCase() + quality.slice(1)} Match
    </span>
  );
}

function ScoreCircle({ score, size = 'large' }: { score: number; size?: 'small' | 'large' }) {
  const getColor = (s: number) => {
    if (s >= 85) return { ring: 'stroke-green-500', text: 'text-green-600', bg: 'bg-green-50' };
    if (s >= 70) return { ring: 'stroke-blue-500', text: 'text-blue-600', bg: 'bg-blue-50' };
    if (s >= 50) return { ring: 'stroke-yellow-500', text: 'text-yellow-600', bg: 'bg-yellow-50' };
    return { ring: 'stroke-red-500', text: 'text-red-600', bg: 'bg-red-50' };
  };

  const colors = getColor(score);
  const circumference = 2 * Math.PI * 45;
  const progress = (score / 100) * circumference;

  if (size === 'small') {
    return (
      <div className={`inline-flex items-center justify-center w-12 h-12 rounded-full ${colors.bg}`}>
        <span className={`text-sm font-bold ${colors.text}`}>{Math.round(score)}%</span>
      </div>
    );
  }

  return (
    <div className={`relative inline-flex items-center justify-center ${colors.bg} rounded-2xl p-6`}>
      <svg className="w-32 h-32 transform -rotate-90">
        <circle
          cx="64"
          cy="64"
          r="45"
          stroke="currentColor"
          strokeWidth="8"
          fill="none"
          className="text-gray-200"
        />
        <circle
          cx="64"
          cy="64"
          r="45"
          strokeWidth="8"
          fill="none"
          strokeLinecap="round"
          className={colors.ring}
          strokeDasharray={circumference}
          strokeDashoffset={circumference - progress}
          style={{ transition: 'stroke-dashoffset 0.5s ease-in-out' }}
        />
      </svg>
      <div className="absolute inset-0 flex flex-col items-center justify-center">
        <span className={`text-4xl font-bold ${colors.text}`}>{Math.round(score)}%</span>
        <span className="text-sm text-gray-500">Match</span>
      </div>
    </div>
  );
}

function ScoreBreakdownCard({ scores }: { scores: ScoreBreakdown }) {
  const items = [
    { label: 'Skills', value: scores.skills_match, icon: '🛠️' },
    { label: 'Experience', value: scores.experience_match, icon: '📈' },
    { label: 'Education', value: scores.education_match, icon: '🎓' },
    { label: 'Keywords', value: scores.keywords_match, icon: '🔑' },
  ];

  return (
    <div className="space-y-3">
      {items.map((item) => (
        <div key={item.label} className="flex items-center gap-3">
          <span className="text-lg">{item.icon}</span>
          <div className="flex-1">
            <div className="flex justify-between text-sm mb-1">
              <span className="text-gray-600">{item.label}</span>
              <span className="font-medium">{Math.round(item.value)}%</span>
            </div>
            <div className="h-2 bg-gray-200 rounded-full overflow-hidden">
              <div
                className={`h-full rounded-full transition-all duration-500 ${
                  item.value >= 80 ? 'bg-green-500' :
                  item.value >= 60 ? 'bg-blue-500' :
                  item.value >= 40 ? 'bg-yellow-500' : 'bg-red-500'
                }`}
                style={{ width: `${item.value}%` }}
              />
            </div>
          </div>
        </div>
      ))}
    </div>
  );
}

function SkillsMatrix({
  matched,
  missing,
}: {
  matched: MatchedSkill[];
  missing: MissingSkill[];
}) {
  return (
    <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
      {/* Matched Skills */}
      <div className="bg-green-50 rounded-lg p-4">
        <h4 className="font-medium text-green-800 mb-3 flex items-center gap-2">
          <span>✓</span> Matched Skills ({matched.length})
        </h4>
        <div className="space-y-2 max-h-64 overflow-y-auto">
          {matched.map((skill, idx) => (
            <div
              key={idx}
              className="bg-white rounded-lg p-2 border border-green-200"
            >
              <div className="flex items-center justify-between">
                <span className="font-medium text-green-700">{skill.skill}</span>
                <div className="flex items-center gap-1">
                  {[...Array(5)].map((_, i) => (
                    <div
                      key={i}
                      className={`w-1.5 h-3 rounded-sm ${
                        i < Math.round(skill.relevance * 5) ? 'bg-green-500' : 'bg-gray-200'
                      }`}
                    />
                  ))}
                </div>
              </div>
              {skill.context && (
                <p className="text-xs text-gray-500 mt-1 line-clamp-2">{skill.context}</p>
              )}
            </div>
          ))}
          {matched.length === 0 && (
            <p className="text-sm text-green-600 italic">No skills matched yet</p>
          )}
        </div>
      </div>

      {/* Missing Skills */}
      <div className="bg-red-50 rounded-lg p-4">
        <h4 className="font-medium text-red-800 mb-3 flex items-center gap-2">
          <span>✗</span> Missing Skills ({missing.length})
        </h4>
        <div className="space-y-2 max-h-64 overflow-y-auto">
          {missing.map((skill, idx) => (
            <div
              key={idx}
              className="bg-white rounded-lg p-2 border border-red-200"
            >
              <div className="flex items-center justify-between">
                <span className="font-medium text-red-700">{skill.skill}</span>
                <span className={`text-xs px-1.5 py-0.5 rounded ${
                  skill.importance === 'required' ? 'bg-red-100 text-red-700' :
                  skill.importance === 'preferred' ? 'bg-orange-100 text-orange-700' :
                  'bg-gray-100 text-gray-600'
                }`}>
                  {skill.importance}
                </span>
              </div>
              <p className="text-xs text-gray-500 mt-1">{skill.suggestion}</p>
              {skill.related_skills && skill.related_skills.length > 0 && (
                <p className="text-xs text-blue-600 mt-1">
                  Related: {skill.related_skills.join(', ')}
                </p>
              )}
            </div>
          ))}
          {missing.length === 0 && (
            <p className="text-sm text-green-600 italic">No critical skills missing!</p>
          )}
        </div>
      </div>
    </div>
  );
}

function RecommendationsList({ recommendations }: { recommendations: Recommendation[] }) {
  const categoryIcons: Record<string, string> = {
    skills: '🛠️',
    experience: '📈',
    keywords: '🔑',
    format: '📝',
  };

  return (
    <div className="space-y-3">
      {recommendations.map((rec, idx) => (
        <div
          key={idx}
          className="bg-white border border-gray-200 rounded-lg p-4 hover:shadow-sm transition-shadow"
        >
          <div className="flex items-start gap-3">
            <span className="text-xl">{categoryIcons[rec.category] || '💡'}</span>
            <div className="flex-1">
              <div className="flex items-center justify-between">
                <h4 className="font-medium text-gray-900">{rec.title}</h4>
                <span className={`text-xs px-2 py-0.5 rounded-full ${
                  rec.priority === 1 ? 'bg-red-100 text-red-700' :
                  rec.priority === 2 ? 'bg-orange-100 text-orange-700' :
                  'bg-gray-100 text-gray-600'
                }`}>
                  P{rec.priority}
                </span>
              </div>
              <p className="text-sm text-gray-600 mt-1">{rec.description}</p>
            </div>
          </div>
        </div>
      ))}
    </div>
  );
}

function HistorySidebar({
  isOpen,
  onClose,
  history,
  onSelect,
}: {
  isOpen: boolean;
  onClose: () => void;
  history: JobHistoryItem[];
  onSelect: (item: JobHistoryItem) => void;
}) {
  if (!isOpen) return null;

  return (
    <>
      {/* Backdrop */}
      <div
        className="fixed inset-0 bg-black/50 z-40 lg:hidden"
        onClick={onClose}
      />

      {/* Sidebar */}
      <div className="fixed right-0 top-0 h-full w-80 bg-white shadow-xl z-50 flex flex-col">
        <div className="p-4 border-b flex items-center justify-between">
          <h3 className="font-semibold">Match History</h3>
          <button onClick={onClose} className="p-1 hover:bg-gray-100 rounded">
            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>

        <div className="flex-1 overflow-y-auto p-4 space-y-2">
          {history.length === 0 ? (
            <p className="text-gray-500 text-sm text-center py-8">No matches yet</p>
          ) : (
            history.map((item) => (
              <button
                key={item.match_id}
                onClick={() => {
                  onSelect(item);
                  onClose();
                }}
                className="w-full text-left p-3 rounded-lg border hover:bg-gray-50 transition-colors"
              >
                <div className="flex items-center justify-between">
                  <span className="font-medium text-sm truncate">
                    {item.job_title || 'Untitled Job'}
                  </span>
                  <ScoreCircle score={item.overall_score} size="small" />
                </div>
                {item.company && (
                  <p className="text-xs text-gray-500 mt-1">{item.company}</p>
                )}
                <p className="text-xs text-gray-400 mt-1">
                  {new Date(item.analyzed_at).toLocaleDateString()}
                </p>
              </button>
            ))
          )}
        </div>
      </div>
    </>
  );
}

function SkillBar({ skill, matchRate, timesRequired }: { skill: string; matchRate: number; timesRequired: number }) {
  return (
    <div className="flex items-center gap-3 py-2">
      <div className="w-24 text-sm font-medium truncate" title={skill}>{skill}</div>
      <div className="flex-1 h-2 bg-gray-200 rounded-full overflow-hidden">
        <div
          className={`h-full rounded-full ${
            matchRate >= 80 ? 'bg-green-500' :
            matchRate >= 50 ? 'bg-yellow-500' : 'bg-red-500'
          }`}
          style={{ width: `${matchRate}%` }}
        />
      </div>
      <div className="w-12 text-xs text-gray-500 text-right">{Math.round(matchRate)}%</div>
      <div className="w-8 text-xs text-gray-400">({timesRequired})</div>
    </div>
  );
}

function AnalyticsSidebar({
  isOpen,
  onClose,
  analytics,
}: {
  isOpen: boolean;
  onClose: () => void;
  analytics: SkillsAnalytics | undefined;
}) {
  if (!isOpen) return null;

  return (
    <>
      <div
        className="fixed inset-0 bg-black/50 z-40 lg:hidden"
        onClick={onClose}
      />

      <div className="fixed right-0 top-0 h-full w-96 bg-white shadow-xl z-50 flex flex-col">
        <div className="p-4 border-b flex items-center justify-between">
          <h3 className="font-semibold">Skills Analytics</h3>
          <button onClick={onClose} className="p-1 hover:bg-gray-100 rounded">
            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>

        <div className="flex-1 overflow-y-auto p-4 space-y-6">
          {!analytics || (analytics.strongest_skills.length === 0 && analytics.most_requested.length === 0) ? (
            <p className="text-gray-500 text-sm text-center py-8">
              Match more jobs to see analytics
            </p>
          ) : (
            <>
              {/* Strongest Skills */}
              {analytics.strongest_skills.length > 0 && (
                <div>
                  <h4 className="font-medium text-green-700 mb-2 flex items-center gap-2">
                    <span>💪</span> Your Strongest Skills
                  </h4>
                  <div className="bg-green-50 rounded-lg p-3">
                    {analytics.strongest_skills.slice(0, 5).map((skill, idx) => (
                      <SkillBar
                        key={idx}
                        skill={skill.skill}
                        matchRate={skill.match_rate}
                        timesRequired={skill.times_required}
                      />
                    ))}
                  </div>
                </div>
              )}

              {/* Most Requested */}
              {analytics.most_requested.length > 0 && (
                <div>
                  <h4 className="font-medium text-blue-700 mb-2 flex items-center gap-2">
                    <span>📊</span> Most Requested Skills
                  </h4>
                  <div className="bg-blue-50 rounded-lg p-3">
                    {analytics.most_requested.slice(0, 5).map((skill, idx) => (
                      <SkillBar
                        key={idx}
                        skill={skill.skill}
                        matchRate={skill.match_rate}
                        timesRequired={skill.times_required}
                      />
                    ))}
                  </div>
                </div>
              )}

              {/* Weakest Skills */}
              {analytics.weakest_skills.length > 0 && (
                <div>
                  <h4 className="font-medium text-red-700 mb-2 flex items-center gap-2">
                    <span>📈</span> Skills to Improve
                  </h4>
                  <div className="bg-red-50 rounded-lg p-3">
                    {analytics.weakest_skills.slice(0, 5).map((skill, idx) => (
                      <SkillBar
                        key={idx}
                        skill={skill.skill}
                        matchRate={skill.match_rate}
                        timesRequired={skill.times_required}
                      />
                    ))}
                  </div>
                </div>
              )}

              {/* Improvement Areas */}
              {analytics.improvement_areas.length > 0 && (
                <div>
                  <h4 className="font-medium text-orange-700 mb-2 flex items-center gap-2">
                    <span>🎯</span> Focus Areas
                  </h4>
                  <div className="flex flex-wrap gap-2">
                    {analytics.improvement_areas.map((area, idx) => (
                      <span
                        key={idx}
                        className="px-3 py-1 bg-orange-100 text-orange-700 rounded-full text-sm"
                      >
                        {area}
                      </span>
                    ))}
                  </div>
                </div>
              )}
            </>
          )}
        </div>
      </div>
    </>
  );
}

// === Main Component ===

export function JobMatchPage() {
  const [jobDescription, setJobDescription] = useState('');
  const [jobTitle, setJobTitle] = useState('');
  const [company, setCompany] = useState('');
  const [showHistory, setShowHistory] = useState(false);
  const [showAnalytics, setShowAnalytics] = useState(false);
  const toast = useToast();

  // Fetch history
  const historyQuery = useQuery({
    queryKey: ['jobHistory'],
    queryFn: () => getJobHistory(20),
  });

  // Fetch analytics
  const analyticsQuery = useQuery({
    queryKey: ['skillsAnalytics'],
    queryFn: () => getSkillsAnalytics(),
  });

  // Match mutation
  const matchMutation = useMutation({
    mutationFn: (request: JobMatchRequest) => matchJob(request),
    onSuccess: (data) => {
      toast.success(`Match complete: ${Math.round(data.overall_score)}% - ${data.quality}`);
      historyQuery.refetch();
    },
    onError: (error) => {
      toast.error(`Match failed: ${error instanceof Error ? error.message : 'Unknown error'}`);
    },
  });

  const handleMatch = () => {
    if (jobDescription.trim().length >= 50) {
      matchMutation.mutate({
        job_description: jobDescription,
        job_title: jobTitle || undefined,
        company: company || undefined,
      });
    }
  };

  const handleCopyResults = () => {
    if (matchMutation.data) {
      const data = matchMutation.data;
      const text = `Job Match Results
================
${data.job_title ? `Position: ${data.job_title}\n` : ''}${data.company ? `Company: ${data.company}\n` : ''}
Overall Score: ${Math.round(data.overall_score)}% (${data.quality})

Score Breakdown:
- Skills: ${Math.round(data.scores.skills_match)}%
- Experience: ${Math.round(data.scores.experience_match)}%
- Education: ${Math.round(data.scores.education_match)}%
- Keywords: ${Math.round(data.scores.keywords_match)}%

Matched Skills (${data.matched_skills.length}):
${data.matched_skills.map(s => `- ${s.skill}`).join('\n')}

Missing Skills (${data.missing_skills.length}):
${data.missing_skills.map(s => `- ${s.skill} (${s.importance})`).join('\n')}

Recommendations:
${data.recommendations.map(r => `${r.priority}. ${r.title}: ${r.description}`).join('\n')}`;

      navigator.clipboard.writeText(text);
      toast.success('Results copied to clipboard');
    }
  };

  const result = matchMutation.data;

  return (
    <div className="h-full flex flex-col">
      {/* Header */}
      <div className="mb-4 flex items-center justify-between">
        <div>
          <h1 className="text-xl md:text-2xl font-bold text-gray-900">Job Matcher</h1>
          <p className="text-sm text-gray-500 hidden sm:block">
            Match your resume against job descriptions
          </p>
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={() => setShowAnalytics(true)}
            className="flex items-center gap-2 px-3 py-2 text-sm bg-purple-50 hover:bg-purple-100 text-purple-700 rounded-lg transition-colors"
          >
            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
            </svg>
            <span className="hidden sm:inline">Analytics</span>
          </button>
          <button
            onClick={() => setShowHistory(true)}
            className="flex items-center gap-2 px-3 py-2 text-sm bg-gray-100 hover:bg-gray-200 rounded-lg transition-colors"
          >
            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
            <span className="hidden sm:inline">History</span>
            {historyQuery.data && historyQuery.data.total_count > 0 && (
              <span className="bg-primary-500 text-white text-xs px-1.5 py-0.5 rounded-full">
                {historyQuery.data.total_count}
              </span>
            )}
          </button>
        </div>
      </div>

      <div className="flex-1 grid grid-cols-1 lg:grid-cols-2 gap-4 md:gap-6 overflow-hidden">
        {/* Left: Input Form */}
        <div className="flex flex-col min-h-0 space-y-4">
          {/* Job Title & Company */}
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Job Title (optional)
              </label>
              <input
                type="text"
                value={jobTitle}
                onChange={(e) => setJobTitle(e.target.value)}
                placeholder="Senior Software Engineer"
                className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-primary-500"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Company (optional)
              </label>
              <input
                type="text"
                value={company}
                onChange={(e) => setCompany(e.target.value)}
                placeholder="TechCorp Inc."
                className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-primary-500"
              />
            </div>
          </div>

          {/* Job Description */}
          <div className="flex-1 flex flex-col min-h-0">
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Job Description *
            </label>
            <textarea
              value={jobDescription}
              onChange={(e) => setJobDescription(e.target.value)}
              placeholder="Paste the complete job description here..."
              className="flex-1 min-h-[200px] p-3 border border-gray-300 rounded-lg resize-none focus:outline-none focus:ring-2 focus:ring-primary-500 text-sm"
            />
          </div>

          {/* Submit Button */}
          <div className="flex items-center justify-between">
            <span className="text-xs text-gray-500">
              {jobDescription.length} chars (min 50)
            </span>
            <button
              onClick={handleMatch}
              disabled={jobDescription.trim().length < 50 || matchMutation.isPending}
              className="px-6 py-2.5 bg-primary-600 text-white rounded-lg hover:bg-primary-700 disabled:bg-gray-300 disabled:cursor-not-allowed transition-colors font-medium"
            >
              {matchMutation.isPending ? (
                <span className="flex items-center gap-2">
                  <svg className="animate-spin h-4 w-4" viewBox="0 0 24 24">
                    <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" fill="none" />
                    <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
                  </svg>
                  Analyzing...
                </span>
              ) : (
                'Match Resume'
              )}
            </button>
          </div>
        </div>

        {/* Right: Results */}
        <div className="overflow-y-auto">
          {matchMutation.error && (
            <div className="p-4 bg-red-50 border border-red-200 rounded-lg text-red-700 mb-4">
              Error: {matchMutation.error instanceof Error ? matchMutation.error.message : 'Match failed'}
            </div>
          )}

          {!result && !matchMutation.isPending && !matchMutation.error && (
            <div className="h-full flex items-center justify-center text-center text-gray-500">
              <div>
                <div className="text-5xl mb-4">🎯</div>
                <p className="text-lg">Paste a job description</p>
                <p className="text-sm mt-1">to see how well your resume matches</p>
              </div>
            </div>
          )}

          {result && (
            <div className="space-y-4">
              {/* Score Header */}
              <div className="bg-white rounded-xl border border-gray-200 p-4">
                <div className="flex items-start justify-between">
                  <div className="flex items-center gap-4">
                    <ScoreCircle score={result.overall_score} />
                    <div>
                      {result.job_title && (
                        <h3 className="font-semibold text-gray-900">{result.job_title}</h3>
                      )}
                      {result.company && (
                        <p className="text-gray-500">{result.company}</p>
                      )}
                      <div className="mt-2">
                        <QualityBadge quality={result.quality} />
                      </div>
                    </div>
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
              </div>

              {/* Score Breakdown */}
              <div className="bg-white rounded-xl border border-gray-200 p-4">
                <h3 className="font-semibold text-gray-900 mb-4">Score Breakdown</h3>
                <ScoreBreakdownCard scores={result.scores} />
              </div>

              {/* Skills Matrix */}
              <div className="bg-white rounded-xl border border-gray-200 p-4">
                <h3 className="font-semibold text-gray-900 mb-4">Skills Analysis</h3>
                <SkillsMatrix matched={result.matched_skills} missing={result.missing_skills} />
              </div>

              {/* Recommendations */}
              {result.recommendations.length > 0 && (
                <div className="bg-white rounded-xl border border-gray-200 p-4">
                  <h3 className="font-semibold text-gray-900 mb-4">💡 Recommendations</h3>
                  <RecommendationsList recommendations={result.recommendations} />
                </div>
              )}

              {/* Extracted Requirements */}
              <div className="bg-white rounded-xl border border-gray-200 p-4">
                <h3 className="font-semibold text-gray-900 mb-4">Extracted Requirements</h3>
                <div className="space-y-3 text-sm">
                  {result.requirements.experience_years && (
                    <p><span className="font-medium">Experience:</span> {result.requirements.experience_years}+ years</p>
                  )}
                  {result.requirements.education && (
                    <p><span className="font-medium">Education:</span> {result.requirements.education}</p>
                  )}
                  {result.requirements.keywords.length > 0 && (
                    <div>
                      <span className="font-medium">Keywords:</span>
                      <div className="flex flex-wrap gap-1 mt-1">
                        {result.requirements.keywords.slice(0, 15).map((kw, idx) => (
                          <span key={idx} className="px-2 py-0.5 bg-gray-100 text-gray-600 rounded text-xs">
                            {kw}
                          </span>
                        ))}
                      </div>
                    </div>
                  )}
                </div>
              </div>
            </div>
          )}
        </div>
      </div>

      {/* History Sidebar */}
      {/* History Sidebar */}
      <HistorySidebar
        isOpen={showHistory}
        onClose={() => setShowHistory(false)}
        history={historyQuery.data?.items || []}
        onSelect={(item) => {
          toast.info(`Selected: ${item.job_title || 'Job'} - ${Math.round(item.overall_score)}%`);
        }}
      />

      {/* Analytics Sidebar */}
      <AnalyticsSidebar
        isOpen={showAnalytics}
        onClose={() => setShowAnalytics(false)}
        analytics={analyticsQuery.data}
      />
    </div>
  );
}
