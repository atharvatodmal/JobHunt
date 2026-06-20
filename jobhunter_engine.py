"""
JobHunter Engine — Shared scraping logic for Telegram bot / Streamlit web app.
===============================================================================
DISCLAIMER: For educational purposes only. Respect each website's ToS.
"""

import asyncio
import hashlib
import logging
import os
import random
import re
import time
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple
from concurrent.futures import ThreadPoolExecutor
from urllib.parse import urlencode, urljoin, urlparse
from urllib.robotparser import RobotFileParser

import cloudscraper
import requests
from bs4 import BeautifulSoup

logging.basicConfig(
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger("JobHunter")

CACHE_TTL_SECONDS = 300
MAX_DETAIL_FETCHES = 5
REQUEST_TIMEOUT = 25
MAX_WORKERS = 5
RESPECT_ROBOTS_TXT = False


def extract_emails(text: str) -> List[str]:
    emails = set()
    pattern = r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}"
    for m in re.finditer(pattern, text):
        email = m.group().strip().lower()
        exclude = ["example", "domain.com", "email.com", "@company.com",
                    "@yourcompany", "@acmecorp"]
        if not any(x in email for x in exclude):
            emails.add(email)
    return list(emails)


def extract_phones(text: str) -> List[str]:
    phones = set()
    patterns = [
        r"(?:\+1[\s.-]?)?\(?\d{3}\)?[\s.-]?\d{3}[\s.-]?\d{4}(?:\s*(?:ext|x|ext\.)\s*\d{1,5})?",
        r"\+\d{1,3}[\s.-]?\(?\d{1,4}\)?[\s.-]?\d{1,4}[\s.-]?\d{2,9}",
        r"\b\d{3}[\s.-]\d{3}[\s.-]\d{4}\b",
    ]
    for pat in patterns:
        for m in re.finditer(pat, text):
            raw = m.group().strip()
            digits = re.sub(r"\D", "", raw)
            if 7 <= len(digits) <= 15:
                phones.add(raw)
    return list(phones)


_robots_cache: Dict[str, Optional[RobotFileParser]] = {}

def check_robots_txt(url: str, ua: str = "JobHunterBot/1.0") -> bool:
    try:
        parsed = urlparse(url)
        domain = parsed.netloc
        robots_url = f"{parsed.scheme}://{domain}/robots.txt"
        if domain not in _robots_cache:
            try:
                resp = requests.get(robots_url, timeout=10,
                                    headers={"User-Agent": "Mozilla/5.0"})
                if resp.status_code == 200 and resp.text.strip():
                    rp = RobotFileParser()
                    rp.parse(resp.text.splitlines())
                    _robots_cache[domain] = rp
                else:
                    rp = RobotFileParser()
                    rp.parse([""])
                    _robots_cache[domain] = rp
            except Exception:
                _robots_cache[domain] = None
        parser = _robots_cache.get(domain)
        return parser.can_fetch(ua, url) if parser else True
    except Exception:
        return True


class SearchCache:
    def __init__(self, ttl: int = CACHE_TTL_SECONDS):
        self._data: Dict[str, Tuple[float, Any]] = {}
        self._ttl = ttl

    def get(self, key: str):
        now = time.time()
        entry = self._data.get(key)
        if entry and now < entry[0]:
            return entry[1]
        if key in self._data:
            del self._data[key]
        return None

    def set(self, key: str, value: Any):
        self._data[key] = (time.time() + self._ttl, value)


search_cache = SearchCache()


class DomainRateLimiter:
    def __init__(self, min_delay: float = 1.0, max_delay: float = 2.5):
        self._last: Dict[str, float] = {}
        self._min = min_delay
        self._max = max_delay

    def wait_if_needed(self, domain: str):
        now = time.time()
        last = self._last.get(domain, 0.0)
        delay = random.uniform(self._min, self._max)
        if now - last < delay:
            time.sleep(delay - (now - last))
        self._last[domain] = time.time()


domain_limiter = DomainRateLimiter(min_delay=1.0, max_delay=2.5)


