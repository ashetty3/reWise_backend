const express = require('express');
const axios = require('axios');

const router = express.Router();

// GET /search?term=
router.get('/', async (req, res) => {
  try {
    const { term } = req.query;
    
    // Validate search term
    if (!term || term.trim() === '') {
      return res.status(400).json({ 
        error: 'Search term is required',
        message: 'Please provide a search term using ?term=your_search_term'
      });
    }

    console.log(`Search request received for term: "${term}"`);

    // Call iTunes Podcast Search API
    const itunesUrl = `https://itunes.apple.com/search?term=${encodeURIComponent(term)}&entity=podcast`;
    
    const response = await axios.get(itunesUrl, {
      timeout: 10000, // 10 second timeout
      headers: {
        'User-Agent': 'reWise-Backend/1.0.0'
      }
    });

    const data = response.data;

    // Check if iTunes API returned results
    if (!data.results || !Array.isArray(data.results)) {
      return res.status(200).json({ 
        podcasts: [],
        message: 'No podcasts found for the given search term'
      });
    }

    // Parse and format the response
    const podcasts = data.results.map(podcast => ({
      podcastName: podcast.collectionName || 'Unknown',
      feedUrl: podcast.feedUrl || null,
      artwork: podcast.artworkUrl600 || podcast.artworkUrl100 || null,
      artistName: podcast.artistName || 'Unknown'
    })).filter(podcast => podcast.feedUrl); // Only return podcasts with valid feed URLs

    console.log(`Found ${podcasts.length} podcasts for term: "${term}"`);

    res.status(200).json({
      podcasts,
      count: podcasts.length,
      searchTerm: term
    });

  } catch (error) {
    console.error('Search error:', error.message);
    
    if (error.code === 'ECONNABORTED') {
      return res.status(504).json({ 
        error: 'Request timeout',
        message: 'The iTunes API request timed out. Please try again.'
      });
    }
    
    if (error.response) {
      // iTunes API error
      return res.status(502).json({ 
        error: 'iTunes API error',
        message: 'Unable to fetch data from iTunes API',
        status: error.response.status
      });
    }
    
    res.status(500).json({ 
      error: 'Internal server error',
      message: 'An error occurred while searching for podcasts'
    });
  }
});

module.exports = router; 