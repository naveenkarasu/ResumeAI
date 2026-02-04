import { useState } from 'react';
import { useMutation } from '@tanstack/react-query';
import { generateEmail, EmailRequest, EmailResponse } from '../api/email';
import { useToast } from '../components/ui';

type EmailType = 'application' | 'followup' | 'thankyou';
type Tone = 'professional' | 'conversational' | 'enthusiastic';
type Length = 'brief' | 'standard' | 'detailed';
type Focus = 'technical' | 'leadership' | 'culture' | undefined;

function EmailTypeButton({
  active,
  onClick,
  icon,
  label,
}: {
  type: EmailType;
  active: boolean;
  onClick: () => void;
  icon: string;
  label: string;
}) {
  return (
    <button
      onClick={onClick}
      className={`flex-1 p-2 md:p-4 rounded-lg border-2 transition-colors ${
        active
          ? 'border-primary-500 bg-primary-50'
          : 'border-gray-200 hover:border-gray-300'
      }`}
    >
      <div className="text-xl md:text-2xl mb-0.5 md:mb-1">{icon}</div>
      <div className={`font-medium text-xs md:text-base ${active ? 'text-primary-700' : 'text-gray-700'}`}>
        {label}
      </div>
    </button>
  );
}

function OptionSelector<T extends string>({
  label,
  options,
  value,
  onChange,
}: {
  label: string;
  options: { value: T; label: string }[];
  value: T;
  onChange: (value: T) => void;
}) {
  return (
    <div>
      <label className="block text-sm font-medium text-gray-700 mb-2">{label}</label>
      <div className="flex gap-2">
        {options.map((opt) => (
          <button
            key={opt.value}
            onClick={() => onChange(opt.value)}
            className={`flex-1 px-3 py-2 rounded-lg text-sm transition-colors ${
              value === opt.value
                ? 'bg-primary-100 text-primary-700 font-medium'
                : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
            }`}
          >
            {opt.label}
          </button>
        ))}
      </div>
    </div>
  );
}

function EmailPreview({ email, onCopy }: { email: EmailResponse; onCopy: () => void }) {
  const [showVariation, setShowVariation] = useState(false);

  return (
    <div className="space-y-4">
      {/* Subject */}
      <div className="bg-white rounded-lg border border-gray-200 p-4">
        <div className="text-sm text-gray-500 mb-1">Subject</div>
        <div className="font-medium text-gray-900">{email.subject}</div>
      </div>

      {/* Body */}
      <div className="bg-white rounded-lg border border-gray-200 p-4">
        <div className="flex items-center justify-between mb-2">
          <span className="text-sm text-gray-500">Body</span>
          <button
            onClick={onCopy}
            className="text-sm text-primary-600 hover:underline"
          >
            Copy to clipboard
          </button>
        </div>
        <div className="whitespace-pre-wrap text-gray-700 font-mono text-sm leading-relaxed">
          {showVariation && email.variations?.[0] ? email.variations[0] : email.body}
        </div>
      </div>

      {/* Variation toggle */}
      {email.variations && email.variations.length > 0 && (
        <button
          onClick={() => setShowVariation(!showVariation)}
          className="text-sm text-primary-600 hover:underline"
        >
          {showVariation ? 'Show original version' : 'Show alternative version'}
        </button>
      )}
    </div>
  );
}

