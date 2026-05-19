'use client';

interface MarkdownContentProps {
  content: string;
  className?: string;
}

export function MarkdownContent({ content, className = '' }: MarkdownContentProps) {
  /**
   * Parse markdown content and render with proper styling.
   * Handles: headings, paragraphs, lists, bold, italic, links, code blocks
   */
  const parseMarkdown = (markdown: string): React.ReactNode[] => {
    const lines = markdown.split('\n');
    const elements: React.ReactNode[] = [];
    let i = 0;

    while (i < lines.length) {
      const line = lines[i];
      const trimmed = line.trim();

      // Skip empty lines but keep track of them for spacing
      if (!trimmed) {
        elements.push(<div key={`empty-${i}`} className="h-2" />);
        i++;
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
          <h1 key={`h1-${i}`} className="mt-8 mb-6 text-4xl font-bold text-slate-900">
            {trimmed.slice(2).trim()}
          </h1>
        );
        i++;
        continue;
      }

      if (trimmed.startsWith('## ')) {
        elements.push(
          <h2 key={`h2-${i}`} className="mt-6 mb-4 text-3xl font-bold text-slate-900">
            {trimmed.slice(3).trim()}
          </h2>
        );
        i++;
        continue;
      }

      if (trimmed.startsWith('### ')) {
        elements.push(
          <h3 key={`h3-${i}`} className="mt-5 mb-3 text-2xl font-bold text-slate-900">
            {trimmed.slice(4).trim()}
          </h3>
        );
        i++;
        continue;
      }

      // Lists
      if (trimmed.startsWith('- ')) {
        const listItems = [];
        while (i < lines.length && lines[i].trim().startsWith('- ')) {
          const itemText = lines[i].trim().slice(2);
          listItems.push(
            <li key={`li-${i}`} className="mb-2 text-slate-800 leading-relaxed">
              {renderInlineMarkdown(itemText)}
            </li>
          );
          i++;
        }
        elements.push(
          <ul key={`ul-${i}`} className="mb-6 ml-6 list-disc space-y-2">
            {listItems}
          </ul>
        );
        continue;
      }

      // Images: ![alt](url)
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

      // Italic/emphasis line
      if (trimmed.startsWith('*') && trimmed.endsWith('*')) {
        elements.push(
          <p key={`em-${i}`} className="mb-4 italic text-slate-600 leading-relaxed">
            {trimmed.slice(1, -1).trim()}
          </p>
        );
        i++;
        continue;
      }

      // Regular paragraph
      elements.push(
        <p key={`p-${i}`} className="mb-4 text-slate-800 leading-relaxed">
          {renderInlineMarkdown(trimmed)}
        </p>
      );
      i++;
    }

    return elements;
  };

  const renderInlineMarkdown = (text: string): React.ReactNode => {
    // Handle bold, italic, links, and images
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
      // Handle code
      else if (match[7]) {
        parts.push(
          <code key={`code-${match.index}`} className="rounded bg-slate-100 px-2 py-1 font-mono text-sm text-slate-900">
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

  return (
    <div className={`prose prose-lg max-w-none space-y-4 ${className}`}>
      {parseMarkdown(content)}
    </div>
  );
}
