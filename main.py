from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from pydantic import BaseModel, HttpUrl, validator
from typing import List, Optional
import httpx
import feedparser
from datetime import datetime
import time
from urllib.parse import urlparse, quote
import logging
import re
from collections import defaultdict
import os

# Configure logging - don't log sensitive information
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Security settings
MAX_SEARCH_LENGTH = 100
MAX_FEED_URL_LENGTH = 500
RATE_LIMIT_WINDOW = 60  # 1 minute
MAX_REQUESTS_PER_WINDOW = 30  # 30 requests per minute
ALLOWED_HOSTS = ["*"]  # Configure this for production

# Rate limiting storage
request_counts = defaultdict(list)

# Initialize FastAPI app
app = FastAPI(
    title="ReWise Backend",
    description="FastAPI backend for podcast search and episode retrieval",
    version="1.0.0"
)

# Security middleware
app.add_middleware(
    TrustedHostMiddleware, 
    allowed_hosts=ALLOWED_HOSTS
)

# Enable CORS for all origins (configure this for production)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure specific origins for production
    allow_credentials=True,
    allow_methods=["GET"],  # Only allow GET requests
    allow_headers=["*"],
)

# Pydantic models with validation
class Podcast(BaseModel):
    podcastName: str
    feedUrl: Optional[str] = None
    artwork: Optional[str] = None
    artistName: str

class Episode(BaseModel):
    title: str
    description: str
    pubDate: Optional[str] = None
    audioUrl: Optional[str] = None

class SearchResponse(BaseModel):
    podcasts: List[Podcast]
    count: int
    searchTerm: str

class EpisodesResponse(BaseModel):
    episodes: List[Episode]
    count: int
    feedUrl: str
    cached: bool
    cacheTimestamp: Optional[int] = None

# In-memory cache for RSS feeds
feed_cache = {}
CACHE_DURATION = 10 * 60  # 10 minutes in seconds

def is_cache_valid(cache_entry):
    """Check if cache entry is still valid"""
    if not cache_entry:
        return False
    return (time.time() - cache_entry['timestamp']) < CACHE_DURATION

def validate_url(url: str) -> bool:
    """Validate if the provided string is a valid URL"""
    try:
        result = urlparse(url)
        # Only allow HTTP and HTTPS
        if result.scheme not in ['http', 'https']:
            return False
        # Check for valid domain
        if not result.netloc or len(result.netloc) > 253:
            return False
        # Basic domain validation
        if not re.match(r'^[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$', result.netloc):
            return False
        return True
    except:
        return False

def sanitize_input(text: str, max_length: int = 100) -> str:
    """Sanitize user input"""
    if not text:
        return ""
    # Remove potentially dangerous characters
    sanitized = re.sub(r'[<>"\']', '', text.strip())
    # Limit length
    return sanitized[:max_length]

def check_rate_limit(client_ip: str) -> bool:
    """Check if client has exceeded rate limit"""
    current_time = time.time()
    # Remove old requests outside the window
    request_counts[client_ip] = [
        req_time for req_time in request_counts[client_ip] 
        if current_time - req_time < RATE_LIMIT_WINDOW
    ]
    # Check if limit exceeded
    if len(request_counts[client_ip]) >= MAX_REQUESTS_PER_WINDOW:
        return False
    # Add current request
    request_counts[client_ip].append(current_time)
    return True

def get_client_ip(request: Request) -> str:
    """Get client IP address"""
    # Check for forwarded headers (common in production)
    forwarded_for = request.headers.get("X-Forwarded-For")
    if forwarded_for:
        return forwarded_for.split(",")[0].strip()
    return request.client.host if request.client else "unknown"

@app.get("/")
async def root():
    """Root endpoint"""
    return {"message": "ReWise FastAPI backend is running"}

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "OK", "message": "Server is running"}