export function EmailPage() {
  // Form state
  const [emailType, setEmailType] = useState<EmailType>('application');
  const [jobDescription, setJobDescription] = useState('');
  const [companyName, setCompanyName] = useState('');
  const [recipientName, setRecipientName] = useState('');
  const [tone, setTone] = useState<Tone>('professional');
  const [length, setLength] = useState<Length>('standard');
  const [focus, setFocus] = useState<Focus>(undefined);
  const toast = useToast();

  // Mutation
  const mutation = useMutation({
    mutationFn: (request: EmailRequest) => generateEmail(request),
    onSuccess: () => toast.success('Email generated!'),
    onError: () => toast.error('Failed to generate email'),
  });

  const handleGenerate = () => {
    if (jobDescription.trim().length < 50) return;

    mutation.mutate({
      email_type: emailType,
      job_description: jobDescription,
      company_name: companyName || undefined,
      recipient_name: recipientName || undefined,
      tone,
      length,
      focus,
    });
  };

  const handleCopy = () => {
    if (mutation.data) {
      const text = `Subject: ${mutation.data.subject}\n\n${mutation.data.body}`;
      navigator.clipboard.writeText(text);
      toast.success('Copied to clipboard');
    }
  };

  const email = mutation.data;

  return (
    <div className="h-full flex flex-col">
      {/* Header */}
      <div className="mb-4 md:mb-6">
        <h1 className="text-xl md:text-2xl font-bold text-gray-900">Email Generator</h1>
        <p className="text-sm text-gray-500 hidden sm:block">Generate professional application emails</p>
      </div>

      <div className="flex-1 grid grid-cols-1 lg:grid-cols-2 gap-4 md:gap-6 overflow-hidden">
        {/* Left: Form */}
        <div className="space-y-4 md:space-y-6 overflow-y-auto">
          {/* Email Type */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Email Type
            </label>
            <div className="flex gap-2 md:gap-3">
              <EmailTypeButton
                type="application"
                active={emailType === 'application'}
                onClick={() => setEmailType('application')}
                icon="📧"
                label="Application"
              />
              <EmailTypeButton
                type="followup"
                active={emailType === 'followup'}
                onClick={() => setEmailType('followup')}
                icon="🔄"
                label="Follow-up"
              />
              <EmailTypeButton
                type="thankyou"
                active={emailType === 'thankyou'}
                onClick={() => setEmailType('thankyou')}
                icon="🙏"
                label="Thank You"
              />
            </div>
          </div>

          {/* Job Description */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Job Description *
            </label>
            <textarea
              value={jobDescription}
              onChange={(e) => setJobDescription(e.target.value)}
              placeholder="Paste the job description or role details..."
              rows={6}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg resize-none focus:outline-none focus:ring-2 focus:ring-primary-500"
            />
            <p className="text-xs text-gray-500 mt-1">
              {jobDescription.length} characters (min 50)
            </p>
          </div>

          {/* Optional fields */}
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Company Name
              </label>
              <input
                value={companyName}
                onChange={(e) => setCompanyName(e.target.value)}
                placeholder="e.g., Google"
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary-500"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Recipient Name
              </label>
              <input
                value={recipientName}
                onChange={(e) => setRecipientName(e.target.value)}
                placeholder="e.g., Jane Smith"
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary-500"
              />
            </div>
          </div>

          {/* Tone */}
          <OptionSelector
            label="Tone"
            options={[
              { value: 'professional', label: 'Professional' },
              { value: 'conversational', label: 'Conversational' },
              { value: 'enthusiastic', label: 'Enthusiastic' },
            ]}
            value={tone}
            onChange={(v) => setTone(v as Tone)}
          />

          {/* Length */}
          <OptionSelector
            label="Length"
            options={[
              { value: 'brief', label: 'Brief' },
              { value: 'standard', label: 'Standard' },
              { value: 'detailed', label: 'Detailed' },
            ]}
            value={length}
            onChange={(v) => setLength(v as Length)}
          />

          {/* Focus (for application emails) */}
          {emailType === 'application' && (
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Focus Area (Optional)
              </label>
              <div className="flex gap-2">
                {[
                  { value: undefined, label: 'Auto' },
                  { value: 'technical', label: 'Technical' },
                  { value: 'leadership', label: 'Leadership' },
                  { value: 'culture', label: 'Culture Fit' },
                ].map((opt) => (
                  <button
                    key={opt.label}
                    onClick={() => setFocus(opt.value as Focus)}
                    className={`flex-1 px-3 py-2 rounded-lg text-sm transition-colors ${
                      focus === opt.value
                        ? 'bg-primary-100 text-primary-700 font-medium'
                        : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
                    }`}
                  >
                    {opt.label}
                  </button>
                ))}
              </div>
            </div>
          )}

          {/* Generate button */}
          <button
            onClick={handleGenerate}
            disabled={jobDescription.trim().length < 50 || mutation.isPending}
            className="w-full px-6 py-3 bg-primary-600 text-white rounded-lg hover:bg-primary-700 disabled:bg-gray-300 disabled:cursor-not-allowed transition-colors"
          >
            {mutation.isPending ? (
              <span className="flex items-center justify-center gap-2">
                <svg className="animate-spin h-4 w-4" viewBox="0 0 24 24">
                  <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" fill="none" />
                  <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
                </svg>
                Generating...
              </span>
            ) : (
              'Generate Email'
            )}
          </button>
        </div>

        {/* Right: Preview */}
        <div className="overflow-y-auto">
          {mutation.error && (
            <div className="p-4 bg-red-50 border border-red-200 rounded-lg text-red-700">
              Error: {mutation.error instanceof Error ? mutation.error.message : 'Failed to generate email'}
            </div>
          )}

          {!email && !mutation.isPending && !mutation.error && (
            <div className="h-full flex items-center justify-center text-center text-gray-500">
              <div>
                <div className="text-4xl mb-4">✉️</div>
                <p>Configure your email and click Generate</p>
                <p className="text-sm mt-1">to create a personalized email</p>
              </div>
            </div>
          )}

          {email && <EmailPreview email={email} onCopy={handleCopy} />}
        </div>
      </div>
    </div>
  );
}
