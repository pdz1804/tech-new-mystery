'use client';

import React, { useState, memo } from 'react';
import {
  AlertCircle,
  BookOpen,
  CheckCircle2,
  ChevronDown,
  ChevronUp,
  Code2,
  Loader2,
  Search,
  Settings,
} from 'lucide-react';
import { ToolIndicatorProps } from '@/types/chat';

function getToolIcon(toolName: string) {
  switch (toolName.toLowerCase()) {
    case 'web_search':
    case 'browser':
      return <Search className="h-4 w-4" aria-hidden="true" />;
    case 'code_interpreter':
      return <Code2 className="h-4 w-4" aria-hidden="true" />;
    case 'semantic_search':
      return <BookOpen className="h-4 w-4" aria-hidden="true" />;
    default:
      return <Settings className="h-4 w-4" aria-hidden="true" />;
  }
}

function formatToolArgs(args?: Record<string, unknown>): string {
  if (!args) return '';
  if (typeof args.query === 'string') return args.query;
  if (typeof args.code === 'string') return `Execute code (${args.code.split('\n').length} lines)`;
  return JSON.stringify(args).slice(0, 100);
}

function formatToolResult(result?: unknown): string {
  if (!result) return '';
  if (typeof result === 'string') return cleanToolText(result);
  if (Array.isArray(result)) return `Found ${result.length} results`;
  if (typeof result === 'object') {
    const value = result as Record<string, unknown>;
    if (typeof value.results_count === 'number') return `Found ${value.results_count} results`;
    if (typeof value.output === 'string') return value.output;
    if (typeof value.stdout === 'string') return value.stdout;
    return JSON.stringify(value).slice(0, 100);
  }
  return String(result).slice(0, 100);
}

function cleanToolText(value: string): string {
  let text = value.trim();

  if (text.startsWith('content=')) {
    text = text.slice('content='.length).trim();
  }

  if (
    (text.startsWith('"') && text.endsWith('"')) ||
    (text.startsWith("'") && text.endsWith("'"))
  ) {
    text = text.slice(1, -1);
  }

  return text
    .replace(/\\n/g, '\n')
    .replace(/\\"/g, '"')
    .trim();
}

function summarizeToolResult(value: string): string {
  const lines = value
    .split('\n')
    .map((line) => line.trim())
    .filter(Boolean);

  return lines.slice(0, 3).join(' ');
}

export const ToolIndicator = memo(function ToolIndicator({
  tool_name,
  tool_id,
  status,
  args,
  result,
}: ToolIndicatorProps) {
  const [expanded, setExpanded] = useState(false);
  const argsDisplay = formatToolArgs(args);
  const resultDisplay = formatToolResult(result);
  const resultPreview = summarizeToolResult(resultDisplay);

  return (
    <div className="w-full overflow-hidden rounded-2xl border border-black/5 border-t-white/70 bg-white/62 shadow-[inset_0_1px_0_rgba(255,255,255,0.72),0_10px_24px_rgba(15,23,42,0.05)] backdrop-blur-2xl">
      <button
        type="button"
        onClick={() => setExpanded((value) => !value)}
        className="flex w-full items-center justify-between gap-3 px-3 py-2 text-left transition-colors hover:bg-white/70"
      >
        <div className="flex min-w-0 flex-1 items-center gap-3">
          {status === 'executing' && <Loader2 className="h-4 w-4 flex-shrink-0 animate-spin text-blue-600" />}
          {status === 'completed' && <CheckCircle2 className="h-4 w-4 flex-shrink-0 text-emerald-600" />}
          {status === 'failed' && <AlertCircle className="h-4 w-4 flex-shrink-0 text-red-600" />}

          <span className="flex flex-shrink-0 items-center gap-2 text-sm font-semibold text-slate-800">
            {getToolIcon(tool_name)}
            {tool_name}
          </span>

          <span className="rounded-full bg-slate-100/80 px-2 py-1 text-xs font-medium text-slate-600">{status}</span>

          {argsDisplay && <span className="min-w-0 flex-1 truncate text-xs text-slate-500">{argsDisplay}</span>}
        </div>

        {expanded ? (
          <ChevronUp className="h-4 w-4 flex-shrink-0 text-slate-400" />
        ) : (
          <ChevronDown className="h-4 w-4 flex-shrink-0 text-slate-400" />
        )}
      </button>

      {!expanded && status === 'completed' && resultPreview && (
        <div className="border-t border-black/5 px-3 py-2">
          <p className="line-clamp-2 text-xs leading-5 text-slate-600">
            {resultPreview}
          </p>
          <span className="mt-1 inline-flex text-[11px] font-medium text-[#007AFF]">
            See tool details
          </span>
        </div>
      )}

      {expanded && (
        <div className="space-y-3 border-t border-black/5 bg-white/48 p-3 text-xs">
          <div>
            <p className="mb-1 font-medium text-slate-500">Tool ID</p>
            <code className="block break-all rounded bg-white px-2 py-1 font-mono text-slate-700">{tool_id}</code>
          </div>

          {args && (
            <div>
              <p className="mb-1 font-medium text-slate-500">Arguments</p>
              <pre className="max-h-32 overflow-x-auto rounded bg-white px-2 py-1 font-mono text-slate-700">
                {JSON.stringify(args, null, 2)}
              </pre>
            </div>
          )}

          {resultDisplay && (
            <div>
              <p className="mb-1 font-medium text-slate-500">Result</p>
              <p className="rounded bg-white px-2 py-1 text-slate-700">{resultDisplay}</p>
            </div>
          )}
        </div>
      )}
    </div>
  );
});

ToolIndicator.displayName = 'ToolIndicator';
