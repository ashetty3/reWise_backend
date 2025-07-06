#!/usr/bin/env python3
"""
Test script for enhanced metadata fields in the /episodes endpoint
Demonstrates the UX improvements and validates the new metadata structure
"""

import asyncio
import httpx
import json
from datetime import datetime

# Test RSS feeds with different formats
TEST_FEEDS = [
    {
        "name": "NPR News (.xml)",
        "url": "https://feeds.npr.org/510313/podcast.xml",
        "expected_features": ["episodeNumber", "duration", "categories"]
    },
    {
        "name": "Huberman Lab (no extension)",
        "url": "https://feeds.megaphone.fm/huberman",
        "expected_features": ["duration", "explicit", "itunes_metadata"]
    }
]

async def test_enhanced_metadata():
    """Test the enhanced metadata fields"""
    
    base_url = "http://localhost:8000"
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        print("🎯 Testing Enhanced Metadata Fields")
        print("=" * 60)
        
        for test_feed in TEST_FEEDS:
            print(f"\n📻 Testing: {test_feed['name']}")
            print(f"🔗 Feed URL: {test_feed['url']}")
            print("-" * 50)
            
            try:
                # Test the episodes endpoint
                response = await client.get(
                    f"{base_url}/episodes",
                    params={"feedUrl": test_feed['url']}
                )
                
                if response.status_code == 200:
                    data = response.json()
                    
                    print(f"✅ Success! Status: {response.status_code}")
                    
                    # Test podcast metadata
                    podcast = data.get('podcast', {})
                    print(f"📻 Podcast: {podcast.get('title', 'N/A')}")
                    print(f"📝 Description: {podcast.get('description', 'N/A')[:100]}...")
                    print(f"🖼️  Artwork: {'✅' if podcast.get('artwork') else '❌'}")
                    
                    # Test episode metadata
                    episodes = data.get('episodes', [])
                    print(f"🎧 Episodes found: {len(episodes)}")
                    
                    if episodes:
                        episode = episodes[0]  # Test first episode
                        print(f"\n🎵 First Episode: {episode.get('title', 'N/A')}")
                        
                        # Test core fields
                        print("\n📋 Core Fields:")
                        print(f"  • Duration: {episode.get('duration', 'N/A')}")
                        print(f"  • Audio URL: {'✅' if episode.get('audioUrl') else '❌'}")
                        print(f"  • Episode Link: {'✅' if episode.get('episodeLink') else '❌'}")
                        print(f"  • Image: {'✅' if episode.get('image') else '❌'}")
                        
                        # Test enhanced UX metadata
                        print("\n🚀 Enhanced UX Metadata:")
                        print(f"  • Episode Number: {episode.get('episodeNumber', 'N/A')}")
                        print(f"  • Season: {episode.get('season', 'N/A')}")
                        print(f"  • Explicit: {episode.get('explicit', 'N/A')}")
                        print(f"  • Language: {episode.get('language', 'N/A')}")
                        print(f"  • File Size: {episode.get('fileSize', 'N/A')}")
                        print(f"  • Audio Quality: {episode.get('audioQuality', 'N/A')}")
                        print(f"  • Format: {episode.get('format', 'N/A')}")
                        print(f"  • Has Transcript: {episode.get('hasTranscript', 'N/A')}")
                        print(f"  • Transcript URL: {'✅' if episode.get('transcriptUrl') else '❌'}")
                        print(f"  • Show Notes URL: {'✅' if episode.get('showNotesUrl') else '❌'}")
                        
                        # Test content discovery fields
                        print("\n🔍 Content Discovery:")
                        categories = episode.get('categories', [])
                        keywords = episode.get('keywords', [])
                        guest_hosts = episode.get('guestHosts', [])
                        content_warnings = episode.get('contentWarnings', [])
                        
                        print(f"  • Categories: {categories if categories else 'None'}")
                        print(f"  • Keywords: {keywords if keywords else 'None'}")
                        print(f"  • Guest Hosts: {guest_hosts if guest_hosts else 'None'}")
                        print(f"  • Content Warnings: {content_warnings if content_warnings else 'None'}")
                        
                        # Test episode type fields
                        print("\n🎭 Episode Type:")
                        print(f"  • Is Live: {episode.get('isLive', 'N/A')}")
                        print(f"  • Is Rerun: {episode.get('isRerun', 'N/A')}")
                        
                        # Test navigation fields
                        print("\n🧭 Navigation:")
                        chapters = episode.get('chapters', [])
                        related_links = episode.get('relatedLinks', [])
                        
                        print(f"  • Chapters: {len(chapters)} found" if chapters else "  • Chapters: None")
                        print(f"  • Related Links: {len(related_links)} found" if related_links else "  • Related Links: None")
                        
                        # Test cache information
                        print("\n💾 Cache Information:")
                        print(f"  • Cached: {data.get('cached', 'N/A')}")
                        print(f"  • Cache Timestamp: {data.get('cacheTimestamp', 'N/A')}")
                        if data.get('cacheTimestamp'):
                            cache_time = datetime.fromtimestamp(data.get('cacheTimestamp'))
                            print(f"  • Cache Time: {cache_time}")
                        
                        # UX Impact Analysis
                        print("\n🎯 UX Impact Analysis:")
                        ux_score = 0
                        total_fields = 0
                        
                        # Check for fields that enhance user experience
                        ux_fields = [
                            ('episodeNumber', 'Episode context'),
                            ('duration', 'Time planning'),
                            ('explicit', 'Content awareness'),
                            ('hasTranscript', 'Accessibility'),
                            ('categories', 'Content discovery'),
                            ('guestHosts', 'Guest recognition'),
                            ('chapters', 'Navigation'),
                            ('relatedLinks', 'Resource access')
                        ]
                        
                        for field, description in ux_fields:
                            total_fields += 1
                            if episode.get(field):
                                ux_score += 1
                                print(f"  ✅ {description}: Available")
                            else:
                                print(f"  ❌ {description}: Not available")
                        
                        ux_percentage = (ux_score / total_fields) * 100
                        print(f"\n📊 UX Enhancement Score: {ux_score}/{total_fields} ({ux_percentage:.1f}%)")
                        
                        if ux_percentage >= 70:
                            print("🎉 Excellent UX metadata coverage!")
                        elif ux_percentage >= 50:
                            print("👍 Good UX metadata coverage")
                        else:
                            print("⚠️  Limited UX metadata coverage")
                    
                else:
                    print(f"❌ Error: {response.status_code}")
                    print(f"Response: {response.text}")
                    
            except Exception as e:
                print(f"❌ Exception: {str(e)}")
            
            print()

