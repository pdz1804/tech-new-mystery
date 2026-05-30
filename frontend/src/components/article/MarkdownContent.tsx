'use client';

import { useMemo, useCallback } from 'react';
import CodeBlock from './CodeBlock';

interface MarkdownContentProps {
  content: string;
  className?: string;
}

export function MarkdownContent({ content, className = '' }: MarkdownContentProps) {
  const parseMarkdown = useCallback((markdown: string): React.ReactNode[] => {
    const lines = markdown.split('\n');
    const elements: React.ReactNode[] = [];
    let i = 0;

    while (i < lines.length) {
      const line = lines[i];
      const trimmed = line.trim();

      // Skip empty lines but keep track for spacing
      if (!trimmed) {
        elements.push(<div key={`empty-${i}`} className="h-2" />);
        i++;
        continue;
      }

      // Code blocks: ``` ... ```
      if (trimmed.startsWith('```')) {
        const codeBlockLines: string[] = [];
        const languageMatch = trimmed.match(/^```(\w*)/);
        const language = languageMatch ? languageMatch[1] : '';
        i++;

        while (i < lines.length && !lines[i].trim().startsWith('```')) {
          codeBlockLines.push(lines[i]);
          i++;
        }

        if (i < lines.length && lines[i].trim().startsWith('```')) {
          i++;
        }

        const codeContent = codeBlockLines.join('\n').trimEnd();
        elements.push(
          <CodeBlock
            key={`code-${i}`}
            code={codeContent}
            language={language}
          />
        );
        continue;
      }

      // Blockquotes
      if (trimmed.startsWith('> ')) {
        const quoteLines: string[] = [];
        while (i < lines.length && lines[i].trim().startsWith('> ')) {
          quoteLines.push(lines[i].trim().slice(2));
          i++;
        }
        elements.push(
          <blockquote key={`quote-${i}`} className="mb-6 border-l-4 border-slate-300 pl-4 italic text-slate-700">
            {quoteLines.join(' ')}
          </blockquote>
        );
        continue;
      }

      // Horizontal rule
      if (trimmed === '---') {
        elements.push(
          <hr key={`hr-${i}`} className="my-8 border-slate-300" />
        );
        i++;
        continue;
      }

      // Headings
      if (trimmed.startsWith('# ')) {
        elements.push(
          <h1 key={`h1-${i}`} className="mt-8 mb-6 text-3xl sm:text-4xl font-bold text-slate-900">
            {renderInlineMarkdown(trimmed.slice(2).trim())}
          </h1>
        );
        i++;
        continue;
      }

      if (trimmed.startsWith('## ')) {
        elements.push(
          <h2 key={`h2-${i}`} className="mt-6 mb-4 text-2xl sm:text-3xl font-bold text-slate-900">
            {renderInlineMarkdown(trimmed.slice(3).trim())}
          </h2>
        );
        i++;
        continue;
      }

      if (trimmed.startsWith('### ')) {
        elements.push(
          <h3 key={`h3-${i}`} className="mt-5 mb-3 text-xl sm:text-2xl font-bold text-slate-900">
            {renderInlineMarkdown(trimmed.slice(4).trim())}
          </h3>
        );
        i++;
        continue;
      }

      // Unordered lists
      if (trimmed.startsWith('- ')) {
        const listItems: React.ReactNode[] = [];
        while (i < lines.length && lines[i].trim().startsWith('- ')) {
          const itemText = lines[i].trim().slice(2);
          listItems.push(
            <li key={`li-${i}`} className="mb-2 text-slate-800 leading-relaxed text-sm sm:text-base">
              {renderInlineMarkdown(itemText)}
            </li>
          );
          i++;
        }
        elements.push(
          <ul key={`ul-${i}`} className="mb-6 ml-4 sm:ml-6 list-disc space-y-2">
            {listItems}
          </ul>
        );
        continue;
      }

      // Ordered lists
      if (/^\d+\. /.test(trimmed)) {
        const listItems: React.ReactNode[] = [];
        while (i < lines.length && /^\d+\. /.test(lines[i].trim())) {
          const itemText = lines[i].trim().replace(/^\d+\. /, '');
          listItems.push(
            <li key={`oli-${i}`} className="mb-2 text-slate-800 leading-relaxed text-sm sm:text-base">
              {renderInlineMarkdown(itemText)}
            </li>
          );
          i++;
        }
        elements.push(
          <ol key={`ol-${i}`} className="mb-6 ml-4 sm:ml-6 list-decimal space-y-2">
            {listItems}
          </ol>
        );
        continue;
      }

      // Tables: | header | header |
      if (trimmed.startsWith('|')) {
        const tableLines: string[] = [];
        let isHeaderSeparator = false;

        // Collect all table rows
        while (i < lines.length && lines[i].trim().startsWith('|')) {
          const currentLine = lines[i].trim();
          tableLines.push(currentLine);

          // Check if next line is separator (|---|---|)
          if (i + 1 < lines.length) {
            const nextLine = lines[i + 1].trim();
            if (nextLine.startsWith('|') && nextLine.match(/\|\s*[-:]+\s*\|/)) {
              isHeaderSeparator = true;
            }
          }
          i++;
        }

        if (tableLines.length >= 2 && isHeaderSeparator) {
          // Parse table
          const headerRow = tableLines[0].split('|').map(cell => cell.trim()).filter(cell => cell);
          const bodyRows = tableLines.slice(2);

          elements.push(
            <div key={`table-${i}`} className="my-6 overflow-x-auto">
              <table className="w-full border-collapse border border-slate-300">
                <thead className="bg-slate-100">
                  <tr>
                    {headerRow.map((header, idx) => (
                      <th
                        key={`th-${idx}`}
                        className="border border-slate-300 px-4 py-3 text-left font-semibold text-slate-900"
                      >
                        {renderInlineMarkdown(header)}
                      </th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {bodyRows.map((row, rowIdx) => {
                    const cells = row.split('|').map(cell => cell.trim()).filter(cell => cell);
                    return (
                      <tr key={`tr-${rowIdx}`} className="hover:bg-slate-50">
                        {cells.map((cell, cellIdx) => (
                          <td
                            key={`td-${rowIdx}-${cellIdx}`}
                            className="border border-slate-300 px-4 py-2 text-slate-800"
                          >
                            {renderInlineMarkdown(cell)}
                          </td>
                        ))}
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          );
          continue;
        }
      }

      // Images
      const imageMatch = trimmed.match(/^!\[([^\]]*)\]\(([^)]+)\)$/);
      if (imageMatch) {
        const [, altText, imageUrl] = imageMatch;
        elements.push(
          <div key={`img-${i}`} className="my-6">
            <img
              src={imageUrl}
              alt={altText || 'Article image'}
              className="max-w-full h-auto rounded-lg shadow-md"
              onError={(e) => {
                const target = e.target as HTMLImageElement;
                target.style.display = 'none';
              }}
            />
          </div>
        );
        i++;
        continue;
      }

      // Italic/emphasis line (starts and ends with *)
      if (trimmed.startsWith('*') && trimmed.endsWith('*') && trimmed.length > 2) {
        elements.push(
          <p key={`em-${i}`} className="mb-4 italic text-slate-600 leading-relaxed text-sm sm:text-base">
            {trimmed.slice(1, -1).trim()}
          </p>
        );
        i++;
        continue;
      }

      // Regular paragraph
      elements.push(
        <p key={`p-${i}`} className="mb-4 text-slate-800 leading-relaxed text-sm sm:text-base">
          {renderInlineMarkdown(trimmed)}
        </p>
      );
      i++;
    }

    return elements;
  }, []);

  const renderInlineMarkdown = (text: string): React.ReactNode => {
    const parts: React.ReactNode[] = [];
    let currentIndex = 0;

    const inlineRegex = /!\[([^\]]*)\]\(([^)]+)\)|\*\*([^*]+)\*\*|\*([^*]+)\*|_([^_]+)_|__([^_]+)__|`([^`]+)`|\[([^\]]+)\]\(([^)]+)\)/g;
    let match;

    while ((match = inlineRegex.exec(text)) !== null) {
      // Add text before match
      if (match.index > currentIndex) {
        parts.push(text.substring(currentIndex, match.index));
      }

      // Handle images: ![alt](url)
      if (match[1] !== undefined && match[2]) {
        parts.push(
          <img
            key={`inline-img-${match.index}`}
            src={match[2]}
            alt={match[1] || 'Image'}
            className="inline max-h-6 align-middle rounded"
            onError={(e) => {
              const target = e.target as HTMLImageElement;
              target.style.display = 'none';
            }}
          />
        );
      }
      // Handle bold
      else if (match[3]) {
        parts.push(
          <strong key={`bold-${match.index}`} className="font-bold text-slate-900">
            {match[3]}
          </strong>
        );
      }
      // Handle italic (single asterisk)
      else if (match[4]) {
        parts.push(
          <em key={`italic-${match.index}`} className="italic">
            {match[4]}
          </em>
        );
      }
      // Handle italic (underscore)
      else if (match[5]) {
        parts.push(
          <em key={`italic2-${match.index}`} className="italic">
            {match[5]}
          </em>
        );
      }
      // Handle bold (underscore)
      else if (match[6]) {
        parts.push(
          <strong key={`bold2-${match.index}`} className="font-bold text-slate-900">
            {match[6]}
          </strong>
        );
      }
      // Handle inline code
      else if (match[7]) {
        parts.push(
          <code key={`code-${match.index}`} className="rounded bg-slate-100 px-2 py-1 font-mono text-xs sm:text-sm text-slate-900">
            {match[7]}
          </code>
        );
      }
      // Handle links: [text](url)
      else if (match[8] && match[9]) {
        parts.push(
          <a
            key={`link-${match.index}`}
            href={match[9]}
            target="_blank"
            rel="noopener noreferrer"
            className="font-semibold text-blue-600 hover:underline"
          >
            {match[8]}
          </a>
        );
      }

      currentIndex = inlineRegex.lastIndex;
    }

    // Add remaining text
    if (currentIndex < text.length) {
      parts.push(text.substring(currentIndex));
    }

    return parts.length > 0 ? parts : text;
  };

  const parsedContent = useMemo(() => parseMarkdown(content), [content, parseMarkdown]);

  return (
    <div className={`prose prose-sm sm:prose-base lg:prose-lg max-w-none space-y-4 ${className}`}>
      {parsedContent}
    </div>
  );
}