@dataclass
class Job:
    title: str
    company: str
    link: str
    email: str = "Not available"
    phone: str = "Not available"
    source: str = ""

    def dedup_key(self) -> str:
        raw = f"{self.title.lower().strip()}|{self.company.lower().strip()}"
        return hashlib.md5(raw.encode()).hexdigest()[:16]

    def to_dict(self) -> dict:
        return {
            "title": self.title,
            "company": self.company,
            "link": self.link,
            "email": self.email,
            "phone": self.phone,
            "source": self.source,
        }


def _create_scraper_session() -> cloudscraper.CloudScraper:
    return cloudscraper.create_scraper()


class BaseScraper:
    NAME = "base"
    BASE_URL = ""

    def _build_search_url(self, keywords: str) -> str:
        raise NotImplementedError

    def _fetch(self, url: str, soup: bool = True):
        domain = urlparse(url).netloc
        if RESPECT_ROBOTS_TXT and not check_robots_txt(url):
            logger.warning(f"[{self.NAME}] robots.txt disallows {url}")
            return None
        if not RESPECT_ROBOTS_TXT and not check_robots_txt(url):
            logger.info(f"[{self.NAME}] robots.txt disallows but proceeding (educational mode)")

        domain_limiter.wait_if_needed(domain)
        session = _create_scraper_session()

        try:
            resp = session.get(url, timeout=REQUEST_TIMEOUT, allow_redirects=True)
            resp.raise_for_status()
            if soup:
                return BeautifulSoup(resp.text, "lxml")
            return resp.text
        except Exception as e:
            logger.warning(f"[{self.NAME}] Request failed: {url[:80]} -> {e}")
            return None

    def search(self, keywords: str) -> List[Job]:
        url = self._build_search_url(keywords)
        logger.info(f"[{self.NAME}] Searching: {url}")
        soup = self._fetch(url)
        if soup is None:
            return []

        listings = self._parse_listings(soup)
        if not listings:
            logger.info(f"[{self.NAME}] No listings found.")
            return []

        seen: set = set()
        unique = []
        for item in listings:
            key = f"{item.get('title','')}|{item.get('company','')}"
            if key not in seen:
                seen.add(key)
                unique.append(item)

        jobs: List[Job] = []
        for i, item in enumerate(unique):
            item.setdefault("source", self.NAME)
            if i < MAX_DETAIL_FETCHES:
                email, phone = self._extract_contact(item.get("link", ""))
                item["email"] = email
                item["phone"] = phone
            else:
                item["email"] = "Not available"
                item["phone"] = "Not available"
            jobs.append(Job(**item))

        logger.info(f"[{self.NAME}] Returning {len(jobs)} jobs.")
        return jobs

    def _parse_listings(self, soup: BeautifulSoup) -> List[Dict[str, str]]:
        raise NotImplementedError

    def _extract_contact(self, url: str) -> Tuple[str, str]:
        if not url or url.startswith("#") or "javascript:" in url:
            return "Not available", "Not available"

        soup = self._fetch(url)
        if soup is None:
            return "Not available", "Not available"

        for tag in soup(["script", "style", "nav", "footer", "header", "noscript"]):
            tag.decompose()
        text = soup.get_text(separator=" ", strip=True)

        emails = []
        for a in soup.find_all("a", href=re.compile(r"^mailto:", re.I)):
            m = a["href"].replace("mailto:", "").split("?")[0].strip()
            if m and "@" in m:
                emails.append(m)
        if not emails:
            emails = extract_emails(text)

        phone_list = extract_phones(text)

        return (emails[0] if emails else "Not available",
                phone_list[0] if phone_list else "Not available")


