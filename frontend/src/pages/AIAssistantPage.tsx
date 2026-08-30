import { useEffect, useRef, useState } from 'react';
import { machinesApi, aiApi } from '../services/api';
import type { Machine, AIAnalysis } from '../types';

// ── constants ────────────────────────────────────────────────────────────────

const SUGGESTED_QUESTIONS = [
  'Why is this machine at risk?',
  'What is the current condition of this machine?',
  'What maintenance should be performed?',
  'Analyze the current sensor readings.',
  'What are the possible failure causes?',
];

type Priority = AIAnalysis['priority'];

const PRIORITY_CLASS: Record<Priority, string> = {
  LOW: 'status-normal',
  MEDIUM: 'status-warning',
  HIGH: 'status-warning',
  CRITICAL: 'status-critical',
};

// ── message types ────────────────────────────────────────────────────────────

interface UserMessage {
  role: 'user';
  content: string;
}

interface AssistantMessage {
  role: 'assistant';
  machineId: string;
  question: string;
  analysis: AIAnalysis;
}

interface ErrorMessage {
  role: 'error';
  content: string;
}

type ChatMessage = UserMessage | AssistantMessage | ErrorMessage;

// ── sub-components ───────────────────────────────────────────────────────────

function AssistantBubble({ msg }: { msg: AssistantMessage }) {
  const { analysis } = msg;
  const priority = analysis.priority as Priority;
  return (
    <div className="message ai" style={{ maxWidth: '100%' }}>
      {/* Header row */}
      <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 10, flexWrap: 'wrap' }}>
        <span style={{ fontWeight: 700, color: '#4aa3ff', fontSize: 13 }}>MaintenAI</span>
        <span
          className={`status-pill ${PRIORITY_CLASS[priority] ?? 'status-normal'}`}
          style={{ fontSize: 11 }}
        >
          {priority} PRIORITY
        </span>
        <span style={{ color: '#8aa0bd', fontSize: 12, marginLeft: 'auto' }}>
          {msg.machineId}
        </span>
      </div>

      {/* Summary */}
      <p style={{ margin: '0 0 12px', lineHeight: 1.6, color: '#e5eefb' }}>
        {analysis.summary}
      </p>

      {/* Possible causes */}
      {analysis.possible_causes.length > 0 && (
        <div style={{ marginBottom: 12 }}>
          <div style={{ color: '#f59e0b', fontWeight: 700, fontSize: 12, marginBottom: 6, textTransform: 'uppercase', letterSpacing: '0.05em' }}>
            Possible Causes
          </div>
          <ul style={{ margin: 0, paddingLeft: 20, display: 'grid', gap: 4 }}>
            {analysis.possible_causes.map((cause, i) => (
              <li key={i} style={{ color: '#cbd5e1', fontSize: 13, lineHeight: 1.5 }}>{cause}</li>
            ))}
          </ul>
        </div>
      )}

      {/* Recommended actions */}
      {analysis.recommended_actions.length > 0 && (
        <div>
          <div style={{ color: '#2dd4bf', fontWeight: 700, fontSize: 12, marginBottom: 6, textTransform: 'uppercase', letterSpacing: '0.05em' }}>
            Recommended Actions
          </div>
          <ol style={{ margin: 0, paddingLeft: 20, display: 'grid', gap: 4 }}>
            {analysis.recommended_actions.map((action, i) => (
              <li key={i} style={{ color: '#cbd5e1', fontSize: 13, lineHeight: 1.5 }}>{action}</li>
            ))}
          </ol>
        </div>
      )}
    </div>
  );
}

// ── main page ────────────────────────────────────────────────────────────────

