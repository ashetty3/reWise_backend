const express = require('express');
const Parser = require('rss-parser');

const router = express.Router();

// In-memory cache for RSS feeds
const feedCache = new Map();
const CACHE_DURATION = 10 * 60 * 1000; // 10 minutes in milliseconds

// RSS parser instance
const parser = new Parser({
  timeout: 10000, // 10 second timeout
  headers: {
    'User-Agent': 'reWise-Backend/1.0.0'
  }
});

// Cache management function
function isCacheValid(cacheEntry) {
  return cacheEntry && (Date.now() - cacheEntry.timestamp) < CACHE_DURATION;
}

// GET /episodes?feedUrl=
router.get('/', async (req, res) => {
  try {
    const { feedUrl } = req.query;
    
    // Validate feed URL
    if (!feedUrl || feedUrl.trim() === '') {
      return res.status(400).json({ 
        error: 'Feed URL is required',
        message: 'Please provide a feed URL using ?feedUrl=your_rss_feed_url'
      });
    }

    // Validate URL format
    try {
      new URL(feedUrl);
    } catch (urlError) {
      return res.status(400).json({ 
        error: 'Invalid URL format',
        message: 'Please provide a valid RSS feed URL'
      });
    }

    console.log(`Episodes request received for feed: "${feedUrl}"`);

    // Check cache first
    const cacheKey = feedUrl;
    const cachedData = feedCache.get(cacheKey);
    
    if (isCacheValid(cachedData)) {
      console.log(`Returning cached episodes for feed: "${feedUrl}"`);
      return res.status(200).json({
        episodes: cachedData.episodes,
        count: cachedData.episodes.length,
        feedUrl: feedUrl,
        cached: true,
        cacheTimestamp: cachedData.timestamp
      });
    }

    // Fetch and parse RSS feed
    console.log(`Fetching fresh episodes for feed: "${feedUrl}"`);
    const feed = await parser.parseURL(feedUrl);

    // Validate feed structure
    if (!feed.items || !Array.isArray(feed.items)) {
      return res.status(400).json({ 
        error: 'Invalid RSS feed',
        message: 'The provided URL does not contain a valid RSS feed'
      });
    }

    // Parse and format episodes
    const episodes = feed.items
      .slice(0, 20) // Limit to 20 episodes
      .map(item => ({
        title: item.title || 'Untitled',
        description: item.contentSnippet || item.summary || item.description || 'No description available',
        pubDate: item.pubDate || item.isoDate || null,
        audioUrl: item.enclosure?.url || null
      }))
      .filter(episode => episode.audioUrl); // Only return episodes with audio URLs

    // Cache the results
    const cacheEntry = {
      episodes,
      timestamp: Date.now()
    };
    feedCache.set(cacheKey, cacheEntry);

    console.log(`Found ${episodes.length} episodes for feed: "${feedUrl}"`);

    res.status(200).json({
      episodes,
      count: episodes.length,
      feedUrl: feedUrl,
      cached: false,
      cacheTimestamp: cacheEntry.timestamp
    });

  } catch (error) {
    console.error('Episodes error:', error.message);
    
    if (error.code === 'ECONNABORTED') {
      return res.status(504).json({ 
        error: 'Request timeout',
        message: 'The RSS feed request timed out. Please try again.'
      });
    }
    
    if (error.code === 'ENOTFOUND') {
      return res.status(404).json({ 
        error: 'Feed not found',
        message: 'The RSS feed URL could not be found or is not accessible'
      });
    }
    
    if (error.message.includes('Invalid XML')) {
      return res.status(400).json({ 
        error: 'Invalid RSS feed',
        message: 'The provided URL does not contain a valid RSS feed format'
      });
    }
    
    res.status(500).json({ 
      error: 'Internal server error',
      message: 'An error occurred while fetching episodes'
    });
  }
});

// Optional: Cache management endpoint
router.get('/cache/clear', (req, res) => {
  const cacheSize = feedCache.size;
  feedCache.clear();
  console.log(`Cache cleared. Removed ${cacheSize} entries.`);
  res.status(200).json({ 
    message: 'Cache cleared successfully',
    clearedEntries: cacheSize
  });
});

// Optional: Cache status endpoint
router.get('/cache/status', (req, res) => {
  const cacheEntries = Array.from(feedCache.entries()).map(([url, data]) => ({
    url,
    episodeCount: data.episodes.length,
    timestamp: data.timestamp,
    isValid: isCacheValid(data)
  }));
  
  res.status(200).json({
    cacheSize: feedCache.size,
    entries: cacheEntries
  });
});

module.exports = router; 