class TalentScraper(BaseScraper):
    NAME = "Talent"
    BASE_URL = "https://www.talent.com"

    def _build_search_url(self, keywords: str) -> str:
        params = {"k": keywords, "days": "30"}
        return f"{self.BASE_URL}/jobs?{urlencode(params)}"

    def _parse_listings(self, soup: BeautifulSoup) -> List[Dict[str, str]]:
        jobs: List[Dict[str, str]] = []
        cards = (
            soup.find_all("article", attrs={"data-testid": "job-card-unified"})
            or soup.select("article.JobCard_card__TSiPB")
            or []
        )
        for card in cards:
            try:
                title_el = card.select_one("h2.JobCard_title__X32Qk") or card.select_one("h2")
                if not title_el:
                    continue
                title = title_el.get_text(strip=True)
                company_el = card.select_one(".JobCard_company__NmRol")
                company = company_el.get_text(strip=True) if company_el else "Unknown"
                link_el = card.select_one("a[href*='/view?id=']") or card.select_one("a[href*='/job/']")
                href = link_el.get("href", "") if link_el else ""
                link = urljoin(self.BASE_URL, href) if href else ""
                if title and link:
                    jobs.append({"title": title, "company": company, "link": link})
            except Exception as exc:
                logger.debug(f"[Talent] parse error: {exc}")
        return jobs


class DiceScraper(BaseScraper):
    NAME = "Dice"
    BASE_URL = "https://www.dice.com"

    def _build_search_url(self, keywords: str) -> str:
        params = {"q": keywords, "postedDate": "30"}
        return f"{self.BASE_URL}/jobs?{urlencode(params)}"

    def _parse_listings(self, soup: BeautifulSoup) -> List[Dict[str, str]]:
        jobs: List[Dict[str, str]] = []
        cards = soup.find_all("div", attrs={"data-testid": "job-card"})
        for card in cards:
            try:
                title_el = card.select_one('a[data-testid="job-search-job-detail-link"]')
                if not title_el:
                    continue
                title = title_el.get_text(strip=True)
                href = title_el.get("href", "")
                link = urljoin(self.BASE_URL, href) if href else ""
                company_el = card.select_one("span.logo p") or card.select_one("p[class*='line-clamp']")
                company = company_el.get_text(strip=True) if company_el else "Unknown"
                if title and link:
                    jobs.append({"title": title, "company": company, "link": link})
            except Exception as exc:
                logger.debug(f"[Dice] parse error: {exc}")
        return jobs


class LinkedInScraper(BaseScraper):
    NAME = "LinkedIn"
    BASE_URL = "https://www.linkedin.com"

    def _build_search_url(self, keywords: str) -> str:
        params = {"keywords": keywords, "f_TPR": "r2592000"}
        return f"{self.BASE_URL}/jobs/search?{urlencode(params)}"

    def _parse_listings(self, soup: BeautifulSoup) -> List[Dict[str, str]]:
        jobs: List[Dict[str, str]] = []
        cards = soup.select(".job-search-card") or soup.select(".base-card")
        for card in cards:
            try:
                link_el = card.select_one("a.base-card__full-link")
                if not link_el:
                    continue
                href = link_el.get("href", "")
                link = href if href.startswith("http") else urljoin(self.BASE_URL, href)
                span = link_el.select_one("span.sr-only")
                title = span.get_text(strip=True) if span else link_el.get_text(strip=True)
                company_el = card.select_one(".base-search-card__subtitle") or card.select_one("h4")
                company = company_el.get_text(strip=True) if company_el else "Unknown"
                if title and link:
                    jobs.append({"title": title, "company": company, "link": link})
            except Exception as exc:
                logger.debug(f"[LinkedIn] parse error: {exc}")
        return jobs

    def _extract_contact(self, url: str) -> Tuple[str, str]:
        return "Not available", "Not available"


