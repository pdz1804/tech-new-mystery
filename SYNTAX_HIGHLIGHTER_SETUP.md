# Syntax Highlighter Setup

## Installation

To enable syntax highlighting for code blocks in articles, install the `react-syntax-highlighter` package:

```bash
cd frontend
npm install react-syntax-highlighter
npm install --save-dev @types/react-syntax-highlighter
```

Or with yarn:

```bash
cd frontend
yarn add react-syntax-highlighter
yarn add --dev @types/react-syntax-highlighter
```

## Features

Once installed, the code block renderer will support:

### Language-Specific Syntax Highlighting
- **Web**: JavaScript, TypeScript, JSX, TSX, HTML, CSS, SCSS, LESS
- **Backend**: Python, Java, C++, C#, PHP, Ruby, Go, Rust, Kotlin, Scala
- **Data**: JSON, YAML, TOML, SQL, XML
- **DevOps**: Bash, Shell, Dockerfile, Makefile
- **And many more...**: Swift, Perl, R, MATLAB, Vim, Regex, LaTeX, etc.

### Visual Features
- **Dark theme** (Atom One Dark) with syntax-aware coloring
- **Line numbers** for code blocks with 10+ lines
- **Copy button** with visual feedback
- **Responsive design** that works on mobile and desktop
- **Language label** showing the code language
- **Horizontal scrolling** for long lines
- **Memoized component** for optimal performance

## Supported Languages

Common languages and their aliases:

| Language | Aliases |
|----------|---------|
| Python | `python`, `py` |
| JavaScript | `javascript`, `js` |
| TypeScript | `typescript`, `ts` |
| Bash | `bash`, `shell`, `sh` |
| Java | `java` |
| C++ | `cpp`, `c++` |
| C# | `csharp`, `c#` |
| Go | `go` |
| Rust | `rust`, `rs` |
| SQL | `sql` |
| JSON | `json` |
| HTML | `html` |
| CSS | `css` |
| YAML | `yaml`, `yml` |

## Example Markdown

When creating articles, code blocks will automatically use the appropriate syntax highlighting:

````markdown
```python
def hello_world():
    print("Hello, World!")
```

```javascript
const greet = (name) => {
  console.log(`Hello, ${name}!`);
};
```

```bash
npm install react-syntax-highlighter
```
````

## Performance

The CodeBlock component is memoized to prevent unnecessary re-renders when the markdown content changes. The syntax highlighter uses an optimized virtual DOM approach for better performance.
