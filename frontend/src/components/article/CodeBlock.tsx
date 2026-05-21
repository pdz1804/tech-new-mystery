'use client';

import { useState, memo } from 'react';
import SyntaxHighlighter from 'react-syntax-highlighter';
import {
  atomOneDark,
} from 'react-syntax-highlighter/dist/esm/styles/hljs';

interface CodeBlockProps {
  code: string;
  language: string;
}

const CodeBlock = memo(function CodeBlock({ code, language }: CodeBlockProps) {
  const [copied, setCopied] = useState(false);

  const handleCopy = async () => {
    try {
      await navigator.clipboard.writeText(code);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch (err) {
      console.error('Failed to copy code:', err);
    }
  };

  // Normalize language name for syntax highlighter
  const normalizeLanguage = (lang: string): string => {
    const mapping: Record<string, string> = {
      'bash': 'bash',
      'shell': 'bash',
      'sh': 'bash',
      'python': 'python',
      'py': 'python',
      'javascript': 'javascript',
      'js': 'javascript',
      'jsx': 'jsx',
      'typescript': 'typescript',
      'ts': 'typescript',
      'tsx': 'tsx',
      'java': 'java',
      'cpp': 'cpp',
      'c++': 'cpp',
      'csharp': 'csharp',
      'c#': 'csharp',
      'ruby': 'ruby',
      'rb': 'ruby',
      'go': 'go',
      'rust': 'rust',
      'rs': 'rust',
      'php': 'php',
      'swift': 'swift',
      'kotlin': 'kotlin',
      'scala': 'scala',
      'sql': 'sql',
      'html': 'html',
      'xml': 'xml',
      'css': 'css',
      'scss': 'scss',
      'sass': 'sass',
      'less': 'less',
      'json': 'json',
      'yaml': 'yaml',
      'yml': 'yaml',
      'toml': 'toml',
      'markdown': 'markdown',
      'md': 'markdown',
      'tex': 'tex',
      'latex': 'latex',
      'dockerfile': 'dockerfile',
      'makefile': 'makefile',
      'vim': 'vim',
      'regex': 'regex',
      'r': 'r',
      'matlab': 'matlab',
      'perl': 'perl',
      '': 'plaintext',
    };

    const normalized = lang.toLowerCase().trim();
    return mapping[normalized] || normalized || 'plaintext';
  };

  const highlightLanguage = normalizeLanguage(language);

  return (
    <div className="mb-6 overflow-hidden rounded-lg bg-slate-900 shadow-lg">
      {/* Header with language and copy button */}
      <div className="flex items-center justify-between bg-slate-800 px-4 py-2.5">
        <span className="text-xs font-bold uppercase tracking-wider text-slate-400 sm:text-sm">
          {language || 'code'}
        </span>
        <button
          type="button"
          onClick={handleCopy}
          className="inline-flex items-center gap-2 rounded bg-slate-700 px-2 py-1 text-xs font-medium text-slate-200 transition-colors hover:bg-slate-600 sm:px-3 sm:text-sm"
          title="Copy code"
        >
          {copied ? (
            <>
              <span>✓</span>
              <span className="hidden sm:inline">Copied!</span>
            </>
          ) : (
            <>
              <span>📋</span>
              <span className="hidden sm:inline">Copy</span>
            </>
          )}
        </button>
      </div>

      {/* Syntax highlighted code */}
      <div className="overflow-x-auto">
        <SyntaxHighlighter
          language={highlightLanguage}
          style={atomOneDark}
          customStyle={{
            margin: 0,
            padding: '1rem',
            fontSize: '0.875rem',
            lineHeight: '1.5',
            background: 'transparent',
          }}
          wrapLines={true}
          wrapLongLines={true}
          showLineNumbers={code.split('\n').length > 10}
          lineNumberStyle={{
            color: '#64748b',
            paddingRight: '1.5rem',
            userSelect: 'none',
          }}
        >
          {code}
        </SyntaxHighlighter>
      </div>
    </div>
  );
});

export default CodeBlock;
