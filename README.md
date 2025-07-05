# reWise Backend

An Express.js backend that provides podcast search and episode retrieval functionality using the iTunes Podcast Search API and RSS feed parsing.

## Features

- **Podcast Search**: Search for podcasts using the iTunes Podcast Search API
- **Episode Retrieval**: Parse RSS feeds to get podcast episodes
- **Caching**: In-memory caching for RSS feeds (10-minute TTL)
- **CORS Enabled**: Ready for frontend integration
- **Comprehensive Logging**: All requests are logged
- **Error Handling**: Robust error handling with appropriate HTTP status codes

## Installation

1. Clone the repository
2. Install dependencies:
   ```bash
   npm install
   ```

## Running the Server

### Development Mode
```bash
npm run dev
```

### Production Mode
```bash
npm start
```

The server will start on port 3000 by default. You can change this by setting the `PORT` environment variable.

## API Endpoints

### 1. Search Podcasts
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
curl "http://localhost:3000/search?term=tech"
```

### 2. Get Episodes
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
  "cacheTimestamp": 1701432000000
}
```

**Example:**
```bash
curl "http://localhost:3000/episodes?feedUrl=https://feeds.example.com/podcast.xml"
```

### 3. Health Check
**GET** `/health`

Returns server status.

**Response:**
```json
{
  "status": "OK",
  "message": "Server is running"
}
```

### 4. Cache Management (Optional)

**Clear Cache:**
```bash
curl "http://localhost:3000/episodes/cache/clear"
```

**Check Cache Status:**
```bash
curl "http://localhost:3000/episodes/cache/status"
```

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

All incoming requests are logged using Morgan middleware in combined format.

## Dependencies

- `express`: Web framework
- `cors`: CORS middleware
- `rss-parser`: RSS feed parsing
- `axios`: HTTP client for API calls
- `morgan`: HTTP request logging
- `nodemon`: Development server (dev dependency)

## Project Structure

```
reWise_backend/
├── server.js          # Main server file
├── routes/
│   ├── search.js      # Podcast search endpoint
│   └── episodes.js    # Episode retrieval endpoint
├── package.json       # Dependencies and scripts
└── README.md         # This file
```

## Development

To run in development mode with auto-restart:
```bash
npm run dev
```

## Testing the API

You can test the endpoints using curl, Postman, or any HTTP client:

1. **Search for podcasts:**
   ```bash
   curl "http://localhost:3000/search?term=javascript"
   ```

2. **Get episodes from a feed:**
   ```bash
   curl "http://localhost:3000/episodes?feedUrl=https://feeds.buzzsprout.com/123456.rss"
   ```

3. **Check server health:**
   ```bash
   curl "http://localhost:3000/health"
   ```

## Notes

- The search endpoint filters out podcasts without valid feed URLs
- The episodes endpoint limits results to 20 episodes maximum
- All external API calls have 10-second timeouts
- The server includes proper error handling for network issues and invalid responses 