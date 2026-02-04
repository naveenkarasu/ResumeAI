"""
Google Dorking Job Scraper

Uses advanced Google search operators (dorks) to find job listings
from sources not easily accessible through APIs.

Based on real dorking techniques:
- site: - Restrict to specific domains
- intitle: - Search page titles
- inurl: - Search within URLs
- filetype: - Target specific file types (pdf, xls, doc)
- intext: - Search body text
- after: - Filter by date
- OR / | - Combine searches

Sources:
- https://dev.to/nish2005karsh/google-dorking-for-job-hunting-advanced-tricks-commands-part-2-oeo
- https://dev.to/csituma/using-google-dorking-to-land-a-job-1lgk
- https://www.stationx.net/google-dorks-cheat-sheet/
"""

import httpx
import logging
import re
from typing import List, Optional, AsyncGenerator, Dict, Any
from datetime import datetime, date, timedelta
from urllib.parse import urlencode, quote_plus
from dataclasses import dataclass
from enum import Enum

from .base_scraper import BaseScraper, ScrapedJob, register_scraper

logger = logging.getLogger(__name__)


# ============== DORK TEMPLATES ==============
# Each template contains real Google dork patterns

DORK_QUERIES = {
    # === CYBERSECURITY DORKS ===
    "cyber_greenhouse": {
        "name": "Cybersecurity - Greenhouse/Lever",
        "category": "cyber",
        "query": '(site:greenhouse.io OR site:lever.co) ("security engineer" OR "SOC analyst" OR "penetration tester" OR "cybersecurity") "apply"',
        "description": "Security roles on top ATS platforms"
    },
    "cyber_bigtech": {
        "name": "Cybersecurity - Big Tech",
        "category": "cyber",
        "query": '(site:careers.google.com OR site:amazon.jobs OR site:careers.microsoft.com) intitle:security (engineer OR analyst OR architect)',
        "description": "Security positions at FAANG companies"
    },
    "cyber_vendors": {
        "name": "Cybersecurity - Security Vendors",
        "category": "cyber",
        "query": '(site:crowdstrike.com OR site:paloaltonetworks.com OR site:cisco.com) inurl:careers (security OR threat OR SOC)',
        "description": "Jobs at security product companies"
    },
    "cyber_remote": {
        "name": "Cybersecurity - Remote",
        "category": "cyber",
        "query": 'intitle:"security engineer" OR intitle:"SOC analyst" "remote" "apply now" -expired',
        "description": "Remote security positions"
    },
    "cyber_pdf": {
        "name": "Cybersecurity - PDF Job Descriptions",
        "category": "cyber",
        "query": 'filetype:pdf ("security analyst" OR "penetration tester") "job description" "requirements"',
        "description": "Detailed job descriptions in PDF format"
    },

    # === SOFTWARE ENGINEERING DORKS ===
    "swe_ats": {
        "name": "Software Engineer - ATS Platforms",
        "category": "swe",
        "query": '(site:greenhouse.io OR site:lever.co OR site:ashbyhq.com) ("software engineer" OR "developer") "apply"',
        "description": "SWE roles across ATS platforms"
    },
    "swe_remote": {
        "name": "Software Engineer - Remote",
        "category": "swe",
        "query": '(site:lever.co OR site:greenhouse.io) (developer OR engineer) "remote" ("react" OR "python" OR "node")',
        "description": "Remote developer positions"
    },
    "swe_fullstack": {
        "name": "Full Stack Developer",
        "category": "swe",
        "query": 'intitle:"full stack" (developer OR engineer) (site:greenhouse.io OR site:lever.co) "apply"',
        "description": "Full stack positions"
    },
    "swe_backend": {
        "name": "Backend Engineer",
        "category": "swe",
        "query": '(site:greenhouse.io OR site:lever.co) intitle:"backend engineer" ("python" OR "java" OR "golang")',
        "description": "Backend engineering roles"
    },
    "swe_frontend": {
        "name": "Frontend Developer",
        "category": "swe",
        "query": '(site:greenhouse.io OR site:lever.co) ("frontend" OR "front-end") (developer OR engineer) ("react" OR "vue" OR "angular")',
        "description": "Frontend development positions"
    },

    # === DATA & ML DORKS ===
    "data_ml": {
        "name": "ML Engineer - ATS",
        "category": "data",
        "query": '(site:greenhouse.io OR site:lever.co) ("machine learning" OR "ML engineer" OR "data scientist") "apply"',
        "description": "ML and data science roles"
    },
    "data_ai_companies": {
        "name": "AI Companies",
        "category": "data",
        "query": '(site:openai.com OR site:anthropic.com OR site:deepmind.com) inurl:careers ("engineer" OR "scientist")',
        "description": "AI company positions"
    },
    "data_remote": {
        "name": "Data Science - Remote",
        "category": "data",
        "query": 'intitle:"data scientist" OR intitle:"ML engineer" "remote" "python" "apply"',
        "description": "Remote data science positions"
    },

    # === DEVOPS & SRE DORKS ===
    "devops_ats": {
        "name": "DevOps - ATS Platforms",
        "category": "devops",
        "query": '(site:greenhouse.io OR site:lever.co) ("DevOps" OR "SRE" OR "site reliability") "apply"',
        "description": "DevOps/SRE on ATS platforms"
    },
    "devops_cloud": {
        "name": "Cloud Engineer",
        "category": "devops",
        "query": '(site:greenhouse.io OR site:lever.co) ("cloud engineer" OR "platform engineer") ("AWS" OR "GCP" OR "Azure")',
        "description": "Cloud and platform engineering"
    },
    "devops_kubernetes": {
        "name": "Kubernetes/Docker",
        "category": "devops",
        "query": 'intitle:"DevOps" OR intitle:"platform engineer" ("kubernetes" OR "docker" OR "terraform") "apply"',
        "description": "Container/K8s focused roles"
    },

    # === STARTUP DORKS ===
    "startup_yc": {
        "name": "Y Combinator Startups",
        "category": "startup",
        "query": 'site:workatastartup.com OR (site:ycombinator.com inurl:companies) (engineer OR developer)',
        "description": "YC-backed company positions"
    },
    "startup_angel": {
        "name": "AngelList/Wellfound",
        "category": "startup",
        "query": '(site:angel.co OR site:wellfound.com) inurl:jobs ("software" OR "engineer" OR "developer")',
        "description": "Startup jobs on Wellfound"
    },
    "startup_early": {
        "name": "Early Stage Startups",
        "category": "startup",
        "query": 'intitle:"founding engineer" OR intitle:"first engineer" (site:greenhouse.io OR site:lever.co) "equity"',
        "description": "Early employee positions"
    },

    # === REMOTE-FIRST DORKS ===
    "remote_boards": {
        "name": "Remote Job Boards",
        "category": "remote",
        "query": '(site:weworkremotely.com OR site:remoteok.com OR site:remote.co) (developer OR engineer)',
        "description": "Remote-first job boards"
    },
    "remote_any": {
        "name": "Any Remote Tech Job",
        "category": "remote",
        "query": 'intitle:"remote" (developer OR engineer OR "software") "fully remote" "apply" -hybrid',
        "description": "Fully remote positions"
    },

    # === BIG TECH DORKS ===
    "bigtech_faang": {
        "name": "FAANG Companies",
        "category": "bigtech",
        "query": '(site:careers.google.com OR site:amazon.jobs OR site:metacareers.com OR site:jobs.apple.com OR site:jobs.netflix.com) (engineer OR developer)',
        "description": "FAANG job postings"
    },
    "bigtech_msft": {
        "name": "Microsoft",
        "category": "bigtech",
        "query": 'site:careers.microsoft.com (engineer OR developer OR "program manager")',
        "description": "Microsoft positions"
    },
    "bigtech_nvidia": {
        "name": "NVIDIA & AI Hardware",
        "category": "bigtech",
        "query": '(site:nvidia.com OR site:amd.com OR site:intel.com) inurl:careers (engineer OR scientist)',
        "description": "AI hardware companies"
    },

    # === GENERAL ATS DORKS ===
    "ats_all": {
        "name": "All ATS Platforms",
        "category": "ats",
        "query": '(site:greenhouse.io OR site:lever.co OR site:workable.com OR site:ashbyhq.com OR site:smartrecruiters.com) "apply"',
        "description": "Search across all major ATS"
    },
    "ats_workday": {
        "name": "Workday ATS",
        "category": "ats",
        "query": 'site:myworkdayjobs.com (engineer OR developer OR analyst) "apply"',
        "description": "Companies using Workday"
    },

    # === GOVERNMENT & EDU DORKS ===
    "gov_federal": {
        "name": "Government Tech Jobs",
        "category": "gov",
        "query": 'site:.gov intitle:"job opening" (IT OR technology OR cyber OR developer) filetype:pdf',
        "description": "Federal tech positions"
    },
    "edu_university": {
        "name": "University Tech Jobs",
        "category": "edu",
        "query": 'site:.edu inurl:careers (developer OR engineer OR "IT specialist") "apply"',
        "description": "University tech positions"
    },

    # === SPECIALTY DORKS ===
    "pdf_jd": {
        "name": "PDF Job Descriptions",
        "category": "specialty",
        "query": 'filetype:pdf "job description" (engineer OR developer) "requirements" "qualifications"',
        "description": "Detailed JDs in PDF format"
    },
    "spreadsheet_jobs": {
        "name": "Spreadsheet Job Lists",
        "category": "specialty",
        "query": 'filetype:xls OR filetype:xlsx inurl:"jobs" OR inurl:"openings" (tech OR engineer)',
        "description": "Job listings in spreadsheets"
    },
    "hiring_now": {
        "name": "Actively Hiring",
        "category": "specialty",
        "query": 'intitle:"we are hiring" OR intitle:"now hiring" (developer OR engineer) "apply"',
        "description": "Companies actively hiring"
    },
}

