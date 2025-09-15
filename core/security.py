import requests
from urllib.parse import urlparse
from typing import Optional, Tuple
from core.config import settings
from core.logging import get_logger

logger = get_logger(__name__)


def is_allowed_domain(url: str) -> bool:
    """Check if the domain is in the allowlist"""
    try:
        domain = urlparse(url).netloc.lower()
        return any(allowed in domain for allowed in settings.allowlist_domains)
    except Exception as e:
        logger.error(f"Error parsing domain from {url}: {e}")
        return False


def check_robots_txt(url: str) -> bool:
    """Check robots.txt for the given URL (best effort)"""
    try:
        parsed = urlparse(url)
        robots_url = f"{parsed.scheme}://{parsed.netloc}/robots.txt"
        
        response = requests.get(robots_url, timeout=5)
        if response.status_code != 200:
            return True  # Assume allowed if robots.txt not found
        
        robots_content = response.text.lower()
        user_agent = "*"
        
        # Simple robots.txt parsing
        lines = robots_content.split('\n')
        disallow_sections = []
        current_user_agent = None
        
        for line in lines:
            line = line.strip()
            if line.startswith('user-agent:'):
                current_user_agent = line.split(':', 1)[1].strip()
            elif line.startswith('disallow:') and current_user_agent in [user_agent, '*']:
                disallow_path = line.split(':', 1)[1].strip()
                disallow_sections.append(disallow_path)
        
        # Check if our path is disallowed
        path = parsed.path
        for disallow_path in disallow_sections:
            if path.startswith(disallow_path):
                logger.warning(f"URL {url} is disallowed by robots.txt")
                return False
        
        return True
        
    except Exception as e:
        logger.warning(f"Error checking robots.txt for {url}: {e}")
        return True  # Assume allowed on error


def validate_pdf_url(url: str) -> Tuple[bool, Optional[str]]:
    """Validate if URL points to a valid PDF"""
    try:
        # Check robots.txt first
        if not check_robots_txt(url):
            return False, "Disallowed by robots.txt"
        
        # Check domain allowlist
        if not is_allowed_domain(url):
            return False, f"Domain not in allowlist: {urlparse(url).netloc}"
        
        # HEAD request to check content type and size
        response = requests.head(url, timeout=10, allow_redirects=True)
        
        if response.status_code != 200:
            return False, f"HTTP {response.status_code}"
        
        content_type = response.headers.get('content-type', '').lower()
        if 'application/pdf' not in content_type:
            return False, f"Not a PDF: {content_type}"
        
        content_length = response.headers.get('content-length')
        if content_length:
            size_mb = int(content_length) / (1024 * 1024)
            if size_mb > settings.max_pdf_mb:
                return False, f"File too large: {size_mb:.1f}MB > {settings.max_pdf_mb}MB"
        
        return True, None
        
    except Exception as e:
        logger.error(f"Error validating PDF URL {url}: {e}")
        return False, str(e)
