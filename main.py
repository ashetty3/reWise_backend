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

class PodcastInfo(BaseModel):
    title: str
    description: str
    artwork: Optional[str] = None

class Episode(BaseModel):
    title: str
    description: str
    pubDate: Optional[str] = None
    audioUrl: Optional[str] = None
    duration: Optional[str] = None
    episodeLink: Optional[str] = None
    image: Optional[str] = None
    # Enhanced UX metadata
    episodeNumber: Optional[int] = None
    season: Optional[int] = None
    explicit: Optional[bool] = None
    language: Optional[str] = None
    fileSize: Optional[str] = None
    audioQuality: Optional[str] = None
    format: Optional[str] = None
    hasTranscript: Optional[bool] = None
    transcriptUrl: Optional[str] = None
    showNotesUrl: Optional[str] = None
    categories: Optional[List[str]] = None
    keywords: Optional[List[str]] = None
    guestHosts: Optional[List[str]] = None
    contentWarnings: Optional[List[str]] = None
    isLive: Optional[bool] = None
    isRerun: Optional[bool] = None
    chapters: Optional[List[dict]] = None
    relatedLinks: Optional[List[str]] = None

class SearchResponse(BaseModel):
    podcasts: List[Podcast]
    count: int
    searchTerm: str

class EpisodesResponse(BaseModel):
    podcast: PodcastInfo
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

def safe_get(obj, attr, default=None):
    """Safely get attribute from feedparser object"""
    try:
        if hasattr(obj, attr):
            value = getattr(obj, attr)
            # Handle feedparser's complex object types
            if hasattr(value, 'href'):
                return value.href
            elif hasattr(value, 'term'):
                return value.term
            elif hasattr(value, 'value'):
                return value.value
            elif isinstance(value, (list, tuple)) and len(value) > 0:
                # Handle lists of objects
                if hasattr(value[0], 'href'):
                    return value[0].href
                elif hasattr(value[0], 'term'):
                    return value[0].term
                else:
                    return str(value[0]) if value[0] else default
            else:
                return str(value) if value else default
        return default
    except Exception:
        return default

def safe_get_int(obj, attr, default=None):
    """Safely get integer attribute from feedparser object"""
    try:
        value = safe_get(obj, attr, default)
        if value is not None:
            return int(str(value))
        return default
    except (ValueError, TypeError):
        return default