class AdzunaAPISource:
    NAME = "Adzuna"
    BASE_URL = "https://api.adzuna.com/v1/api/jobs"

    def __init__(self):
        self.app_id = os.getenv("ADZUNA_APP_ID", "")
        self.api_key = os.getenv("ADZUNA_API_KEY", "")
        self.available = bool(self.app_id and self.api_key)
        if not self.available:
            logger.warning(f"[{self.NAME}] Skipping — set ADZUNA_APP_ID and ADZUNA_API_KEY env vars")

    def search(self, keywords: str) -> List[Job]:
        if not self.available:
            return []
        url = f"{self.BASE_URL}/in/search/1"
        params = {
            "app_id": self.app_id,
            "app_key": self.api_key,
            "what": keywords,
            "results_per_page": 20,
            "content-type": "application/json",
        }
        try:
            resp = requests.get(url, params=params, timeout=REQUEST_TIMEOUT)
            resp.raise_for_status()
            data = resp.json()
        except Exception as e:
            logger.error(f"[{self.NAME}] API request failed: {e}")
            return []

        jobs = []
        for item in data.get("results", []):
            try:
                title = item.get("title", "").strip()
                company = item.get("company", {}).get("display_name", "Unknown")
                link = item.get("redirect_url", "")
                if title and link:
                    jobs.append(Job(title=title, company=company, link=link,
                                    source=self.NAME))
            except Exception:
                continue

        logger.info(f"[{self.NAME}] Returning {len(jobs)} jobs.")
        return jobs


class JoobleAPISource:
    NAME = "Jooble"
    BASE_URL = "https://jooble.org/api"

    def __init__(self):
        self.api_key = os.getenv("JOOBLE_API_KEY", "")
        self.available = bool(self.api_key)
        if not self.available:
            logger.warning(f"[{self.NAME}] Skipping — set JOOBLE_API_KEY env var")

    def search(self, keywords: str) -> List[Job]:
        if not self.available:
            return []
        url = f"{self.BASE_URL}/{self.api_key}"
        payload = {"keywords": keywords, "location": "India"}
        try:
            resp = requests.post(url, json=payload, timeout=REQUEST_TIMEOUT)
            resp.raise_for_status()
            data = resp.json()
        except Exception as e:
            logger.error(f"[{self.NAME}] API request failed: {e}")
            return []

        jobs = []
        for item in data.get("jobs", []):
            try:
                title = item.get("title", "").strip()
                company = item.get("company", "Unknown")
                link = item.get("link", "")
                if title and link:
                    jobs.append(Job(title=title, company=company, link=link,
                                    source=self.NAME))
            except Exception:
                continue

        logger.info(f"[{self.NAME}] Returning {len(jobs)} jobs.")
        return jobs


class JobSearchEngine:
    def __init__(self):
        self.sources = [
            TalentScraper(),
            DiceScraper(),
            LinkedInScraper(),
            AdzunaAPISource(),
            JoobleAPISource(),
        ]

    def search(self, keywords: str) -> List[Job]:
        cache_key = hashlib.md5(keywords.lower().strip().encode()).hexdigest()
        cached = search_cache.get(cache_key)
        if cached is not None:
            logger.info(f"Cache hit for '{keywords}' ({len(cached)} jobs)")
            return cached

        all_jobs: List[Job] = []
        seen_keys: set = set()

        for source in self.sources:
            try:
                jobs = source.search(keywords)
                for job in jobs:
                    k = job.dedup_key()
                    if k not in seen_keys:
                        seen_keys.add(k)
                        all_jobs.append(job)
            except Exception as exc:
                logger.error(f"Source {source.NAME} failed: {exc}", exc_info=True)
                continue

        # ── Relevance filter: drop jobs with zero keyword overlap ──
        query_words = [w for w in keywords.lower().split() if len(w) > 1]
        if query_words:
            before = len(all_jobs)
            all_jobs = [j for j in all_jobs
                        if any(w in j.title.lower() for w in query_words)]
            dropped = before - len(all_jobs)
            if dropped:
                logger.info(f"Relevance filter removed {dropped} non-matching jobs")

        search_cache.set(cache_key, all_jobs)
        return all_jobs


_engine = JobSearchEngine()
_thread_pool = ThreadPoolExecutor(max_workers=MAX_WORKERS,
                                  thread_name_prefix="source")


async def search_jobs(keywords: str) -> List[dict]:
    """
    Public async entry point.
    Runs the search engine in a thread pool, returns list of job dicts.
    """
    loop = asyncio.get_event_loop()
    jobs = await loop.run_in_executor(_thread_pool, _engine.search, keywords)
    return [j.to_dict() for j in jobs]
