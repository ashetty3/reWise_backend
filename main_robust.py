from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from pydantic import BaseModel
from typing import List, Optional
import httpx
import feedparser
import time
from urllib.parse import urlparse, quote
import logging
import re
from collections import defaultdict
import os

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Security settings
MAX_SEARCH_LENGTH = 100
MAX_FEED_URL_LENGTH = 500
RATE_LIMIT_WINDOW = 60
MAX_REQUESTS_PER_WINDOW = 30
ALLOWED_HOSTS = ["*"]

# Rate limiting storage
request_counts = defaultdict(list)

# Initialize FastAPI app
app = FastAPI(
    title="ReWise Backend - Robust",
    description="FastAPI backend for podcast search and episode retrieval with robust RSS parsing",
    version="2.0.0"
)

# Security middleware
app.add_middleware(TrustedHostMiddleware, allowed_hosts=ALLOWED_HOSTS)

# Enable CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["GET"],
    allow_headers=["*"],
)

# Pydantic models
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

class EpisodesResponse(BaseModel):
    podcast: PodcastInfo
    episodes: List[Episode]
    count: int
    feedUrl: str
    cached: bool
    cacheTimestamp: Optional[int] = None
    parsingIssues: Optional[List[str]] = None

# In-memory cache
feed_cache = {}
CACHE_DURATION = 10 * 60  # 10 minutes

def is_cache_valid(cache_entry):
    """Check if cache entry is still valid"""
    if not cache_entry:
        return False
    return (time.time() - cache_entry['timestamp']) < CACHE_DURATION

def validate_url(url: str) -> bool:
    """Validate if the provided string is a valid URL"""
    try:
        result = urlparse(url)
        if result.scheme not in ['http', 'https']:
            return False
        if not result.netloc or len(result.netloc) > 253:
            return False
        if not re.match(r'^[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$', result.netloc):
            return False
        return True
    except:
        return False

def sanitize_input(text: str, max_length: int = 100) -> str:
    """Sanitize user input"""
    if not text:
        return ""
    sanitized = re.sub(r'[<>"\']', '', str(text).strip())
    return sanitized[:max_length]

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
    """Safely get integer attribute"""
    try:
        value = safe_get(obj, attr, default)
        if value is not None:
            return int(str(value))
        return default
    except (ValueError, TypeError):
        return default

def safe_get_bool(obj, attr, default=None):
    """Safely get boolean attribute"""
    try:
        value = safe_get(obj, attr, default)
        if value is not None:
            return str(value).lower() in ['yes', 'true', '1']
        return default
    except Exception:
        return default

def check_rate_limit(client_ip: str) -> bool:
    """Check if client has exceeded rate limit"""
    current_time = time.time()
    request_counts[client_ip] = [
        req_time for req_time in request_counts[client_ip] 
        if current_time - req_time < RATE_LIMIT_WINDOW
    ]
    if len(request_counts[client_ip]) >= MAX_REQUESTS_PER_WINDOW:
        return False
    request_counts[client_ip].append(current_time)
    return True

def get_client_ip(request: Request) -> str:
    """Get client IP address"""
    forwarded_for = request.headers.get("X-Forwarded-For")
    if forwarded_for:
        return forwarded_for.split(",")[0].strip()
    return request.client.host if request.client else "unknown"

@app.get("/")
async def root():
    """Root endpoint"""
    return {"message": "ReWise FastAPI backend is running (Robust Version)"}

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "OK", "message": "Server is running"}