def safe_get_bool(obj, attr, default=None):
    """Safely get boolean attribute from feedparser object"""
    try:
        value = safe_get(obj, attr, default)
        if value is not None:
            return str(value).lower() in ['yes', 'true', '1']
        return default
    except Exception:
        return default

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
        Podcast metadata and list of episodes with their details
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
    
    if cached_data and is_cache_valid(cached_data):
        logger.info(f"Returning cached episodes for feed")
        return EpisodesResponse(
            podcast=cached_data['podcast'],
            episodes=cached_data['episodes'],
            count=len(cached_data['episodes']),
            feedUrl=feedUrl,
            cached=True,
            cacheTimestamp=cached_data['timestamp']
        )
    
    try:
        # Fetch and parse RSS feed with robust error handling
        logger.info(f"Fetching fresh episodes for feed")
        
        # Use feedparser with more lenient parsing
        feed = feedparser.parse(feedUrl)
        
        # Validate feed structure
        if not hasattr(feed, 'feed') or not feed.feed:
            raise HTTPException(status_code=400, detail="Invalid RSS feed structure")
        
        # Validate feed structure
        if not hasattr(feed, 'entries') or not feed.entries:
            raise HTTPException(status_code=400, detail="No episodes found in RSS feed")
        
        # Extract podcast-level metadata using safe extraction
        podcast_title = safe_get(feed.feed, 'title', 'Unknown Podcast')
        podcast_description = safe_get(feed.feed, 'description', 'No description available')
        podcast_artwork = safe_get(feed.feed, 'image') or safe_get(feed.feed, 'itunes_image')
        
        # Create podcast info
        podcast_info = PodcastInfo(
            title=sanitize_input(podcast_title, 200),
            description=sanitize_input(podcast_description, 1000),
            artwork=podcast_artwork if podcast_artwork and validate_url(podcast_artwork) else None
        )
        
        # Parse and format episodes
        episodes = []
        for entry in feed.entries[:20]:  # Limit to 20 episodes
            # Extract audio URL from enclosures
            audio_url = None
            if hasattr(entry, 'enclosures') and entry.enclosures:
                for enclosure in entry.enclosures:
                    enclosure_type = getattr(enclosure, 'type', '')
                    if isinstance(enclosure_type, str) and enclosure_type.startswith('audio/'):
                        audio_url = getattr(enclosure, 'href', None)
                        # Validate audio URL
                        if audio_url and validate_url(audio_url):
                            break
                        else:
                            audio_url = None
            
            # Extract and sanitize description (prefer full description)
            description = ""
            if hasattr(entry, 'content') and entry.content and len(entry.content) > 0:
                content_value = getattr(entry.content[0], 'value', '') if entry.content[0] else ''
                description = sanitize_input(str(content_value), 1000)
            elif hasattr(entry, 'summary'):
                description = sanitize_input(str(getattr(entry, 'summary', '')), 1000)
            elif hasattr(entry, 'description'):
                description = sanitize_input(str(getattr(entry, 'description', '')), 1000)
            
            # Extract duration from iTunes tags
            duration = None
            if hasattr(entry, 'itunes_duration'):
                duration = getattr(entry, 'itunes_duration', None)
            
            # Extract episode link
            episode_link = None
            if hasattr(entry, 'link'):
                episode_link = getattr(entry, 'link', None)
                if episode_link and not validate_url(str(episode_link)):
                    episode_link = None
            
            # Extract episode image (prefer episode-level, fallback to podcast-level)
            episode_image = None
            if hasattr(entry, 'media_content') and entry.media_content:
                for media in entry.media_content:
                    if media.get('medium') == 'image':
                        episode_image = media.get('url')
                        if episode_image and validate_url(str(episode_image)):
                            break
                        else:
                            episode_image = None
            
            # Fallback to podcast artwork if no episode image
            if not episode_image:
                episode_image = podcast_artwork
            
            # Extract enhanced metadata for better UX
            episode_number = safe_get_int(entry, 'itunes_episode')
            season = safe_get_int(entry, 'itunes_season')
            explicit = safe_get_bool(entry, 'itunes_explicit')
            language = safe_get(entry, 'language')
            
            # Extract file size and format from enclosures
            file_size = None
            audio_format = None
            if hasattr(entry, 'enclosures') and entry.enclosures:
                for enclosure in entry.enclosures:
                    enclosure_type = safe_get(enclosure, 'type', '')
                    if enclosure_type and str(enclosure_type).startswith('audio/'):
                        file_size = safe_get(enclosure, 'length')
                        audio_format = safe_get(enclosure, 'type')
                        break
            
            # Extract transcript and show notes URLs
            transcript_url = None
            show_notes_url = None
            if hasattr(entry, 'links'):
                for link in entry.links:
                    link_rel = safe_get(link, 'rel')
                    if link_rel == 'transcript':
                        transcript_url = safe_get(link, 'href')
                    elif link_rel == 'show-notes':
                        show_notes_url = safe_get(link, 'href')
            
            # Extract categories and keywords
            categories = []
            if hasattr(entry, 'tags'):
                categories = [safe_get(tag, 'term') for tag in entry.tags if safe_get(tag, 'term')]
            
            keywords = []
            itunes_keywords = safe_get(entry, 'itunes_keywords')
            if itunes_keywords:
                keywords = [kw.strip() for kw in str(itunes_keywords).split(',') if kw.strip()]
            
            # Extract guest hosts
            guest_hosts = []
            itunes_author = safe_get(entry, 'itunes_author')
            if itunes_author:
                guest_hosts = [str(itunes_author)]
            
            # Extract content warnings
            content_warnings = []
            if safe_get_bool(entry, 'itunes_explicit'):
                content_warnings.append('explicit')
            
            # Check if episode is live or rerun
            is_live = False
            is_rerun = False
            episode_type = safe_get(entry, 'itunes_episodetype')
            if episode_type:
                episode_type_str = str(episode_type).lower()
                title_str = str(safe_get(entry, 'title', '')).lower()
                is_live = episode_type_str == 'full' and 'live' in title_str
                is_rerun = episode_type_str == 'rerun'
            
            # Extract chapters if available
            chapters = []
            if hasattr(entry, 'psc_chapters'):
                for chapter in entry.psc_chapters:
                    chapters.append({
                        'title': chapter.get('title', ''),
                        'start': chapter.get('start', ''),
                        'end': chapter.get('end', '')
                    })
            
            # Extract related links from description
            related_links = []
            if description:
                # Simple regex to find URLs in description
                url_pattern = r'https?://[^\s<>"]+'
                found_urls = re.findall(url_pattern, description)
                related_links = [url for url in found_urls if validate_url(url)]
            
            episode = Episode(
                title=sanitize_input(str(safe_get(entry, 'title', 'Untitled')), 200),
                description=description or 'No description available',
                pubDate=str(safe_get(entry, 'published') or safe_get(entry, 'updated', '')),
                audioUrl=audio_url,
                duration=duration,
                episodeLink=episode_link,
                image=str(episode_image) if episode_image and validate_url(str(episode_image)) else None,
                # Enhanced UX metadata
                episodeNumber=episode_number,
                season=season,
                explicit=explicit,
                language=str(language) if language else None,
                fileSize=str(file_size) if file_size else None,
                audioQuality=str(audio_format) if audio_format else None,
                format=str(audio_format) if audio_format else None,
                hasTranscript=transcript_url is not None,
                transcriptUrl=str(transcript_url) if transcript_url and validate_url(str(transcript_url)) else None,
                showNotesUrl=str(show_notes_url) if show_notes_url and validate_url(str(show_notes_url)) else None,
                categories=categories if categories else None,
                keywords=keywords if keywords else None,
                guestHosts=guest_hosts if guest_hosts else None,
                contentWarnings=content_warnings if content_warnings else None,
                isLive=is_live,
                isRerun=is_rerun,
                chapters=chapters if chapters else None,
                relatedLinks=related_links if related_links else None
            )
            
            # Only include episodes with valid audio URLs
            if episode.audioUrl:
                episodes.append(episode)
        
        # Cache the results
        cache_entry = {
            'podcast': podcast_info,
            'episodes': episodes,
            'timestamp': int(time.time())
        }
        feed_cache[cache_key] = cache_entry
        
        logger.info(f"Found {len(episodes)} episodes for feed")
        
        return EpisodesResponse(
            podcast=podcast_info,
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
        if data:  # Check if data exists
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