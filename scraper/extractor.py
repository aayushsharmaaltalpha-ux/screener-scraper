import asyncio
import logging
import re
import tempfile
import os
from pathlib import Path
from playwright.async_api import Page

logger = logging.getLogger(__name__)


async def fetch_document_text(page: Page, doc_url: str) -> str | None:
    """
    Navigate to document URL and extract all text.
    Handles both PDF and HTML documents.
    Returns extracted text or None.
    """
    if not doc_url:
        return None

    # PDF path
    if doc_url.lower().endswith(".pdf") or "pdf" in doc_url.lower():
        return await _fetch_pdf_text(page, doc_url)

    # HTML / web page
    try:
        await page.goto(doc_url, wait_until="networkidle", timeout=40000)
        text = await page.evaluate("() => document.body.innerText")
        return text
    except Exception as e:
        logger.warning(f"fetch_document_text HTML error for {doc_url}: {e}")
        return None


async def _fetch_pdf_text(page: Page, pdf_url: str) -> str | None:
    """Download PDF and extract text using pdfplumber."""
    import httpx
    import pdfplumber

    try:
        # Get cookies from browser context
        cookies = await page.context.cookies()
        cookie_dict = {c["name"]: c["value"] for c in cookies}

        async with httpx.AsyncClient(follow_redirects=True, timeout=40) as client:
            resp = await client.get(
                pdf_url,
                headers={
                    "User-Agent": (
                        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                        "AppleWebKit/537.36 (KHTML, like Gecko) "
                        "Chrome/122.0.0.0 Safari/537.36"
                    ),
                    "Referer": "https://www.screener.in/",
                },
                cookies=cookie_dict,
            )
        resp.raise_for_status()

        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
            tmp.write(resp.content)
            tmp_path = tmp.name

        try:
            text_parts = []
            with pdfplumber.open(tmp_path) as pdf:
                for p in pdf.pages:
                    t = p.extract_text()
                    if t:
                        text_parts.append(t)
            return "\n".join(text_parts)
        finally:
            os.unlink(tmp_path)

    except Exception as e:
        logger.warning(f"_fetch_pdf_text error for {pdf_url}: {e}")
        return None


def extract_percent_responses(text: str) -> str | None:
    """
    Search text for '% responses' or '%responses' and extract the numeric value.
    Returns value as string (e.g. '45.23') or None.
    """
    if not text:
        return None

    patterns = [
        # "% Responses   45.23" or "% Responses: 45.23"
        r"%\s*responses?\s*[:\-]?\s*([\d,]+\.?\d*)\s*%?",
        # "Responses (%): 45.23"
        r"responses?\s*\(%\)\s*[:\-]?\s*([\d,]+\.?\d*)",
        # "45.23 % responses"
        r"([\d,]+\.?\d*)\s*%\s*responses?",
        # Table cell pattern – number immediately before/after column header
        r"(?i)%\s*response[s]?\D{0,10}([\d,]+\.?\d*)",
    ]

    text_lower = text.lower()
    for pattern in patterns:
        match = re.search(pattern, text_lower)
        if match:
            val = match.group(1).replace(",", "")
            return val

    return None


def extract_promoter_participation(text: str) -> str:
    """
    Determine if promoter participated in buyback.
    Returns 'Yes', 'No', or 'Unknown'.
    """
    if not text:
        return "Unknown"

    text_lower = text.lower()

    no_patterns = [
        r"promoter[s]?\s+(did\s+not|have\s+not|has\s+not|not)\s+participat",
        r"no\s+promoter\s+participat",
        r"promoter[s]?\s+participation\s*[:\-]?\s*nil",
        r"promoter[s]?\s+participation\s*[:\-]?\s*no",
        r"nil.*promoter",
    ]
    yes_patterns = [
        r"promoter[s]?\s+(have\s+)?participat",
        r"promoter[s]?\s+participation\s*[:\-]?\s*yes",
        r"participation\s+by\s+promoter[s]?",
    ]

    for p in no_patterns:
        if re.search(p, text_lower):
            return "No"

    for p in yes_patterns:
        if re.search(p, text_lower):
            return "Yes"

    return "Unknown"
