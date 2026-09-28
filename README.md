# Autonomous Self-Healing E2E Test Automation Framework

An autonomous, self-healing end-to-end test automation framework powered by Google Gemini and Playwright Python.

## 🚀 Key Capabilities

- **DOM Reconnaissance**: Headless Chromium navigates to any web app and produces a token-efficient, pruned accessibility map.
- **BDD Test Planner Agent**: Transforms natural language scenarios into structured Gherkin test plans mapped to verified UI roles and assertions.
- **Automation Generator Agent**: Produces production-grade Page Object Model (`framework/pages/<feature>_page.py`) and Pytest test suites (`framework/tests/test_<feature>.py`) with web-first assertions.
- **Subprocess Runner & Self-Healer Agent**: Executes tests via `uv run pytest`, intercepts locator timeouts or assertion errors, diagnoses the root cause, and autonomously patches the code in-place.
- **Comprehensive Reporting**: Generates interactive HTML reports (`pytest-html`), Allure test results, Playwright trace zips, failure screenshots, and executive Markdown summaries.

## 🛠️ Stack & Constraints

- **Python**: `>=3.11` managed strictly by `uv`
- **LLM**: Google Gemini (`google-genai` / `langchain-google-genai`)
- **Browser Automation**: `playwright`
- **Test Engine**: `pytest`, `pytest-playwright`, `pytest-html`, `allure-pytest`
- **Design Pattern**: Page Object Model (POM) inheriting from `BasePage`

## 📦 Setup & Installation

1. **Clone & Initialize with `uv`**:
   ```bash
   uv venv
   uv sync
   uv run playwright install chromium
   ```

2. **Configure API Keys**:
   Copy `.env.example` to `.env`:
   ```bash
   cp .env.example .env
   ```
   Add your Gemini API Key:
   ```env
   GEMINI_API_KEY=your_gemini_api_key_here
   GEMINI_MODEL=gemini-2.5-flash
   DEFAULT_HEADLESS=true
   MAX_HEALING_ATTEMPTS=3
   PAGE_TIMEOUT=30000
   ```

## 🎯 Usage

Run the autonomous test generator and runner via the CLI:

```bash
uv run python run.py --url "https://www.saucedemo.com" --scenario "Log in with standard_user, add backpack to cart, and verify cart badge shows 1"
```

### CLI Flags

| Flag | Description | Default |
|---|---|---|
| `--url` | Target application URL (required) | - |
| `--scenario` | Natural language test requirement (required) | - |
| `--model` | Gemini model override | `gemini-2.5-flash` |
| `--headless` / `--no-headless` | Toggle headless or visible browser window | `True` |
| `--max-healing` | Maximum healing retry attempts | `3` |

## 📊 Reports & Artifacts

- **HTML Report**: `reports/report.html`
- **Executive Summary**: `reports/executive_summary.md`
- **Allure Results**: `reports/allure-results/`
- **Playwright Traces**: `reports/traces/` (exported on test failure)
- **Screenshots**: `reports/screenshots/` (captured on failure)