@app.get("/search", response_model=SearchResponse)
async def search_podcasts(
    request: Request,
    term: str = Query(..., description="Search term for podcasts", max_length=MAX_SEARCH_LENGTH)
):
    """
    Search for podcasts using iTunes Search API
    
    Args:
        term: Search term for finding podcasts
        
    Returns:
        List of podcasts with their details
    """
    # Rate limiting
    client_ip = get_client_ip(request)
    if not check_rate_limit(client_ip):
        raise HTTPException(status_code=429, detail="Rate limit exceeded. Please try again later.")
    
    # Input validation and sanitization
    if not term or term.strip() == "":
        raise HTTPException(status_code=400, detail="Search term is required")
    
    # Sanitize search term
    sanitized_term = sanitize_input(term, MAX_SEARCH_LENGTH)
    if not sanitized_term:
        raise HTTPException(status_code=400, detail="Invalid search term")
    
    logger.info(f"Search request received for term: '{sanitized_term[:20]}...' from IP: {client_ip}")
    
    try:
        # URL encode the search term to prevent injection
        encoded_term = quote(sanitized_term)
        itunes_url = f"https://itunes.apple.com/search?term={encoded_term}&entity=podcast"
        
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(
                itunes_url,
                headers={"User-Agent": "ReWise-Backend/1.0.0"}
            )
            response.raise_for_status()
            data = response.json()
        
        # Check if iTunes API returned results
        if not data.get('results') or not isinstance(data['results'], list):
            return SearchResponse(
                podcasts=[],
                count=0,
                searchTerm=sanitized_term
            )
        
        # Parse and format the response
        podcasts = []
        for podcast in data['results']:
            # Validate feed URL before including
            feed_url = podcast.get('feedUrl')
            if feed_url and validate_url(feed_url):
                podcast_data = Podcast(
                    podcastName=sanitize_input(podcast.get('collectionName', 'Unknown'), 200),
                    feedUrl=feed_url,
                    artwork=podcast.get('artworkUrl600') or podcast.get('artworkUrl100'),
                    artistName=sanitize_input(podcast.get('artistName', 'Unknown'), 200)
                )
                podcasts.append(podcast_data)
        
        logger.info(f"Found {len(podcasts)} podcasts for term: '{sanitized_term[:20]}...'")
        
        return SearchResponse(
            podcasts=podcasts,
            count=len(podcasts),
            searchTerm=sanitized_term
        )
        
    except httpx.TimeoutException:
        logger.error(f"Timeout error for search term: '{sanitized_term[:20]}...'")
        raise HTTPException(status_code=504, detail="Request timeout")
    except httpx.HTTPStatusError as e:
        logger.error(f"iTunes API error: {e.response.status_code}")
        raise HTTPException(status_code=502, detail="iTunes API error")
    except Exception as e:
        logger.error(f"Search error: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")

