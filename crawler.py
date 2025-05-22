import requests
from bs4 import BeautifulSoup
import time
import random
import urllib.robotparser
from urllib.parse import urlparse, urljoin
import logging
from utils import setup_logger, get_random_delay

# Setup logger
logger = setup_logger()

class ClearnetCrawler:
    def __init__(self, respect_robots=True, crawl_depth=3, link_limit=5, mode="exploratory"):
        """
        Initialize the crawler with configuration parameters.
        
        Args:
            respect_robots (bool): Whether to respect robots.txt
            crawl_depth (int): Maximum depth to crawl
            link_limit (int): Maximum links to follow per page
            mode (str): Crawling mode (exploratory, deep_dive, stealth)
        """
        self.respect_robots = respect_robots
        self.crawl_depth = crawl_depth
        self.link_limit = link_limit
        self.mode = mode
        
        # Set user agent
        self.user_agent = "ClearnetResearchAssistant/1.0 (+https://example.com/bot; research-purpose)"
        
        # Configure mode-specific settings
        if mode == "exploratory":
            self.link_limit = min(link_limit * 2, 20)  # More links for exploration
            self.delay_min, self.delay_max = 1, 3
        elif mode == "deep_dive":
            self.crawl_depth = min(crawl_depth + 2, 10)  # Deeper crawling
            self.delay_min, self.delay_max = 2, 4
        elif mode == "stealth":
            self.delay_min, self.delay_max = 3, 7  # Longer delays for stealth
        else:
            self.delay_min, self.delay_max = 2, 4  # Default
        
        # Initialize cache for robots.txt
        self.robots_cache = {}
        
        # Initialize visited URLs
        self.visited_urls = set()
        
        logger.info(f"Initialized crawler with mode={mode}, depth={self.crawl_depth}, link_limit={self.link_limit}")
    
    def is_allowed(self, url):
        """Check if URL is allowed by robots.txt"""
        if not self.respect_robots:
            return True
            
        parsed_url = urlparse(url)
        base_url = f"{parsed_url.scheme}://{parsed_url.netloc}"
        
        # Check cache first
        if base_url in self.robots_cache:
            rp = self.robots_cache[base_url]
        else:
            # Initialize and cache robots parser
            rp = urllib.robotparser.RobotFileParser()
            rp.set_url(urljoin(base_url, "/robots.txt"))
            try:
                rp.read()
                self.robots_cache[base_url] = rp
            except Exception as e:
                logger.warning(f"Error reading robots.txt for {base_url}: {e}")
                return True  # Assume allowed if can't read robots.txt
        
        return rp.can_fetch(self.user_agent, url)
    
    def extract_content(self, url, html):
        """Extract content, links, and resources from HTML"""
        soup = BeautifulSoup(html, 'html.parser')
        
        # Extract text content
        text_elements = soup.find_all(['p', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'li', 'span', 'div'])
        text_content = ' '.join([elem.get_text(strip=True) for elem in text_elements if elem.get_text(strip=True)])
        
        # Extract links (only internal links)
        base_domain = urlparse(url).netloc
        links = []
        for a_tag in soup.find_all('a', href=True):
            link = urljoin(url, a_tag['href'])
            parsed_link = urlparse(link)
            # Only include internal links with http/https scheme
            if (parsed_link.netloc == base_domain or not parsed_link.netloc) and \
               parsed_link.scheme in ['http', 'https'] and \
               '#' not in parsed_link.path:  # Exclude anchors
                links.append(link)
        
        # Limit links based on configuration
        links = links[:self.link_limit]
        
        # Extract resources (images, scripts, stylesheets)
        resources = {
            'images': [urljoin(url, img['src']) for img in soup.find_all('img', src=True)],
            'scripts': [urljoin(url, script['src']) for script in soup.find_all('script', src=True)],
            'stylesheets': [urljoin(url, link['href']) for link in soup.find_all('link', rel="stylesheet", href=True)]
        }
        
        # Extract title
        title = soup.title.string if soup.title else "No title"
        
        # Extract metadata
        metadata = {
            'title': title,
            'description': soup.find('meta', attrs={'name': 'description'})['content'] if soup.find('meta', attrs={'name': 'description'}) else "",
            'keywords': soup.find('meta', attrs={'name': 'keywords'})['content'] if soup.find('meta', attrs={'name': 'keywords'}) else ""
        }
        
        return {
            'content': text_content,
            'links': links,
            'resources': resources,
            'metadata': metadata
        }
    
    def crawl_url(self, url, depth=0):
        """Crawl a single URL and extract content"""
        if depth > self.crawl_depth or url in self.visited_urls:
            return {}
        
        # Mark as visited
        self.visited_urls.add(url)
        
        # Check robots.txt
        if not self.is_allowed(url):
            logger.info(f"Skipping {url} (disallowed by robots.txt)")
            return {}
        
        # Add delay
        delay = get_random_delay(self.delay_min, self.delay_max)
        time.sleep(delay)
        
        try:
            # Make request
            headers = {'User-Agent': self.user_agent}
            response = requests.get(url, headers=headers, timeout=10)
            
            # Check if successful
            if response.status_code != 200:
                logger.warning(f"Failed to fetch {url}: HTTP {response.status_code}")
                return {}
            
            # Extract content
            data = self.extract_content(url, response.text)
            logger.info(f"Crawled {url} (depth={depth}): {len(data['content'])} chars, {len(data['links'])} links")
            
            return {url: data}
            
        except Exception as e:
            logger.error(f"Error crawling {url}: {e}")
            return {}
    
    def crawl(self, seed_url):
        """
        Crawl starting from seed URL up to specified depth.
        
        Args:
            seed_url (str): Starting URL for crawling
            
        Returns:
            dict: Dictionary of crawled data keyed by URL
        """
        logger.info(f"Starting crawl from {seed_url} with depth={self.crawl_depth}")
        
        # Reset visited URLs
        self.visited_urls = set()
        
        # Initialize results
        results = {}
        
        # Queue for BFS crawling
        queue = [(seed_url, 0)]  # (url, depth)
        
        while queue:
            url, depth = queue.pop(0)
            
            # Skip if already visited or too deep
            if url in self.visited_urls or depth > self.crawl_depth:
                continue
            
            # Crawl URL
            data = self.crawl_url(url, depth)
            results.update(data)
            
            # Add links to queue
            if url in data:
                for link in data[url]['links']:
                    if link not in self.visited_urls:
                        queue.append((link, depth + 1))
        
        logger.info(f"Crawl complete: {len(results)} pages crawled")
        return results
