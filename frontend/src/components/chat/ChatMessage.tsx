import ReactMarkdown from 'react-markdown';
import type { Message, Citation } from '../../types';

interface ChatMessageProps {
  message: Message;
}

function Citations({ citations }: { citations: Citation[] }) {
  if (!citations || citations.length === 0) return null;

  return (
    <div className="mt-3 pt-3 border-t border-gray-200">
      <div className="text-xs text-gray-500 mb-2">Sources:</div>
      <div className="space-y-2">
        {citations.slice(0, 3).map((citation, idx) => (
          <div
            key={idx}
            className="text-xs bg-gray-50 p-2 rounded border border-gray-100"
          >
            <div className="font-medium text-gray-700">{citation.section}</div>
            <div className="text-gray-500 mt-1 line-clamp-2">{citation.text}</div>
            <div className="text-gray-400 mt-1">
              Relevance: {Math.round(citation.relevance_score * 100)}%
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

export function ChatMessage({ message }: ChatMessageProps) {
  const isUser = message.role === 'user';

  return (
    <div className={`flex gap-3 ${isUser ? 'justify-end' : 'justify-start'}`}>
      {/* Avatar */}
      {!isUser && (
        <div className="w-8 h-8 rounded-full bg-primary-100 flex items-center justify-center flex-shrink-0">
          <span className="text-sm">🤖</span>
        </div>
      )}

      {/* Message bubble */}
      <div
        className={`max-w-[70%] rounded-lg p-4 ${
          isUser
            ? 'bg-primary-600 text-white'
            : 'bg-white border border-gray-200'
        }`}
      >
        {isUser ? (
          <p className="whitespace-pre-wrap">{message.content}</p>
        ) : (
          <>
            <div className="prose prose-sm max-w-none">
              <ReactMarkdown>{message.content}</ReactMarkdown>
            </div>
            <Citations citations={message.citations || []} />

            {/* Metadata */}
            {(message.grounding_score !== undefined || message.processing_time_ms !== undefined) && (
              <div className="mt-3 pt-2 border-t border-gray-100 flex gap-4 text-xs text-gray-400">
                {message.grounding_score !== undefined && (
                  <span>Grounding: {Math.round(message.grounding_score * 100)}%</span>
                )}
                {message.processing_time_ms !== undefined && (
                  <span>{message.processing_time_ms}ms</span>
                )}
              </div>
            )}
          </>
        )}
      </div>

      {/* User avatar */}
      {isUser && (
        <div className="w-8 h-8 rounded-full bg-gray-200 flex items-center justify-center flex-shrink-0">
          <span className="text-sm">👤</span>
        </div>
      )}
    </div>
  );
}
