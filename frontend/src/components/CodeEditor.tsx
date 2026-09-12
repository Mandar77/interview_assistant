// frontend/src/components/CodeEditor.tsx

import { useState, useRef, useEffect } from 'react';
import Editor, { OnMount } from '@monaco-editor/react';
import { Play, Loader2, Wand2 } from 'lucide-react';
import type { editor } from 'monaco-editor';

interface CodeEditorProps {
  language: string;
  initialCode?: string;
  onChange?: (code: string) => void;
  onRun?: (code: string) => void;
  height?: string;
  readOnly?: boolean;
  theme?: 'vs-dark' | 'light';
}

const LANGUAGE_MAP: Record<string, string> = {
  'python': 'python',
  'java': 'java',
  'cpp': 'cpp',
  'c': 'c',
  'javascript': 'javascript',
};

export default function CodeEditor({
  language,
  initialCode = '',
  onChange,
  onRun,
  height = '500px',
  readOnly = false,
  theme = 'vs-dark',
}: CodeEditorProps) {
  const [code, setCode] = useState(initialCode);
  const [isRunning, setIsRunning] = useState(false);
  const editorRef = useRef<editor.IStandaloneCodeEditor | null>(null);
  const monacoRef = useRef<typeof import('monaco-editor') | null>(null);

  useEffect(() => {
    setCode(initialCode);
  }, [initialCode]);

  const handleEditorChange = (value: string | undefined) => {
    const newCode = value || '';
    setCode(newCode);
    if (onChange) {
      onChange(newCode);
    }
  };

  const handleEditorDidMount: OnMount = (editor, monaco) => {
    editorRef.current = editor;
    monacoRef.current = monaco;
    
    // Add keyboard shortcuts
    editor.addCommand(
      monaco.KeyMod.CtrlCmd | monaco.KeyCode.Enter,
      () => {
        if (onRun) {
          handleRun();
        }
      }
    );
  };

  const handleRun = async () => {
    if (!onRun || isRunning) return;
    
    setIsRunning(true);
    try {
      await onRun(code);
    } finally {
      setIsRunning(false);
    }
  };

  const handleFormat = () => {
    if (editorRef.current) {
      editorRef.current.getAction('editor.action.formatDocument')?.run();
    }
  };

  const monacoLanguage = LANGUAGE_MAP[language] || 'plaintext';

  return (
    <div className="flex flex-col h-full">
      {/* Toolbar */}
      <div className="flex items-center justify-between border-b border-[var(--border)] bg-[var(--surface-2)] px-4 py-2">
        <div className="flex items-center gap-2.5">
          <span className="text-sm font-medium text-[var(--text-secondary)]">Editor</span>
          <span className="rounded-[var(--radius-xs)] bg-[var(--surface-3)] px-1.5 py-0.5 font-mono text-2xs font-medium uppercase tracking-wide text-[var(--text-muted)]">
            {language}
          </span>
        </div>
        
        <div className="flex items-center gap-2">
          <button
            onClick={handleFormat}
            className="inline-flex items-center gap-1.5 rounded-[var(--radius-sm)] border border-[var(--border)] px-2.5 py-1.5 text-sm text-[var(--text-secondary)] transition-colors hover:bg-[var(--surface-3)] hover:text-[var(--text)]"
            title="Format code (Shift+Alt+F)"
          >
            <Wand2 size={14} /> Format
          </button>
          
          {onRun && (
            <button
              onClick={handleRun}
              disabled={isRunning || readOnly}
              className="inline-flex items-center gap-1.5 rounded-[var(--radius-sm)] bg-[var(--accent)] px-3.5 py-1.5 text-sm font-medium text-[var(--accent-contrast)] transition-colors hover:bg-[var(--accent-hover)] disabled:opacity-50"
              title="Run code (Ctrl/Cmd+Enter)"
            >
              {isRunning ? (
                <>
                  <Loader2 size={14} className="animate-spin" /> Running…
                </>
              ) : (
                <>
                  <Play size={14} /> Run
                </>
              )}
            </button>
          )}
        </div>
      </div>

      {/* Editor */}
      <div style={{ height }}>
        <Editor
          height="100%"
          language={monacoLanguage}
          value={code}
          theme={theme}
          onChange={handleEditorChange}
          onMount={handleEditorDidMount}
          options={{
            minimap: { enabled: false },
            fontSize: 14,
            lineNumbers: 'on',
            roundedSelection: false,
            scrollBeyondLastLine: false,
            readOnly: readOnly,
            automaticLayout: true,
            tabSize: 4,
            wordWrap: 'on',
            formatOnPaste: true,
            formatOnType: true,
          }}
        />
      </div>
    </div>
  );
}