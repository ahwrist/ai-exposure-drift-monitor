# Contributing to AEDM

Thank you for your interest in contributing to the AI Exposure Drift Monitor. This guide covers development setup, code standards, and the contribution process.

## Development Setup

### Prerequisites

- Python 3.11 or higher
- [uv](https://github.com/astral-sh/uv) (recommended) or pip

### Installation

```bash
# Clone the repository
git clone https://github.com/ahwrist/ai-exposure-drift-monitor.git
cd ai-exposure-drift-monitor

# Install with development dependencies
pip install -e ".[dev]"

# Or with uv
uv pip install -e ".[dev]"
```

### Verify Setup

```bash
# Run tests
pytest

# Run linter
ruff check src/ tests/

# Run type checker
mypy src/aedm/

# Run formatter
ruff format --check src/ tests/
```

## Code Style

### Python Standards

- **Python 3.11+** — Use modern syntax (type unions with `|`, `match` statements where appropriate)
- **Full type annotations** — All function signatures must be typed. Target mypy strict mode.
- **Pydantic v2** — All data models use Pydantic `BaseModel`
- **Google-style docstrings** — On all public functions and classes
- **No print statements** — Use `structlog` for any logging in library code

### Linting and Formatting

This project uses [Ruff](https://github.com/astral-sh/ruff) for both linting and formatting:

```bash
# Check for issues
ruff check src/ tests/

# Auto-fix issues
ruff check --fix src/ tests/

# Format code
ruff format src/ tests/
```

### Type Checking

```bash
mypy src/aedm/
```

## Testing

### Running Tests

```bash
# Full suite
pytest

# With coverage
pytest --cov=aedm --cov-report=term-missing

# Single file
pytest tests/test_exposure.py

# Verbose output
pytest -v
```

### Test Conventions

- Test files mirror the source structure: `test_exposure.py` tests `analysis/exposure.py`
- Shared fixtures live in `tests/conftest.py`
- Every analysis function needs at minimum:
  - One happy-path test
  - One edge-case test
  - One test using the sample data
- Use descriptive test names: `test_exposure_score_high_soc_group_returns_critical_tier`

## Pull Request Process

1. **Fork and branch** — Create a feature branch from `main` with a descriptive name (`feature/add-tenure-segment`, `fix/drift-empty-series`)

2. **Make changes** — Follow the code standards above. Keep PRs focused on a single concern.

3. **Test** — Ensure all tests pass and coverage doesn't decrease:
   ```bash
   pytest --cov=aedm
   ruff check src/ tests/
   mypy src/aedm/
   ```

4. **Commit** — Write clear commit messages describing the *why*, not just the *what*:
   ```
   Add tenure-based segmentation to demographic analysis

   Enables disparity analysis by employee tenure bands (0-2y, 2-5y, 5-10y, 10y+),
   complementing existing gender/education/pay dimensions.
   ```

5. **Open PR** — Target the `main` branch. Include:
   - Summary of changes
   - Any new dependencies and why they're needed
   - Test plan
   - Screenshots for any UI/output changes

6. **Review** — Address feedback promptly. Keep discussion in the PR.

## Issue Labels

| Label | Description |
|-------|-------------|
| `bug` | Something isn't working as expected |
| `enhancement` | New feature or improvement |
| `documentation` | Documentation improvements |
| `methodology` | Statistical methodology changes or additions |
| `data` | Data format, schema, or sample data changes |
| `good first issue` | Good for newcomers |

## Architecture Notes

Before making significant changes, review [ARCHITECTURE.md](ARCHITECTURE.md) to understand the system design. Key constraints:

- Analysis functions must be **pure**: data in, result out, no side effects
- No ML frameworks (tensorflow, torch, etc.) — this is a statistical analysis tool
- All exposure scores are normalized to [0, 1]
- Output is designed for a CHRO audience, not just data scientists

## Code of Conduct

This project follows the [Contributor Covenant Code of Conduct](https://www.contributor-covenant.org/version/2/1/code_of_conduct/). Be respectful, constructive, and inclusive.

## Questions?

Open an issue with the `question` label, or start a discussion in the GitHub Discussions tab.
