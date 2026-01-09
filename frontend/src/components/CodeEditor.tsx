// frontend/src/components/CodeEditor.tsx

import { useState, useRef, useEffect } from 'react';
import Editor, { OnMount } from '@monaco-editor/react';
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
      <div className="bg-gray-800 border-b border-gray-700 px-4 py-2 flex items-center justify-between">
        <div className="flex items-center gap-3">
          <span className="text-sm font-semibold text-gray-300">
            📝 Code Editor
          </span>
          <span className="px-2 py-1 bg-blue-600 text-white text-xs font-semibold rounded">
            {language.toUpperCase()}
          </span>
        </div>
        
        <div className="flex items-center gap-2">
          <button
            onClick={handleFormat}
            className="px-3 py-1.5 bg-gray-700 hover:bg-gray-600 text-white text-sm rounded transition-colors"
            title="Format Code (Shift+Alt+F)"
          >
            ✨ Format
          </button>
          
          {onRun && (
            <button
              onClick={handleRun}
              disabled={isRunning || readOnly}
              className="px-4 py-1.5 bg-green-600 hover:bg-green-700 disabled:bg-gray-600 text-white text-sm font-semibold rounded transition-colors flex items-center gap-2"
              title="Run Code (Ctrl/Cmd+Enter)"
            >
              {isRunning ? (
                <>
                  <div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin"></div>
                  Running...
                </>
              ) : (
                <>
                  ▶️ Run Code
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