@app.get("/episodes", response_model=EpisodesResponse)
async def get_episodes(
    request: Request,
    feedUrl: str = Query(..., description="RSS feed URL", max_length=MAX_FEED_URL_LENGTH)
):
    """
    Get episodes from a podcast RSS feed
    
    Args:
        feedUrl: The RSS feed URL of the podcast
        
    Returns:
        List of episodes with their details
    """
    # Rate limiting
    client_ip = get_client_ip(request)
    if not check_rate_limit(client_ip):
        raise HTTPException(status_code=429, detail="Rate limit exceeded. Please try again later.")
    
    # Input validation
    if not feedUrl or feedUrl.strip() == "":
        raise HTTPException(status_code=400, detail="Feed URL is required")
    
    if not validate_url(feedUrl):
        raise HTTPException(status_code=400, detail="Invalid URL format")
    
    logger.info(f"Episodes request received for feed from IP: {client_ip}")
    
    # Check cache first
    cache_key = feedUrl
    cached_data = feed_cache.get(cache_key)
    
    if is_cache_valid(cached_data):
        logger.info(f"Returning cached episodes for feed")
        return EpisodesResponse(
            episodes=cached_data['episodes'],
            count=len(cached_data['episodes']),
            feedUrl=feedUrl,
            cached=True,
            cacheTimestamp=cached_data['timestamp']
        )
    
    try:
        # Fetch and parse RSS feed
        logger.info(f"Fetching fresh episodes for feed")
        
        # Use feedparser to parse the RSS feed
        feed = feedparser.parse(feedUrl)
        
        # Check for parsing errors
        if hasattr(feed, 'bozo') and feed.bozo:
            raise HTTPException(status_code=400, detail="Invalid RSS feed format")
        
        # Validate feed structure
        if not hasattr(feed, 'entries') or not feed.entries:
            raise HTTPException(status_code=400, detail="No episodes found in RSS feed")
        
        # Parse and format episodes
        episodes = []
        for entry in feed.entries[:20]:  # Limit to 20 episodes
            # Extract audio URL from enclosures
            audio_url = None
            if hasattr(entry, 'enclosures') and entry.enclosures:
                for enclosure in entry.enclosures:
                    if enclosure.get('type', '').startswith('audio/'):
                        audio_url = enclosure.get('href')
                        # Validate audio URL
                        if audio_url and validate_url(audio_url):
                            break
                        else:
                            audio_url = None
            
            # Extract and sanitize description
            description = ""
            if hasattr(entry, 'summary'):
                description = sanitize_input(entry.summary, 1000)
            elif hasattr(entry, 'description'):
                description = sanitize_input(entry.description, 1000)
            elif hasattr(entry, 'content') and entry.content and len(entry.content) > 0:
                content_value = entry.content[0].get('value', '') if entry.content[0] else ''
                description = sanitize_input(content_value, 1000)
            
            episode = Episode(
                title=sanitize_input(entry.get('title', 'Untitled'), 200),
                description=description or 'No description available',
                pubDate=entry.get('published') or entry.get('updated'),
                audioUrl=audio_url
            )
            
            # Only include episodes with valid audio URLs
            if episode.audioUrl:
                episodes.append(episode)
        
        # Cache the results
        cache_entry = {
            'episodes': episodes,
            'timestamp': int(time.time())
        }
        feed_cache[cache_key] = cache_entry
        
        logger.info(f"Found {len(episodes)} episodes for feed")
        
        return EpisodesResponse(
            episodes=episodes,
            count=len(episodes),
            feedUrl=feedUrl,
            cached=False,
            cacheTimestamp=cache_entry['timestamp']
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Episodes error: {str(e)}")
        raise HTTPException(status_code=500, detail="Error fetching episodes")

@app.get("/episodes/cache/clear")
async def clear_cache(request: Request):
    """Clear the RSS feed cache"""
    # Rate limiting
    client_ip = get_client_ip(request)
    if not check_rate_limit(client_ip):
        raise HTTPException(status_code=429, detail="Rate limit exceeded. Please try again later.")
    
    cache_size = len(feed_cache)
    feed_cache.clear()
    logger.info(f"Cache cleared. Removed {cache_size} entries by IP: {client_ip}")
    return {"message": "Cache cleared successfully", "clearedEntries": cache_size}

@app.get("/episodes/cache/status")
async def cache_status(request: Request):
    """Get cache status"""
    # Rate limiting
    client_ip = get_client_ip(request)
    if not check_rate_limit(client_ip):
        raise HTTPException(status_code=429, detail="Rate limit exceeded. Please try again later.")
    
    cache_entries = []
    for url, data in feed_cache.items():
        cache_entries.append({
            "url": url[:50] + "..." if len(url) > 50 else url,  # Truncate long URLs
            "episodeCount": len(data['episodes']),
            "timestamp": data['timestamp'],
            "isValid": is_cache_valid(data)
        })
    
    return {
        "cacheSize": len(feed_cache),
        "entries": cache_entries
    }

if __name__ == "__main__":
    import uvicorn
    # Use environment variables for production
    port = int(os.getenv("PORT", 8000))
    host = os.getenv("HOST", "0.0.0.0")
    uvicorn.run(app, host=host, port=port) 