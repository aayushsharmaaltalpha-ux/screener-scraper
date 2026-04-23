import asyncio
import logging
from typing import AsyncGenerator
from playwright.async_api import async_playwright

from scraper.browser import (
    get_browser,
    new_page,
    search_company,
    navigate_to_announcements,
    find_post_announcement,
    random_delay,
)
from scraper.extractor import fetch_document_text, extract_percent_responses, extract_promoter_participation

logger = logging.getLogger(__name__)

MAX_CONCURRENCY = 3
MAX_RETRIES = 2


def _empty_result(company: str, error: str) -> dict:
    return {
        "Company Name": company,
        "% Responses": "",
        "Promoter Participated": "",
        "Document URL": "",
        "Status": "Failed",
        "Error Message": error,
    }


async def scrape_company(browser, company: str) -> dict:
    """End-to-end scrape for a single company. Returns result dict."""
    page = None
    try:
        page = await new_page(browser)

        # Step 1: Search
        company_url = await search_company(page, company)
        if not company_url:
            return _empty_result(company, "Company not found on screener.in")

        logger.info(f"[{company}] Found page: {company_url}")

        # Step 2: Navigate to Announcements
        found = await navigate_to_announcements(page, company_url)
        if not found:
            return _empty_result(company, "Could not navigate to Announcements section")

        # Step 3: Find 'post' announcement
        doc_url, ann_title = await find_post_announcement(page)
        if not doc_url:
            return _empty_result(company, "No announcement with keyword 'post' found")

        logger.info(f"[{company}] Document URL: {doc_url}")

        # Step 4: Extract document text
        text = await fetch_document_text(page, doc_url)
        if not text:
            return _empty_result(company, "Could not extract text from document")

        # Step 5: Parse values
        pct_responses = extract_percent_responses(text)
        promoter = extract_promoter_participation(text)

        return {
            "Company Name": company,
            "% Responses": pct_responses or "Not found",
            "Promoter Participated": promoter,
            "Document URL": doc_url,
            "Status": "Success",
            "Error Message": "",
        }

    except Exception as e:
        logger.error(f"[{company}] Unhandled error: {e}")
        return _empty_result(company, str(e))
    finally:
        if page:
            try:
                await page.context.close()
            except Exception:
                pass


async def scrape_with_retry(browser, company: str) -> dict:
    """Retry wrapper — up to MAX_RETRIES attempts."""
    last_result = None
    for attempt in range(1, MAX_RETRIES + 2):
        if attempt > 1:
            wait = 2 ** attempt
            logger.info(f"[{company}] Retry {attempt - 1}/{MAX_RETRIES} after {wait}s")
            await asyncio.sleep(wait)
        result = await scrape_company(browser, company)
        last_result = result
        if result["Status"] == "Success":
            return result
    return last_result


async def run_pipeline(companies: list[str]) -> AsyncGenerator[tuple[int, dict], None]:
    """
    Async generator — yields (index, result) as each company finishes.
    Limits concurrency to MAX_CONCURRENCY.
    """
    semaphore = asyncio.Semaphore(MAX_CONCURRENCY)
    results: dict[int, dict] = {}
    next_yield = 0

    async with async_playwright() as playwright:
        browser = await get_browser(playwright)

        async def process(idx: int, company: str):
            async with semaphore:
                await random_delay(300, 900)
                result = await scrape_with_retry(browser, company)
                results[idx] = result

        tasks = [asyncio.create_task(process(i, c)) for i, c in enumerate(companies)]

        # Yield results in original order as they complete
        while next_yield < len(companies):
            await asyncio.sleep(0.2)
            while next_yield in results:
                yield next_yield, results[next_yield]
                next_yield += 1

        # Ensure all tasks finish
        await asyncio.gather(*tasks, return_exceptions=True)

        # Yield any remaining results
        while next_yield < len(companies):
            if next_yield in results:
                yield next_yield, results[next_yield]
                next_yield += 1
            else:
                await asyncio.sleep(0.1)

        await browser.close()
