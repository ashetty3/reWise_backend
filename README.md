# ReWise Backend - FastAPI

A FastAPI backend that provides podcast search and episode retrieval functionality using the iTunes Podcast Search API and RSS feed parsing.

## Features

- **Podcast Search**: Search for podcasts using the iTunes Podcast Search API
- **Episode Retrieval**: Parse RSS feeds to get podcast episodes
- **Caching**: In-memory caching for RSS feeds (10-minute TTL)
- **CORS Enabled**: Ready for frontend integration
- **Comprehensive Logging**: All requests are logged
- **Error Handling**: Robust error handling with appropriate HTTP status codes
- **Auto-generated API Documentation**: Interactive docs with Swagger UI

## Installation

1. Clone the repository
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

## Running the Server

### Development Mode
```bash
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

### Production Mode
```bash
uvicorn main:app --host 0.0.0.0 --port 8000
```

### Using Python directly
```bash
python main.py
```

The server will start on port 8000 by default.

## API Endpoints

### 1. Root Endpoint
**GET** `/`

Returns a simple message indicating the server is running.

**Response:**
```json
{
  "message": "ReWise FastAPI backend is running"
}
```

### 2. Health Check
**GET** `/health`

Returns server status.

**Response:**
```json
{
  "status": "OK",
  "message": "Server is running"
}
```

### 3. Search Podcasts
**GET** `/search?term=<search_term>`

Searches for podcasts using the iTunes Podcast Search API.

**Parameters:**
- `term` (required): The search term for finding podcasts

**Response:**
```json
{
  "podcasts": [
    {
      "podcastName": "Podcast Name",
      "feedUrl": "https://example.com/feed.xml",
      "artwork": "https://example.com/artwork.jpg",
      "artistName": "Artist Name"
    }
  ],
  "count": 1,
  "searchTerm": "your search term"
}
```

**Example:**
```bash
curl "http://localhost:8000/search?term=tech"
```

### 4. Get Episodes
**GET** `/episodes?feedUrl=<rss_feed_url>`

Retrieves episodes from a podcast RSS feed.

**Parameters:**
- `feedUrl` (required): The RSS feed URL of the podcast

**Response:**
```json
{
  "episodes": [
    {
      "title": "Episode Title",
      "description": "Episode description or summary",
      "pubDate": "2023-12-01T10:00:00Z",
      "audioUrl": "https://example.com/episode.mp3"
    }
  ],
  "count": 1,
  "feedUrl": "https://example.com/feed.xml",
  "cached": false,
  "cacheTimestamp": 1701432000
}
```

**Example:**
```bash
curl "http://localhost:8000/episodes?feedUrl=https://feeds.example.com/podcast.xml"
```

### 5. Cache Management (Optional)

**Clear Cache:**
```bash
curl "http://localhost:8000/episodes/cache/clear"
```

**Check Cache Status:**
```bash
curl "http://localhost:8000/episodes/cache/status"
```

## Interactive API Documentation

FastAPI automatically generates interactive API documentation:

- **Swagger UI**: `http://localhost:8000/docs`
- **ReDoc**: `http://localhost:8000/redoc`

## Error Handling

The API returns appropriate HTTP status codes and error messages:

- `400`: Bad Request (missing or invalid parameters)
- `404`: Not Found (RSS feed not accessible)
- `500`: Internal Server Error
- `502`: Bad Gateway (iTunes API error)
- `504`: Gateway Timeout (request timeout)

## Caching

- RSS feeds are cached in memory for 10 minutes
- Cache is automatically invalidated after the TTL expires
- Cache can be manually cleared using the cache management endpoints
- Cache status can be monitored using the status endpoint

## CORS

CORS is enabled for all origins, making it ready for frontend integration.

## Logging

All incoming requests are logged using Python's logging module.

## Dependencies

- `fastapi`: Web framework
- `uvicorn`: ASGI server
- `feedparser`: RSS feed parsing
- `httpx`: HTTP client for API calls
- `pydantic`: Data validation
- `python-multipart`: Form data parsing

## Project Structure

```
reWise_backend/
├── main.py           # Main FastAPI application
├── requirements.txt  # Python dependencies
├── README.md        # This file
└── .gitignore       # Git ignore file
```

## Development

To run in development mode with auto-reload:
```bash
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

## Testing the API

You can test the endpoints using curl, Postman, or any HTTP client:

1. **Check if server is running:**
   ```bash
   curl "http://localhost:8000/"
   ```

2. **Search for podcasts:**
   ```bash
   curl "http://localhost:8000/search?term=javascript"
   ```

3. **Get episodes from a feed:**
   ```bash
   curl "http://localhost:8000/episodes?feedUrl=https://feeds.buzzsprout.com/123456.rss"
   ```

4. **Check server health:**
   ```bash
   curl "http://localhost:8000/health"
   ```

## Deployment

### Render Deployment

This project is ready for deployment on Render. The `requirements.txt` file contains all necessary dependencies.

### Environment Variables

- `PORT`: Server port (default: 8000)
- `HOST`: Server host (default: 0.0.0.0)

## Notes

- The search endpoint filters out podcasts without valid feed URLs
- The episodes endpoint limits results to 20 episodes maximum
- All external API calls have 10-second timeouts
- The server includes proper error handling for network issues and invalid responses
- FastAPI provides automatic request/response validation using Pydantic models 