# Category definitions for frontend
DORK_CATEGORIES = {
    "cyber": {"name": "Cybersecurity", "icon": "🔒", "description": "Security Engineer, SOC, Pentester"},
    "swe": {"name": "Software Engineering", "icon": "💻", "description": "Full Stack, Backend, Frontend"},
    "data": {"name": "Data & ML", "icon": "🤖", "description": "Data Science, ML, AI"},
    "devops": {"name": "DevOps & SRE", "icon": "⚙️", "description": "Platform, Cloud, Infrastructure"},
    "startup": {"name": "Startups", "icon": "🚀", "description": "Early-stage, YC, Equity"},
    "remote": {"name": "Remote-First", "icon": "🌍", "description": "Fully remote positions"},
    "bigtech": {"name": "Big Tech", "icon": "🏢", "description": "FAANG, Microsoft, NVIDIA"},
    "ats": {"name": "ATS Platforms", "icon": "📋", "description": "Greenhouse, Lever, Workday"},
    "gov": {"name": "Government", "icon": "🏛️", "description": "Federal, Public sector"},
    "edu": {"name": "Education", "icon": "🎓", "description": "University positions"},
    "specialty": {"name": "Specialty", "icon": "🔍", "description": "PDF JDs, Spreadsheets"},
}


@register_scraper("google_dork")
class GoogleDorkScraper(BaseScraper):
    """
    Scraper using Google dorking to find hidden job listings.
    Uses DuckDuckGo as it's more permissive than Google.
    """

    RATE_LIMIT_SECONDS = 2

    @property
    def source_name(self) -> str:
        return "google_dork"

    @property
    def base_url(self) -> str:
        return "https://html.duckduckgo.com"

    def __init__(self):
        super().__init__()
        self._client: Optional[httpx.AsyncClient] = None

    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is None:
            self._client = httpx.AsyncClient(
                timeout=30.0,
                follow_redirects=True,
                headers={
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                    "Accept-Language": "en-US,en;q=0.9",
                }
            )
        return self._client

    async def _close_client(self):
        if self._client:
            await self._client.aclose()
            self._client = None

    def get_available_dorks(self) -> Dict[str, Any]:
        """Get all available dork queries organized by category"""
        result = {
            "categories": DORK_CATEGORIES,
            "queries": {}
        }

        for query_id, query_data in DORK_QUERIES.items():
            category = query_data["category"]
            if category not in result["queries"]:
                result["queries"][category] = []

            result["queries"][category].append({
                "id": query_id,
                "name": query_data["name"],
                "description": query_data["description"],
                "query_preview": query_data["query"][:80] + "..." if len(query_data["query"]) > 80 else query_data["query"]
            })

        return result

    def _detect_category(self, keywords: List[str]) -> str:
        """Auto-detect best category from keywords"""
        keywords_lower = " ".join(keywords).lower()

        mappings = [
            (["cyber", "security", "soc", "pentest", "infosec", "threat", "incident"], "cyber"),
            (["data scien", "machine learning", "ml ", "ai ", "deep learning", "nlp"], "data"),
            (["devops", "sre", "site reliability", "platform", "kubernetes", "k8s"], "devops"),
            (["startup", "early stage", "founding", "seed", "series a", "equity"], "startup"),
            (["remote", "work from home", "wfh", "distributed"], "remote"),
            (["google", "amazon", "meta", "apple", "microsoft", "faang"], "bigtech"),
        ]

        for terms, category in mappings:
            if any(term in keywords_lower for term in terms):
                return category

        return "swe"  # Default

    def _build_custom_query(
        self,
        keywords: List[str],
        location: Optional[str] = None,
        category: Optional[str] = None,
    ) -> str:
        """Build a custom dork query from user input"""
        # Determine category
        if not category or category == "auto":
            category = self._detect_category(keywords)

        # Get a base query from the category
        category_queries = [q for q_id, q in DORK_QUERIES.items() if q["category"] == category]

        if category_queries:
            base_query = category_queries[0]["query"]
        else:
            # Fallback: ATS search
            base_query = DORK_QUERIES["ats_all"]["query"]

        # Add user keywords
        user_keywords = " ".join(f'"{k}"' if " " in k else k for k in keywords)

        # Add location/remote modifier
        location_part = ""
        if location:
            if location.lower() == "remote":
                location_part = ' "remote" "fully remote"'
            else:
                location_part = f' "{location}"'

        # Combine
        query = f"({base_query}) {user_keywords}{location_part}"
        return query

    async def _search_duckduckgo(self, query: str, max_results: int = 30) -> List[Dict]:
        """Search DuckDuckGo and extract results"""
        results = []

        try:
            client = await self._get_client()
            params = {"q": query}
            url = f"{self.base_url}/html/?{urlencode(params)}"

            await self._rate_limit()
            response = await client.get(url)

            if response.status_code != 200:
                logger.warning(f"DuckDuckGo returned {response.status_code}")
                return results

            from bs4 import BeautifulSoup
            soup = BeautifulSoup(response.text, "html.parser")

            for result in soup.select(".result")[:max_results]:
                link_elem = result.select_one(".result__a")
                snippet_elem = result.select_one(".result__snippet")

                if link_elem:
                    href = link_elem.get("href", "")
                    if "uddg=" in href:
                        import urllib.parse
                        parsed = urllib.parse.parse_qs(urllib.parse.urlparse(href).query)
                        if "uddg" in parsed:
                            href = urllib.parse.unquote(parsed["uddg"][0])

                    title = link_elem.get_text(strip=True)
                    snippet = snippet_elem.get_text(strip=True) if snippet_elem else ""

                    if href and title:
                        results.append({
                            "url": href,
                            "title": title,
                            "snippet": snippet,
                        })

            logger.info(f"Found {len(results)} results from DuckDuckGo")

        except Exception as e:
            logger.error(f"Error searching DuckDuckGo: {e}")

        return results

    def _extract_company(self, url: str, title: str) -> str:
        """Extract company name from URL or title"""
        patterns = [
            (r"boards\.greenhouse\.io/(\w+)", None),
            (r"(\w+)\.greenhouse\.io", None),
            (r"jobs\.lever\.co/(\w+)", None),
            (r"apply\.workable\.com/(\w+)", None),
            (r"(\w+)\.ashbyhq\.com", None),
            (r"careers\.google\.com", "Google"),
            (r"amazon\.jobs", "Amazon"),
            (r"metacareers\.com", "Meta"),
            (r"careers\.microsoft\.com", "Microsoft"),
            (r"jobs\.apple\.com", "Apple"),
            (r"jobs\.netflix\.com", "Netflix"),
            (r"nvidia\.com", "NVIDIA"),
            (r"openai\.com", "OpenAI"),
            (r"anthropic\.com", "Anthropic"),
            (r"(\w+)\.myworkdayjobs\.com", None),
        ]

        for pattern, default_name in patterns:
            match = re.search(pattern, url, re.IGNORECASE)
            if match:
                if default_name:
                    return default_name
                return match.group(1).replace("-", " ").replace("_", " ").title()

        # Try "at Company" pattern in title
        at_match = re.search(r'\bat\s+([^|–-]+?)(?:\s*[-|–]|$)', title, re.IGNORECASE)
        if at_match:
            return at_match.group(1).strip()

        return "Unknown Company"

    def _parse_result_to_job(self, result: Dict, dork_id: str) -> Optional[ScrapedJob]:
        """Parse a search result into a ScrapedJob"""
        url = result.get("url", "")
        title = result.get("title", "")
        snippet = result.get("snippet", "")

        if not url or not title:
            return None

        # Skip non-job URLs
        job_patterns = ["job", "career", "position", "apply", "opening", "hiring", "role", "vacancy"]
        url_lower = url.lower()
        title_lower = title.lower()
        if not any(p in url_lower or p in title_lower for p in job_patterns):
            return None

        company = self._extract_company(url, title)

        # Clean title
        clean_title = re.sub(r'\s*[-|–@]\s*.+$', '', title).strip()
        clean_title = re.sub(rf'\s+at\s+{re.escape(company)}.*$', '', clean_title, flags=re.IGNORECASE).strip()
        if not clean_title:
            clean_title = title

        # Detect location type
        location_type = None
        location = None
        text_lower = (title + " " + snippet).lower()

        if "remote" in text_lower or "work from home" in text_lower:
            location_type = "remote"
            location = "Remote"
        elif "hybrid" in text_lower:
            location_type = "hybrid"
        elif "on-site" in text_lower or "onsite" in text_lower:
            location_type = "onsite"

        # Try to extract city/state
        loc_match = re.search(r'\b([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*,\s*[A-Z]{2})\b', title + " " + snippet)
        if loc_match:
            location = loc_match.group(1)

        return ScrapedJob(
            url=url,
            title=clean_title,
            company_name=company,
            description=snippet,
            source=f"dork_{dork_id}",
            location=location,
            location_type=location_type,
            posted_date=date.today(),
            raw_data={"dork_id": dork_id, **result},
        )

    async def search(
        self,
        keywords: List[str],
        location: Optional[str] = None,
        filters: Optional[Dict] = None
    ) -> AsyncGenerator[ScrapedJob, None]:
        """
        Search for jobs using Google dorking.

        Args:
            keywords: Search keywords
            location: Location filter (or "remote")
            filters: Additional filters:
                - dork_id: Specific dork query to use
                - dork_category: Category of dorks to use
                - custom_query: Custom dork query string
        """
        if not keywords:
            return

        filters = filters or {}
        dork_id = filters.get("dork_id")
        dork_category = filters.get("dork_category")
        custom_query = filters.get("custom_query")

        # Determine which query to use
        if custom_query:
            query = custom_query
            query_id = "custom"
        elif dork_id and dork_id in DORK_QUERIES:
            query = DORK_QUERIES[dork_id]["query"]
            query_id = dork_id
            # Add user keywords
            user_keywords = " ".join(f'"{k}"' if " " in k else k for k in keywords)
            query = f"({query}) {user_keywords}"
        else:
            # Build custom query based on keywords and category
            query = self._build_custom_query(keywords, location, dork_category)
            query_id = dork_category or self._detect_category(keywords)

        logger.info(f"Dork query [{query_id}]: {query[:100]}...")

        results = await self._search_duckduckgo(query)

        seen_urls = set()
        seen_titles = set()

        for result in results:
            url = result.get("url", "")
            if url in seen_urls:
                continue
            seen_urls.add(url)

            job = self._parse_result_to_job(result, query_id)
            if job:
                key = f"{job.title.lower()}|{job.company_name.lower()}"
                if key in seen_titles:
                    continue
                seen_titles.add(key)
                yield job

    async def get_job_details(self, url: str) -> Optional[ScrapedJob]:
        return None


# ============== API HELPERS ==============

def get_dork_strategies() -> Dict[str, Any]:
    """Get available dork strategies for API/frontend"""
    scraper = GoogleDorkScraper()
    return scraper.get_available_dorks()


def get_dork_categories() -> List[Dict[str, str]]:
    """Get dork categories for dropdown"""
    return [
        {"id": cat_id, **cat_data}
        for cat_id, cat_data in DORK_CATEGORIES.items()
    ]
