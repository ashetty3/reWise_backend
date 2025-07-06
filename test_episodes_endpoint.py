#!/usr/bin/env python3
"""
Test script for the updated /episodes endpoint
Tests various RSS feed formats and validates the new response structure
"""

import asyncio
import httpx
import json
from urllib.parse import quote

# Test RSS feed URLs (these are public podcast feeds)
TEST_FEEDS = [
    "https://feeds.npr.org/510313/podcast.xml",  # NPR News
    "https://feeds.megaphone.fm/huberman",       # Huberman Lab
    "https://feeds.buzzsprout.com/1234567.rss",  # Example with .rss extension
    "https://feeds.simplecast.com/abc123",       # Example with no extension
]

async def test_episodes_endpoint():
    """Test the /episodes endpoint with various feed formats"""
    
    # Start the server (you'll need to run this separately)
    base_url = "http://localhost:8000"
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        print("Testing /episodes endpoint with various RSS feed formats...")
        print("=" * 60)
        
        for i, feed_url in enumerate(TEST_FEEDS, 1):
            print(f"\nTest {i}: {feed_url}")
            print("-" * 40)
            
            try:
                # Test the episodes endpoint
                response = await client.get(
                    f"{base_url}/episodes",
                    params={"feedUrl": feed_url}
                )
                
                if response.status_code == 200:
                    data = response.json()
                    
                    # Validate the new response structure
                    print(f"✅ Success! Status: {response.status_code}")
                    print(f"📻 Podcast: {data.get('podcast', {}).get('title', 'N/A')}")
                    print(f"📝 Description: {data.get('podcast', {}).get('description', 'N/A')[:100]}...")
                    print(f"🖼️  Artwork: {data.get('podcast', {}).get('artwork', 'N/A')}")
                    print(f"🎧 Episodes: {data.get('count', 0)}")
                    print(f"💾 Cached: {data.get('cached', False)}")
                    
                    # Check first episode structure
                    if data.get('episodes') and len(data['episodes']) > 0:
                        first_episode = data['episodes'][0]
                        print(f"🎵 First episode: {first_episode.get('title', 'N/A')}")
                        print(f"⏱️  Duration: {first_episode.get('duration', 'N/A')}")
                        print(f"🔗 Episode link: {first_episode.get('episodeLink', 'N/A')}")
                        print(f"🖼️  Episode image: {first_episode.get('image', 'N/A')}")
                        print(f"🎵 Audio URL: {first_episode.get('audioUrl', 'N/A')[:50]}...")
                    
                else:
                    print(f"❌ Error: {response.status_code}")
                    print(f"Response: {response.text}")
                    
            except Exception as e:
                print(f"❌ Exception: {str(e)}")
            
            print()

async def test_health_endpoint():
    """Test the health endpoint to ensure server is running"""
    base_url = "http://localhost:8000"
    
    async with httpx.AsyncClient(timeout=10.0) as client:
        try:
            response = await client.get(f"{base_url}/health")
            if response.status_code == 200:
                print("✅ Health check passed - server is running")
                return True
            else:
                print(f"❌ Health check failed: {response.status_code}")
                return False
        except Exception as e:
            print(f"❌ Cannot connect to server: {str(e)}")
            print("Make sure the server is running with: python main.py")
            return False

async def main():
    """Main test function"""
    print("ReWise Backend - Episodes Endpoint Test")
    print("=" * 50)
    
    # First check if server is running
    if not await test_health_endpoint():
        return
    
    # Test the episodes endpoint
    await test_episodes_endpoint()
    
    print("\n" + "=" * 50)
    print("Test completed!")

if __name__ == "__main__":
    asyncio.run(main()) 