export function AIAssistantPage() {
  const [machines, setMachines] = useState<Machine[]>([]);
  const [machinesLoading, setMachinesLoading] = useState(true);
  const [machinesError, setMachinesError] = useState<string | null>(null);

  const [selectedMachineId, setSelectedMachineId] = useState('');
  const [question, setQuestion] = useState('');
  const [analyzing, setAnalyzing] = useState(false);

  // Initialize with a welcome message (not error)
  const [chat, setChat] = useState<ChatMessage[]>([
    {
      role: 'assistant',
      machineId: '',
      question: '',
      analysis: {
        summary: 'Welcome! Select a machine and ask a question to get an AI-powered maintenance analysis based on live sensor data and predictions.',
        possible_causes: [],
        recommended_actions: [],
        priority: 'LOW',
      },
    } as AssistantMessage,
  ]);

  const chatBottomRef = useRef<HTMLDivElement>(null);

  // Load machine list
  useEffect(() => {
    setMachinesLoading(true);
    machinesApi.getAll()
      .then((res) => {
        const list = res.data as Machine[];
        setMachines(list);
        if (list.length > 0) setSelectedMachineId(list[0].machine_id);
      })
      .catch(() => setMachinesError('Failed to load machine list. Is the backend running?'))
      .finally(() => setMachinesLoading(false));
  }, []);

  // Auto-scroll to bottom on new messages
  useEffect(() => {
    chatBottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [chat]);

  const sendQuestion = async (q: string) => {
    const trimmed = q.trim();
    if (!trimmed) return;
    if (!selectedMachineId) {
      setChat((prev) => [
        ...prev,
        { role: 'error', content: 'Please select a machine before asking a question.' },
      ]);
      return;
    }

    // Add user message
    setChat((prev) => [...prev, { role: 'user', content: trimmed }]);
    setQuestion('');
    setAnalyzing(true);

    try {
      const res = await aiApi.analyze(selectedMachineId, trimmed);
      const analysis = res.data as AIAnalysis;
      setChat((prev) => [
        ...prev,
        { role: 'assistant', machineId: selectedMachineId, question: trimmed, analysis },
      ]);
    } catch (err: unknown) {
      const axiosErr = err as { response?: { status: number; data?: { detail?: string } } };
      let msg = 'Analysis failed. Please try again.';
      if (axiosErr?.response?.status === 404) {
        msg = `Machine "${selectedMachineId}" was not found in the database.`;
      } else if (axiosErr?.response?.status === 400) {
        msg = axiosErr.response?.data?.detail ?? 'This machine has no sensor or prediction data available for analysis.';
      } else if (axiosErr?.response?.status === 422) {
        msg = 'Invalid request. Please check the selected machine and question.';
      } else if (axiosErr?.response?.status === 500) {
        msg = 'Server error during analysis. Please try again later.';
      } else if (!axiosErr?.response) {
        msg = 'Cannot reach the backend server. Is it running on port 8000?';
      }
      setChat((prev) => [...prev, { role: 'error', content: msg }]);
    } finally {
      setAnalyzing(false);
    }
  };

  const handleSend = () => sendQuestion(question);

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  const selectedMachine = machines.find((m) => m.machine_id === selectedMachineId);

  // ── render ──────────────────────────────────────────────────────────────

  return (
    <div className="page-shell">

      {/* Header */}
      <div className="topbar">
        <div>
          <h1 style={{ margin: 0 }}>AI Maintenance Assistant</h1>
          <div style={{ color: '#8aa0bd', fontSize: 13, marginTop: 3 }}>
            Powered by rule-based analysis with optional LLM enhancement
          </div>
        </div>
      </div>

      {/* Machine selector */}
      <div className="card" style={{ padding: '16px 20px' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 16, flexWrap: 'wrap' }}>
          <label style={{ color: '#8aa0bd', fontSize: 13, fontWeight: 600, whiteSpace: 'nowrap' }}>
            Analyze Machine:
          </label>

          {machinesLoading ? (
            <span style={{ color: '#8aa0bd', fontSize: 13 }}>Loading machines…</span>
          ) : machinesError ? (
            <span style={{ color: '#f87171', fontSize: 13 }}>{machinesError}</span>
          ) : (
            <select
              id="machine-selector"
              className="input"
              style={{ flex: 1, minWidth: 240, maxWidth: 420 }}
              value={selectedMachineId}
              onChange={(e) => setSelectedMachineId(e.target.value)}
              disabled={analyzing}
            >
              {machines.map((m) => (
                <option key={m.machine_id} value={m.machine_id}>
                  {m.machine_id} — {m.name} ({m.type}) [{m.status}]
                </option>
              ))}
            </select>
          )}

          {selectedMachine && (
            <div style={{ color: '#8aa0bd', fontSize: 12 }}>
              {selectedMachine.location}
            </div>
          )}
        </div>
      </div>

      {/* Chat window */}
      <div
        className="card"
        style={{
          minHeight: 360,
          maxHeight: 520,
          overflowY: 'auto',
          display: 'flex',
          flexDirection: 'column',
          gap: 14,
          padding: '20px 24px',
        }}
      >
        {chat.map((msg, i) => {
          if (msg.role === 'user') {
            return (
              <div key={i} className="message user">
                {msg.content}
              </div>
            );
          }
          if (msg.role === 'error') {
            if (!msg.content) return null; // skip the initial placeholder
            return (
              <div
                key={i}
                style={{
                  background: 'rgba(248,113,113,0.08)',
                  border: '1px solid rgba(248,113,113,0.2)',
                  borderRadius: 12,
                  padding: '10px 14px',
                  color: '#f87171',
                  fontSize: 13,
                }}
              >
                ⚠ {msg.content}
              </div>
            );
          }
          // assistant
          return <AssistantBubble key={i} msg={msg as AssistantMessage} />;
        })}

        {analyzing && (
          <div className="message ai" style={{ color: '#8aa0bd', fontStyle: 'italic', fontSize: 13 }}>
            <span>Analyzing {selectedMachineId}…</span>
          </div>
        )}

        <div ref={chatBottomRef} />
      </div>

      {/* Suggested questions */}
      <div className="card" style={{ padding: '14px 18px' }}>
        <div style={{ color: '#8aa0bd', fontSize: 12, fontWeight: 600, marginBottom: 10, textTransform: 'uppercase', letterSpacing: '0.05em' }}>
          Quick Questions
        </div>
        <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
          {SUGGESTED_QUESTIONS.map((q) => (
            <button
              key={q}
              id={`quick-q-${q.slice(0, 20).replace(/\s+/g, '-').toLowerCase()}`}
              className="secondary-button"
              style={{ fontSize: 12 }}
              onClick={() => sendQuestion(q)}
              disabled={analyzing || !selectedMachineId || machinesLoading}
            >
              {q}
            </button>
          ))}
        </div>
      </div>

      {/* Input area */}
      <div className="card" style={{ padding: '14px 18px' }}>
        <div style={{ display: 'flex', gap: 12, alignItems: 'flex-end' }}>
          <textarea
            id="ai-question-input"
            className="input"
            style={{
              flex: 1,
              minHeight: 60,
              resize: 'vertical',
              lineHeight: 1.5,
            }}
            placeholder={
              !selectedMachineId
                ? 'Select a machine above first…'
                : 'Ask a question about this machine (Enter to send, Shift+Enter for newline)…'
            }
            value={question}
            onChange={(e) => setQuestion(e.target.value)}
            onKeyDown={handleKeyDown}
            disabled={analyzing || !selectedMachineId || machinesLoading}
          />
          <button
            id="btn-send-analysis"
            className="primary-button"
            style={{ height: 60, minWidth: 90, fontSize: 15, flexShrink: 0 }}
            onClick={handleSend}
            disabled={analyzing || !question.trim() || !selectedMachineId || machinesLoading}
          >
            {analyzing ? '…' : 'Analyze'}
          </button>
        </div>
      </div>

    </div>
  );
}

