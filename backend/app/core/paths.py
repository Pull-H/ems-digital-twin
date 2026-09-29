from pathlib import Path


BACKEND_DIR = Path(__file__).resolve().parents[2]
PROJECT_ROOT = BACKEND_DIR.parent
DATA_DIR = PROJECT_ROOT / "data"
DOCS_DIR = PROJECT_ROOT / "docs"
RESEARCH_DIR = PROJECT_ROOT / "research"
RUNTIME_DIR = DATA_DIR / "runtime"
REPORTS_DIR = PROJECT_ROOT / "reports"
