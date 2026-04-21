import re
import logging
from difflib import SequenceMatcher


def setup_logging(level: str = "INFO"):
    logging.basicConfig(
        level=getattr(logging, level.upper(), logging.INFO),
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%H:%M:%S",
    )


def similarity(a: str, b: str) -> float:
    return SequenceMatcher(None, a.lower(), b.lower()).ratio()


def best_match(query: str, candidates: list[str]) -> str | None:
    """Return the best matching candidate for query, or None if score < 0.5."""
    if not candidates:
        return None
    scored = [(similarity(query, c), c) for c in candidates]
    best_score, best_cand = max(scored, key=lambda x: x[0])
    return best_cand if best_score >= 0.5 else None


def clean_text(text: str) -> str:
    """Normalize whitespace and remove control characters."""
    text = re.sub(r"[\r\n\t]+", " ", text)
    text = re.sub(r"\s{2,}", " ", text)
    return text.strip()


def truncate(text: str, max_len: int = 200) -> str:
    return text[:max_len] + "..." if len(text) > max_len else text