async def test_caching_behavior():
    """Test caching behavior"""
    print("\n🔄 Testing Caching Behavior")
    print("=" * 40)
    
    base_url = "http://localhost:8000"
    test_feed = "https://feeds.npr.org/510313/podcast.xml"
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        # First request (should be fresh)
        print("📡 Making first request (should be fresh)...")
        start_time = datetime.now()
        response1 = await client.get(f"{base_url}/episodes", params={"feedUrl": test_feed})
        first_request_time = (datetime.now() - start_time).total_seconds()
        
        if response1.status_code == 200:
            data1 = response1.json()
            print(f"✅ First request: {first_request_time:.2f}s, Cached: {data1.get('cached', False)}")
            
            # Second request (should be cached)
            print("📡 Making second request (should be cached)...")
            start_time = datetime.now()
            response2 = await client.get(f"{base_url}/episodes", params={"feedUrl": test_feed})
            second_request_time = (datetime.now() - start_time).total_seconds()
            
            if response2.status_code == 200:
                data2 = response2.json()
                print(f"✅ Second request: {second_request_time:.2f}s, Cached: {data2.get('cached', False)}")
                
                # Compare performance
                if second_request_time < first_request_time:
                    print(f"🚀 Caching working! Second request {first_request_time/second_request_time:.1f}x faster")
                else:
                    print("⚠️  Caching may not be working as expected")

async def main():
    """Main test function"""
    print("🎯 ReWise Backend - Enhanced Metadata Test")
    print("=" * 50)
    
    # Test enhanced metadata
    await test_enhanced_metadata()
    
    # Test caching behavior
    await test_caching_behavior()
    
    print("\n" + "=" * 50)
    print("✅ Test completed! Check the results above.")
    print("\n💡 Next steps:")
    print("1. Import the Postman collection for detailed API testing")
    print("2. Use the enhanced metadata in your frontend")
    print("3. Implement UX features based on the metadata guide")

if __name__ == "__main__":
    asyncio.run(main()) 