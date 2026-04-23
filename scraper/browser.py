import asyncio
import logging
import random
from playwright.async_api import async_playwright, Page, Browser, TimeoutError as PWTimeout

logger = logging.getLogger(__name__)

BASE_URL = "https://www.screener.in"
SEARCH_URL = f"{BASE_URL}/api/company/search/?q={{query}}&v=3&fts=1"


async def random_delay(min_ms: int = 800, max_ms: int = 2400):
    await asyncio.sleep(random.uniform(min_ms / 1000, max_ms / 1000))


async def get_browser(playwright) -> Browser:
    return await playwright.chromium.launch(
        headless=True,
        args=["--no-sandbox", "--disable-blink-features=AutomationControlled"],
    )


async def new_page(browser: Browser) -> Page:
    context = await browser.new_context(
        viewport={"width": 1280, "height": 800},
        user_agent=(
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/122.0.0.0 Safari/537.36"
        ),
        java_script_enabled=True,
    )
    page = await context.new_page()
    await page.add_init_script(
        "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})"
    )
    return page


async def search_company(page: Page, company_name: str) -> str | None:
    """Search for company on screener.in and return the company page URL."""
    try:
        await page.goto(BASE_URL, wait_until="domcontentloaded", timeout=30000)
        await random_delay(500, 1200)

        search_input = page.locator("input#search, input[name='q'], .search-input input").first
        await search_input.wait_for(state="visible", timeout=10000)
        await search_input.click()
        await random_delay(200, 500)

        for char in company_name:
            await search_input.type(char, delay=random.randint(40, 120))

        await random_delay(800, 1500)

        # Wait for autocomplete suggestions
        suggestion = page.locator(".search-results a, ul.ui-autocomplete li a, [data-url]").first
        try:
            await suggestion.wait_for(state="visible", timeout=8000)
            href = await suggestion.get_attribute("href") or await suggestion.get_attribute("data-url")
            if href:
                return BASE_URL + href if href.startswith("/") else href
        except PWTimeout:
            pass

        # Fallback: press Enter and grab first result
        await search_input.press("Enter")
        await random_delay(1500, 2500)
        try:
            await page.wait_for_url("**/company/**", timeout=10000)
            return page.url
        except PWTimeout:
            return None

    except Exception as e:
        logger.warning(f"search_company error for '{company_name}': {e}")
        return None


async def navigate_to_announcements(page: Page, company_url: str) -> bool:
    """Navigate to company page and click the Announcements tab."""
    try:
        await page.goto(company_url, wait_until="domcontentloaded", timeout=30000)
        await random_delay(800, 1500)

        # Try clicking Announcements tab/link
        ann_link = page.locator("a:has-text('Announcements'), [href*='announcements']").first
        await ann_link.wait_for(state="visible", timeout=10000)
        await ann_link.click()
        await random_delay(1000, 2000)
        return True
    except Exception as e:
        logger.warning(f"navigate_to_announcements error: {e}")
        return False


async def find_post_announcement(page: Page) -> tuple[str | None, str | None]:
    """
    Look for announcements containing 'post' keyword.
    Returns (document_url, announcement_title) or (None, None).
    """
    try:
        # Some pages have a search/filter box within announcements
        ann_search = page.locator(
            "input[placeholder*='Search'], input[placeholder*='Filter'], "
            ".announcements input, #announcements input"
        ).first
        try:
            await ann_search.wait_for(state="visible", timeout=5000)
            await ann_search.fill("post")
            await random_delay(800, 1500)
        except PWTimeout:
            logger.info("No announcement search box found, scanning all announcements")

        # Collect announcement rows
        rows = await page.locator(
            ".announcement-row, .announcement a, #announcements li, "
            "table.data-table tbody tr, .announcements-list .row"
        ).all()

        if not rows:
            # Try generic approach: all links inside announcements section
            rows = await page.locator("#announcements a, .announcements a").all()

        for row in rows:
            text = (await row.inner_text()).lower()
            if "post" in text:
                href = await row.get_attribute("href")
                title = await row.inner_text()
                if href:
                    url = BASE_URL + href if href.startswith("/") else href
                    return url, title.strip()

        return None, None

    except Exception as e:
        logger.warning(f"find_post_announcement error: {e}")
        return None, None