@app.get("/episodes", response_model=EpisodesResponse)
async def get_episodes(
    request: Request,
    feedUrl: str = Query(..., description="RSS feed URL", max_length=MAX_FEED_URL_LENGTH)
):
    """
    Get episodes from a podcast RSS feed with robust error handling
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
            cacheTimestamp=cached_data['timestamp'],
            parsingIssues=cached_data.get('parsingIssues')
        )
    
    try:
        # Fetch and parse RSS feed with robust error handling
        logger.info(f"Fetching fresh episodes for feed")
        
        # Use feedparser with more lenient parsing
        feed = feedparser.parse(feedUrl)
        
        # Handle parsing errors gracefully
        parsing_issues = []
        if hasattr(feed, 'bozo') and feed.bozo:
            error_msg = str(feed.bozo_exception) if hasattr(feed, 'bozo_exception') else 'Unknown parsing error'
            logger.warning(f"RSS feed has parsing issues: {error_msg}")
            parsing_issues.append(f"Feed parsing warnings: {error_msg}")
        
        # Try to extract basic feed information even with parsing issues
        if not hasattr(feed, 'feed') or not feed.feed:
            raise HTTPException(status_code=400, detail="Invalid RSS feed structure")
        
        # Check for entries - be more flexible
        entries = getattr(feed, 'entries', [])
        if not entries:
            # Try alternative parsing if no entries found
            logger.info("No entries found, attempting alternative parsing...")
            if hasattr(feed, 'items'):
                entries = feed.items
            elif hasattr(feed, 'channel') and hasattr(feed.channel, 'items'):
                entries = feed.channel.items
            
            if not entries:
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
        for entry in entries[:20]:  # Limit to 20 episodes
            try:
                # Extract audio URL from enclosures
                audio_url = None
                if hasattr(entry, 'enclosures') and entry.enclosures:
                    for enclosure in entry.enclosures:
                        enclosure_type = safe_get(enclosure, 'type', '')
                        if isinstance(enclosure_type, str) and enclosure_type.startswith('audio/'):
                            audio_url = safe_get(enclosure, 'href')
                            if audio_url and validate_url(audio_url):
                                break
                            else:
                                audio_url = None
                
                # Extract and sanitize description
                description = ""
                if hasattr(entry, 'content') and entry.content and len(entry.content) > 0:
                    content_value = safe_get(entry.content[0], 'value', '') if entry.content[0] else ''
                    description = sanitize_input(content_value, 1000)
                elif hasattr(entry, 'summary'):
                    description = sanitize_input(safe_get(entry, 'summary', ''), 1000)
                elif hasattr(entry, 'description'):
                    description = sanitize_input(safe_get(entry, 'description', ''), 1000)
                
                # Extract duration
                duration = safe_get(entry, 'itunes_duration')
                
                # Extract episode link
                episode_link = safe_get(entry, 'link')
                if episode_link and not validate_url(episode_link):
                    episode_link = None
                
                # Extract episode image
                episode_image = None
                if hasattr(entry, 'media_content') and entry.media_content:
                    for media in entry.media_content:
                        if safe_get(media, 'medium') == 'image':
                            episode_image = safe_get(media, 'url')
                            if validate_url(episode_image):
                                break
                            else:
                                episode_image = None
                
                # Fallback to podcast artwork
                if not episode_image:
                    episode_image = podcast_artwork
                
                # Extract enhanced metadata
                episode_number = safe_get_int(entry, 'itunes_episode')
                season = safe_get_int(entry, 'itunes_season')
                explicit = safe_get_bool(entry, 'itunes_explicit')
                language = safe_get(entry, 'language')
                
                # Extract file size and format
                file_size = None
                audio_format = None
                if hasattr(entry, 'enclosures') and entry.enclosures:
                    for enclosure in entry.enclosures:
                        if safe_get(enclosure, 'type', '').startswith('audio/'):
                            file_size = safe_get(enclosure, 'length')
                            audio_format = safe_get(enclosure, 'type')
                            break
                
                # Extract transcript and show notes URLs
                transcript_url = None
                show_notes_url = None
                if hasattr(entry, 'links'):
                    for link in entry.links:
                        if safe_get(link, 'rel') == 'transcript':
                            transcript_url = safe_get(link, 'href')
                        elif safe_get(link, 'rel') == 'show-notes':
                            show_notes_url = safe_get(link, 'href')
                
                # Extract categories and keywords
                categories = []
                if hasattr(entry, 'tags'):
                    for tag in entry.tags:
                        term = safe_get(tag, 'term')
                        if term:
                            categories.append(term)
                
                keywords = []
                keywords_str = safe_get(entry, 'itunes_keywords')
                if keywords_str:
                    keywords = [kw.strip() for kw in keywords_str.split(',') if kw.strip()]
                
                # Extract guest hosts
                guest_hosts = []
                guest_host = safe_get(entry, 'itunes_author')
                if guest_host:
                    guest_hosts = [guest_host]
                
                # Extract content warnings
                content_warnings = []
                if safe_get_bool(entry, 'itunes_explicit'):
                    content_warnings.append('explicit')
                
                # Check if episode is live or rerun
                is_live = False
                is_rerun = False
                episode_type = safe_get(entry, 'itunes_episodetype', '').lower()
                if episode_type:
                    is_live = episode_type == 'full' and 'live' in safe_get(entry, 'title', '').lower()
                    is_rerun = episode_type == 'rerun'
                
                # Extract chapters
                chapters = []
                if hasattr(entry, 'psc_chapters'):
                    for chapter in entry.psc_chapters:
                        chapters.append({
                            'title': safe_get(chapter, 'title', ''),
                            'start': safe_get(chapter, 'start', ''),
                            'end': safe_get(chapter, 'end', '')
                        })
                
                # Extract related links from description
                related_links = []
                if description:
                    url_pattern = r'https?://[^\s<>"]+'
                    found_urls = re.findall(url_pattern, description)
                    related_links = [url for url in found_urls if validate_url(url)]
                
                episode = Episode(
                    title=sanitize_input(safe_get(entry, 'title', 'Untitled'), 200),
                    description=description or 'No description available',
                    pubDate=safe_get(entry, 'published') or safe_get(entry, 'updated'),
                    audioUrl=audio_url,
                    duration=duration,
                    episodeLink=episode_link,
                    image=episode_image if episode_image and validate_url(episode_image) else None,
                    # Enhanced UX metadata
                    episodeNumber=episode_number,
                    season=season,
                    explicit=explicit,
                    language=language,
                    fileSize=file_size,
                    audioQuality=audio_format,
                    format=audio_format,
                    hasTranscript=transcript_url is not None,
                    transcriptUrl=transcript_url if transcript_url and validate_url(transcript_url) else None,
                    showNotesUrl=show_notes_url if show_notes_url and validate_url(show_notes_url) else None,
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
                    
            except Exception as e:
                logger.warning(f"Error parsing episode: {str(e)}")
                parsing_issues.append(f"Episode parsing error: {str(e)}")
                continue
        
        # Cache the results
        cache_entry = {
            'podcast': podcast_info,
            'episodes': episodes,
            'timestamp': int(time.time()),
            'parsingIssues': parsing_issues if parsing_issues else None
        }
        feed_cache[cache_key] = cache_entry
        
        logger.info(f"Found {len(episodes)} episodes for feed")
        
        return EpisodesResponse(
            podcast=podcast_info,
            episodes=episodes,
            count=len(episodes),
            feedUrl=feedUrl,
            cached=False,
            cacheTimestamp=cache_entry['timestamp'],
            parsingIssues=parsing_issues if parsing_issues else None
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Episodes error: {str(e)}")
        raise HTTPException(status_code=500, detail="Error fetching episodes")

@app.get("/episodes/cache/clear")
async def clear_cache(request: Request):
    """Clear the RSS feed cache"""
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
    client_ip = get_client_ip(request)
    if not check_rate_limit(client_ip):
        raise HTTPException(status_code=429, detail="Rate limit exceeded. Please try again later.")
    
    cache_entries = []
    for url, data in feed_cache.items():
        if data:
            cache_entries.append({
                "url": url[:50] + "..." if len(url) > 50 else url,
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
    port = int(os.getenv("PORT", 8000))
    host = os.getenv("HOST", "0.0.0.0")
    uvicorn.run(app, host=host, port=port) 