import { useState } from 'react';
import { useQuery, useMutation } from '@tanstack/react-query';
import {
  getQuestions,
  getCategories,
  getRoleTypes,
  generateStar,
  evaluatePractice,
  InterviewQuestion,
} from '../api/interview';
import { useToast } from '../components/ui';

type Tab = 'questions' | 'star' | 'practice';

function TabButton({
  active,
  onClick,
  children,
}: {
  active: boolean;
  onClick: () => void;
  children: React.ReactNode;
}) {
  return (
    <button
      onClick={onClick}
      className={`px-4 py-2 font-medium rounded-lg transition-colors ${
        active
          ? 'bg-primary-100 text-primary-700'
          : 'text-gray-600 hover:bg-gray-100'
      }`}
    >
      {children}
    </button>
  );
}

function QuestionCard({
  question,
  onPractice,
}: {
  question: InterviewQuestion;
  onPractice: (q: InterviewQuestion) => void;
}) {
  const [expanded, setExpanded] = useState(false);

  const difficultyColors = {
    easy: 'bg-green-100 text-green-700',
    medium: 'bg-yellow-100 text-yellow-700',
    hard: 'bg-red-100 text-red-700',
  };

  return (
    <div className="bg-white rounded-lg border border-gray-200 p-4">
      <div className="flex items-start justify-between gap-4">
        <div className="flex-1">
          <p className="font-medium text-gray-900">{question.question}</p>
          <div className="mt-2 flex items-center gap-2 flex-wrap">
            <span className="px-2 py-0.5 bg-gray-100 text-gray-600 rounded text-xs">
              {question.category}
            </span>
            <span className={`px-2 py-0.5 rounded text-xs ${difficultyColors[question.difficulty as keyof typeof difficultyColors] || 'bg-gray-100'}`}>
              {question.difficulty}
            </span>
          </div>
        </div>
        <button
          onClick={() => onPractice(question)}
          className="px-3 py-1 text-sm bg-primary-100 text-primary-700 rounded-lg hover:bg-primary-200"
        >
          Practice
        </button>
      </div>

      {question.tips && (
        <div className="mt-3">
          <button
            onClick={() => setExpanded(!expanded)}
            className="text-sm text-primary-600 hover:underline"
          >
            {expanded ? 'Hide tips' : 'Show tips'}
          </button>
          {expanded && (
            <p className="mt-2 text-sm text-gray-600 bg-gray-50 p-2 rounded">
              {question.tips}
            </p>
          )}
        </div>
      )}
    </div>
  );
}

function QuestionsTab({ onPractice }: { onPractice: (q: InterviewQuestion) => void }) {
  const [category, setCategory] = useState<string>('');
  const [roleType, setRoleType] = useState<string>('');
  const [difficulty, setDifficulty] = useState<string>('');

  const { data: categories = [] } = useQuery({
    queryKey: ['interview-categories'],
    queryFn: getCategories,
  });

  const { data: roleTypes = [] } = useQuery({
    queryKey: ['interview-roles'],
    queryFn: getRoleTypes,
  });

  const { data: questions = [], isLoading } = useQuery({
    queryKey: ['interview-questions', category, roleType, difficulty],
    queryFn: () => getQuestions({
      category: category || undefined,
      role_type: roleType || undefined,
      difficulty: difficulty || undefined,
      limit: 20,
    }),
  });

  return (
    <div className="space-y-4">
      {/* Filters */}
      <div className="flex flex-wrap gap-3">
        <select
          value={category}
          onChange={(e) => setCategory(e.target.value)}
          className="px-3 py-2 border border-gray-300 rounded-lg text-sm"
        >
          <option value="">All Categories</option>
          {categories.map((c) => (
            <option key={c.id} value={c.id}>{c.name}</option>
          ))}
        </select>

        <select
          value={roleType}
          onChange={(e) => setRoleType(e.target.value)}
          className="px-3 py-2 border border-gray-300 rounded-lg text-sm"
        >
          <option value="">All Roles</option>
          {roleTypes.map((r) => (
            <option key={r.id} value={r.id}>{r.name}</option>
          ))}
        </select>

        <select
          value={difficulty}
          onChange={(e) => setDifficulty(e.target.value)}
          className="px-3 py-2 border border-gray-300 rounded-lg text-sm"
        >
          <option value="">All Difficulties</option>
          <option value="easy">Easy</option>
          <option value="medium">Medium</option>
          <option value="hard">Hard</option>
        </select>
      </div>

      {/* Questions */}
      {isLoading ? (
        <div className="text-center py-8 text-gray-500">Loading questions...</div>
      ) : questions.length === 0 ? (
        <div className="text-center py-8 text-gray-500">No questions found</div>
      ) : (
        <div className="space-y-3">
          {questions.map((q) => (
            <QuestionCard key={q.id} question={q} onPractice={onPractice} />
          ))}
        </div>
      )}
    </div>
  );
}

