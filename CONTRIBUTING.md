# Contributing to PSDL Inspector

Thank you for your interest in contributing to PSDL Inspector! This document provides guidelines and instructions for contributing.

## Code of Conduct

Please be respectful and constructive in all interactions. We welcome contributors of all backgrounds and experience levels.

## Getting Started

### Prerequisites

- Python 3.9+
- Node.js 18+
- Git
- Docker (optional, for containerized development)

### Development Setup

1. **Fork and clone the repository**
   ```bash
   git clone https://github.com/YOUR_USERNAME/psdl-inspector.git
   cd psdl-inspector
   ```

2. **Set up the backend**
   ```bash
   cd backend
   python -m venv .venv
   source .venv/bin/activate  # Windows: .venv\Scripts\activate
   pip install -r requirements.txt
   pip install -r requirements-dev.txt  # If available
   ```

3. **Set up the frontend**
   ```bash
   cd frontend
   npm install
   ```

4. **Start development servers**
   ```bash
   # Terminal 1 - Backend
   cd backend && source .venv/bin/activate
   uvicorn app.main:app --reload --port 8200

   # Terminal 2 - Frontend
   cd frontend
   npm run dev
   ```

5. **Verify setup**
   - Frontend: http://localhost:9806
   - Backend API: http://localhost:8200
   - API docs: http://localhost:8200/docs

### Alternative: Docker Development

For a quick start with the full environment (including OMOP vocabulary):

```bash
docker-compose up
```

This builds both frontend and backend with all dependencies. See [docs/DEPLOYMENT.md](docs/DEPLOYMENT.md) for details.

## How to Contribute

### Reporting Bugs

1. Check if the bug has already been reported in [Issues](https://github.com/Chesterguan/psdl-inspector/issues)
2. If not, create a new issue with:
   - Clear, descriptive title
   - Steps to reproduce
   - Expected vs actual behavior
   - Environment details (OS, browser, versions)
   - Screenshots if applicable

### Suggesting Features

1. Check existing issues and discussions for similar suggestions
2. Create a new issue with:
   - Use case description
   - Proposed solution
   - Alternatives considered

### Pull Requests

1. **Create a feature branch**
   ```bash
   git checkout -b feature/your-feature-name
   ```

2. **Make your changes**
   - Follow the code style guidelines below
   - Write tests if applicable
   - Update documentation as needed

3. **Test your changes**
   ```bash
   # Backend
   cd backend && python -m pytest  # If tests exist

   # Frontend
   cd frontend && npm run lint
   npm run build
   ```

4. **Commit your changes**
   ```bash
   git add .
   git commit -m "feat: add your feature description"
   ```

   Use [conventional commits](https://www.conventionalcommits.org/):
   - `feat:` - New feature
   - `fix:` - Bug fix
   - `docs:` - Documentation only
   - `refactor:` - Code refactoring
   - `test:` - Adding tests
   - `chore:` - Maintenance tasks

5. **Push and create PR**
   ```bash
   git push origin feature/your-feature-name
   ```
   Then create a Pull Request on GitHub.

## Code Style

### Python (Backend)

- Follow PEP 8
- Use type hints
- Docstrings for public functions
- Maximum line length: 100 characters

```python
def validate_scenario(content: str) -> tuple[PSDLScenario | None, list[ValidationError], list[ValidationError]]:
    """Validate a PSDL scenario.

    Args:
        content: PSDL YAML content

    Returns:
        Tuple of (scenario, errors, warnings)
    """
    ...
```

### TypeScript (Frontend)

- ESLint + Prettier configuration
- Use TypeScript strict mode
- Prefer functional components
- Use meaningful variable names

```typescript
interface Props {
  scenario: ScenarioOutline;
  onValidate: (result: ValidationResult) => void;
}

export default function ScenarioEditor({ scenario, onValidate }: Props) {
  // ...
}
```

## Project Structure

```
psdl-inspector/
├── backend/                 # FastAPI backend
│   ├── app/
│   │   ├── main.py         # Application entry
│   │   ├── models/         # Pydantic schemas
│   │   ├── routers/        # API endpoints (validate, outline, export, generate, vocabulary, meds)
│   │   └── services/       # Business logic
│   ├── psdl_meds/          # Shared MEDS writer/validator/CLI (installable as `psdl-meds`, also embedded by PSDL Workbench)
│   ├── data/vocabulary/    # OMOP vocabulary (included in Docker)
│   ├── Dockerfile
│   └── requirements.txt
├── frontend/               # Next.js frontend
│   ├── src/
│   │   ├── app/           # Next.js app router
│   │   ├── components/    # React components
│   │   ├── context/       # React context
│   │   └── lib/           # Utilities
│   ├── Dockerfile
│   └── package.json
├── docs/                   # Documentation
├── docker-compose.yml      # Full stack deployment
└── README.md
```

## Areas for Contribution

### High Priority
- Bug fixes
- Documentation improvements
- Test coverage
- Accessibility improvements

### Feature Ideas
- Editable DAG (visual scenario editing)
- Lint rules for PSDL best practices
- Scenario registry/versioning
- Semantic diff between scenario versions
- Additional LLM provider integrations
- `psdl_meds` improvements — additional MEDS-DEV task labels, unit harmonization, alternative input formats for `psdl-meds convert`

### Good First Issues
Look for issues labeled `good first issue` in the GitHub Issues.

## Questions?

- Open a [Discussion](https://github.com/Chesterguan/psdl-inspector/discussions)
- Check existing documentation in `/docs`
- Review the [PSDL specification](https://github.com/Chesterguan/PSDL)

## License

By contributing, you agree that your contributions will be licensed under the MIT License.
