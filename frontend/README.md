# PSDL Inspector Frontend

Next.js frontend for PSDL Inspector - the governance middleware for clinical scenarios.

## Tech Stack

- **Next.js 14** - React framework with App Router
- **React 18** - UI library
- **Tailwind CSS** - Styling
- **CodeMirror 6** - YAML editor
- **ReactFlow** - DAG visualization
- **dagre** - Automatic graph layout
- **lucide-react** - Icons

## Development

```bash
# Install dependencies
npm install

# Start development server (port 9806)
npm run dev

# Build for production
npm run build

# Run linting
npm run lint

# Type checking
npx tsc --noEmit
```

## Project Structure

```
src/
├── app/
│   ├── page.tsx          # Main wizard page
│   ├── layout.tsx        # Root layout with theme provider
│   └── globals.css       # Global styles + CSS variables
├── components/
│   ├── Editor.tsx        # CodeMirror YAML editor
│   ├── GenerationPanel.tsx # AI scenario generation
│   ├── ValidationPanel.tsx # Validation display
│   ├── OutlineTree.tsx   # Semantic tree view
│   ├── DAGView.tsx       # ReactFlow visualization
│   ├── BundlePanel.tsx   # Certified bundle preview
│   ├── GovernancePanel.tsx # IRB documentation
│   ├── ExportButton.tsx  # Bundle download
│   ├── CanonicalView.tsx # Canonical summary
│   ├── ThemeToggle.tsx   # Dark/light mode
│   └── Logo.tsx          # SVG logo
├── context/
│   └── ThemeContext.tsx  # Theme state management
└── lib/
    └── api.ts            # Backend API client
```

## Environment Variables

```bash
# Backend API URL (default: http://localhost:8200)
NEXT_PUBLIC_API_URL=http://localhost:8200
```

## Features

### Wizard Workflow
3-step process: Input → Preview → Export

### AI Generation
- OpenAI GPT-4o-mini integration
- Local Ollama support
- Auto-validation and error correction
- Clinical context input

### DAG Visualization
- Custom node types (Signal, Trend, Gate, Logic)
- Automatic layout with dagre
- Severity-based coloring
- Hover details panel

### Theme Support
- Light and dark modes
- CSS custom properties for colors
- Persistent preference

## API Integration

The frontend connects to the FastAPI backend at `/api/*`:

- `GET /api/version` - Version info
- `GET /api/generate/status` - LLM availability
- `POST /api/generate/scenario` - AI generation
- `POST /api/validate` - Validation
- `POST /api/outline` - Semantic outline
- `POST /api/export/bundle` - Certified bundle
- `POST /api/export/irb-document` - Word export

*Updated: 2025-12-17*