function StarTab() {
  const [situation, setSituation] = useState('');
  const [questionContext, setQuestionContext] = useState('');
  const toast = useToast();

  const mutation = useMutation({
    mutationFn: () => generateStar(situation, questionContext || undefined),
    onSuccess: () => toast.success('STAR story generated!'),
    onError: () => toast.error('Failed to generate story'),
  });

  const handleCopyStory = () => {
    if (mutation.data) {
      const text = `SITUATION:\n${mutation.data.situation}\n\nTASK:\n${mutation.data.task}\n\nACTION:\n${mutation.data.action}\n\nRESULT:\n${mutation.data.result}`;
      navigator.clipboard.writeText(text);
      toast.success('Story copied to clipboard');
    }
  };

  const story = mutation.data;

  return (
    <div className="grid grid-cols-1 lg:grid-cols-2 gap-4 md:gap-6">
      {/* Input */}
      <div className="space-y-4">
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-2">
            Situation or Achievement
          </label>
          <textarea
            value={situation}
            onChange={(e) => setSituation(e.target.value)}
            placeholder="Describe a situation, achievement, or experience..."
            rows={5}
            className="w-full px-3 py-2 border border-gray-300 rounded-lg resize-none focus:outline-none focus:ring-2 focus:ring-primary-500 text-sm md:text-base"
          />
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-700 mb-2">
            Interview Question (Optional)
          </label>
          <input
            value={questionContext}
            onChange={(e) => setQuestionContext(e.target.value)}
            placeholder="What question should this answer?"
            className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary-500 text-sm md:text-base"
          />
        </div>

        <button
          onClick={() => mutation.mutate()}
          disabled={situation.trim().length < 10 || mutation.isPending}
          className="w-full px-4 py-2.5 bg-primary-600 text-white rounded-lg hover:bg-primary-700 disabled:bg-gray-300 disabled:cursor-not-allowed transition-colors"
        >
          {mutation.isPending ? 'Generating...' : 'Generate STAR Story'}
        </button>
      </div>

      {/* Result */}
      <div className="overflow-y-auto">
        {mutation.error && (
          <div className="p-4 bg-red-50 border border-red-200 rounded-lg text-red-700 text-sm">
            Error generating story
          </div>
        )}

        {!story && !mutation.isPending && (
          <div className="h-full min-h-[200px] flex items-center justify-center text-center text-gray-500">
            <div>
              <div className="text-4xl mb-4">✨</div>
              <p>Enter a situation and generate</p>
              <p className="text-sm mt-1">your STAR story</p>
            </div>
          </div>
        )}

        {story && (
          <div className="space-y-3 md:space-y-4">
            <div className="flex justify-end">
              <button
                onClick={handleCopyStory}
                className="text-sm text-primary-600 hover:underline flex items-center gap-1"
              >
                <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 16H6a2 2 0 01-2-2V6a2 2 0 012-2h8a2 2 0 012 2v2m-6 12h8a2 2 0 002-2v-8a2 2 0 00-2-2h-8a2 2 0 00-2 2v8a2 2 0 002 2z" />
                </svg>
                Copy
              </button>
            </div>
            {(['situation', 'task', 'action', 'result'] as const).map((key) => (
              <div key={key} className="bg-white rounded-lg border border-gray-200 p-3 md:p-4">
                <h4 className="font-semibold text-primary-700 uppercase text-xs md:text-sm mb-2">
                  {key.charAt(0).toUpperCase() + key.slice(1)}
                </h4>
                <p className="text-gray-700 text-sm md:text-base">{story[key]}</p>
              </div>
            ))}

            {story.question_fit && story.question_fit.length > 0 && (
              <div className="bg-gray-50 rounded-lg p-3 md:p-4">
                <h4 className="font-medium text-gray-700 text-sm mb-2">Questions this story could answer:</h4>
                <ul className="text-xs md:text-sm text-gray-600 space-y-1">
                  {story.question_fit.map((q, idx) => (
                    <li key={idx}>• {q}</li>
                  ))}
                </ul>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}

function PracticeTab({ initialQuestion }: { initialQuestion?: InterviewQuestion }) {
  const [question, setQuestion] = useState(initialQuestion?.question || '');
  const [questionId, setQuestionId] = useState(initialQuestion?.id || 'custom');
  const [answer, setAnswer] = useState('');
  const toast = useToast();

  const mutation = useMutation({
    mutationFn: () => evaluatePractice(questionId, question, answer),
    onSuccess: (data) => toast.success(`Score: ${Math.round(data.score)}/100`),
    onError: () => toast.error('Failed to evaluate answer'),
  });

  const feedback = mutation.data;

  const handleNewQuestion = () => {
    setQuestion('');
    setQuestionId('custom');
    setAnswer('');
    mutation.reset();
  };

  return (
    <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
      {/* Input */}
      <div className="space-y-4">
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-2">
            Question
          </label>
          <textarea
            value={question}
            onChange={(e) => {
              setQuestion(e.target.value);
              setQuestionId('custom');
            }}
            placeholder="Enter or select an interview question..."
            rows={3}
            className="w-full px-3 py-2 border border-gray-300 rounded-lg resize-none focus:outline-none focus:ring-2 focus:ring-primary-500"
          />
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-700 mb-2">
            Your Answer
          </label>
          <textarea
            value={answer}
            onChange={(e) => setAnswer(e.target.value)}
            placeholder="Type your practice answer here..."
            rows={10}
            className="w-full px-3 py-2 border border-gray-300 rounded-lg resize-none focus:outline-none focus:ring-2 focus:ring-primary-500"
          />
          <p className="text-xs text-gray-500 mt-1">{answer.length} characters</p>
        </div>

        <div className="flex gap-3">
          <button
            onClick={() => mutation.mutate()}
            disabled={question.trim().length < 10 || answer.trim().length < 20 || mutation.isPending}
            className="flex-1 px-4 py-2 bg-primary-600 text-white rounded-lg hover:bg-primary-700 disabled:bg-gray-300 disabled:cursor-not-allowed"
          >
            {mutation.isPending ? 'Evaluating...' : 'Get Feedback'}
          </button>
          <button
            onClick={handleNewQuestion}
            className="px-4 py-2 border border-gray-300 rounded-lg hover:bg-gray-50"
          >
            New Question
          </button>
        </div>
      </div>

      {/* Feedback */}
      <div>
        {mutation.error && (
          <div className="p-4 bg-red-50 border border-red-200 rounded-lg text-red-700">
            Error evaluating answer
          </div>
        )}

        {!feedback && !mutation.isPending && (
          <div className="h-full flex items-center justify-center text-center text-gray-500">
            <div>
              <div className="text-4xl mb-4">📝</div>
              <p>Answer a question and get</p>
              <p className="text-sm mt-1">AI-powered feedback</p>
            </div>
          </div>
        )}

        {feedback && (
          <div className="space-y-4">
            {/* Score */}
            <div className={`rounded-xl p-6 text-center ${
              feedback.score >= 80 ? 'bg-green-100' :
              feedback.score >= 60 ? 'bg-yellow-100' :
              'bg-orange-100'
            }`}>
              <div className={`text-4xl font-bold ${
                feedback.score >= 80 ? 'text-green-600' :
                feedback.score >= 60 ? 'text-yellow-600' :
                'text-orange-600'
              }`}>
                {Math.round(feedback.score)}
              </div>
              <div className="text-gray-600 mt-1">Score</div>
            </div>

            {/* Feedback sections */}
            <div className="bg-white rounded-lg border border-gray-200 p-4">
              <h4 className="font-semibold text-gray-900 mb-2">Relevance</h4>
              <p className="text-sm text-gray-700">{feedback.relevance_feedback}</p>
            </div>

            <div className="bg-white rounded-lg border border-gray-200 p-4">
              <h4 className="font-semibold text-gray-900 mb-2">Structure</h4>
              <p className="text-sm text-gray-700">{feedback.structure_feedback}</p>
            </div>

            <div className="bg-white rounded-lg border border-gray-200 p-4">
              <h4 className="font-semibold text-gray-900 mb-2">Specificity</h4>
              <p className="text-sm text-gray-700">{feedback.specificity_feedback}</p>
            </div>

            {/* Strengths & Improvements */}
            <div className="grid grid-cols-2 gap-4">
              <div className="bg-green-50 rounded-lg p-3">
                <h4 className="font-medium text-green-700 mb-2">Strengths</h4>
                <ul className="text-sm text-green-800 space-y-1">
                  {feedback.strengths.map((s, idx) => (
                    <li key={idx}>• {s}</li>
                  ))}
                </ul>
              </div>
              <div className="bg-orange-50 rounded-lg p-3">
                <h4 className="font-medium text-orange-700 mb-2">Improvements</h4>
                <ul className="text-sm text-orange-800 space-y-1">
                  {feedback.improvements.map((i, idx) => (
                    <li key={idx}>• {i}</li>
                  ))}
                </ul>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

export function InterviewPage() {
  const [activeTab, setActiveTab] = useState<Tab>('questions');
  const [practiceQuestion, setPracticeQuestion] = useState<InterviewQuestion | undefined>();

  const handlePractice = (question: InterviewQuestion) => {
    setPracticeQuestion(question);
    setActiveTab('practice');
  };

  return (
    <div className="h-full flex flex-col">
      {/* Header */}
      <div className="mb-4 md:mb-6">
        <h1 className="text-xl md:text-2xl font-bold text-gray-900">Interview Prep</h1>
        <p className="text-sm text-gray-500 hidden sm:block">Prepare for interviews with AI-powered feedback</p>
      </div>

      {/* Tabs - horizontal scroll on mobile */}
      <div className="flex gap-2 mb-4 md:mb-6 overflow-x-auto pb-1 -mx-1 px-1">
        <TabButton active={activeTab === 'questions'} onClick={() => setActiveTab('questions')}>
          Questions
        </TabButton>
        <TabButton active={activeTab === 'star'} onClick={() => setActiveTab('star')}>
          STAR
        </TabButton>
        <TabButton active={activeTab === 'practice'} onClick={() => setActiveTab('practice')}>
          Practice
        </TabButton>
      </div>

      {/* Content */}
      <div className="flex-1 overflow-y-auto min-h-0">
        {activeTab === 'questions' && <QuestionsTab onPractice={handlePractice} />}
        {activeTab === 'star' && <StarTab />}
        {activeTab === 'practice' && <PracticeTab initialQuestion={practiceQuestion} />}
      </div>
    </div>
  );
}
