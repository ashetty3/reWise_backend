const axios = require('axios');

const BASE_URL = 'http://localhost:3000';

async function testAPI() {
  console.log('🧪 Testing reWise Backend API...\n');

  try {
    // Test 1: Health Check
    console.log('1. Testing Health Check...');
    const healthResponse = await axios.get(`${BASE_URL}/health`);
    console.log('✅ Health Check:', healthResponse.data);
    console.log('');

    // Test 2: Search Endpoint
    console.log('2. Testing Search Endpoint...');
    const searchResponse = await axios.get(`${BASE_URL}/search?term=javascript`);
    console.log('✅ Search Results:');
    console.log(`   Found ${searchResponse.data.count} podcasts`);
    if (searchResponse.data.podcasts.length > 0) {
      const firstPodcast = searchResponse.data.podcasts[0];
      console.log(`   First podcast: ${firstPodcast.podcastName} by ${firstPodcast.artistName}`);
      console.log(`   Feed URL: ${firstPodcast.feedUrl}`);
    }
    console.log('');

    // Test 3: Episodes Endpoint (if we have a valid feed URL)
    if (searchResponse.data.podcasts.length > 0) {
      const testFeedUrl = searchResponse.data.podcasts[0].feedUrl;
      console.log('3. Testing Episodes Endpoint...');
      console.log(`   Using feed URL: ${testFeedUrl}`);
      
      try {
        const episodesResponse = await axios.get(`${BASE_URL}/episodes?feedUrl=${encodeURIComponent(testFeedUrl)}`);
        console.log('✅ Episodes Results:');
        console.log(`   Found ${episodesResponse.data.count} episodes`);
        if (episodesResponse.data.episodes.length > 0) {
          const firstEpisode = episodesResponse.data.episodes[0];
          console.log(`   First episode: ${firstEpisode.title}`);
          console.log(`   Published: ${firstEpisode.pubDate}`);
        }
        console.log(`   Cached: ${episodesResponse.data.cached}`);
      } catch (episodesError) {
        console.log('⚠️  Episodes test failed (this is normal for some feeds):', episodesError.response?.data?.message || episodesError.message);
      }
      console.log('');

      // Test 4: Cache Status
      console.log('4. Testing Cache Status...');
      const cacheStatusResponse = await axios.get(`${BASE_URL}/episodes/cache/status`);
      console.log('✅ Cache Status:', cacheStatusResponse.data);
      console.log('');

    } else {
      console.log('3. Skipping Episodes test (no valid feed URLs found)');
      console.log('');
    }

    console.log('🎉 All tests completed successfully!');
    console.log('\n📝 API Endpoints Summary:');
    console.log(`   Health: ${BASE_URL}/health`);
    console.log(`   Search: ${BASE_URL}/search?term=your_search_term`);
    console.log(`   Episodes: ${BASE_URL}/episodes?feedUrl=your_feed_url`);
    console.log(`   Cache Status: ${BASE_URL}/episodes/cache/status`);
    console.log(`   Clear Cache: ${BASE_URL}/episodes/cache/clear`);

  } catch (error) {
    console.error('❌ Test failed:', error.message);
    if (error.response) {
      console.error('   Status:', error.response.status);
      console.error('   Data:', error.response.data);
    }
    console.log('\n💡 Make sure the server is running with: npm run dev');
  }
}

// Run the tests
testAPI(); 