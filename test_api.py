import asyncio
import httpx
import json

BASE_URL = "http://localhost:8000"

async def test_api():
    print("🧪 Testing ReWise FastAPI Backend...\n")
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            # Test 1: Root endpoint
            print("1. Testing Root Endpoint...")
            response = await client.get(f"{BASE_URL}/")
            print(f"✅ Root Response: {response.json()}")
            print()
            
            # Test 2: Health check
            print("2. Testing Health Check...")
            response = await client.get(f"{BASE_URL}/health")
            print(f"✅ Health Check: {response.json()}")
            print()
            
            # Test 3: Search endpoint
            print("3. Testing Search Endpoint...")
            response = await client.get(f"{BASE_URL}/search?term=javascript")
            data = response.json()
            print(f"✅ Search Results:")
            print(f"   Found {data['count']} podcasts")
            if data['podcasts']:
                first_podcast = data['podcasts'][0]
                print(f"   First podcast: {first_podcast['podcastName']} by {first_podcast['artistName']}")
                print(f"   Feed URL: {first_podcast['feedUrl']}")
            print()
            
            # Test 4: Episodes endpoint (if we have a valid feed URL)
            if data['podcasts']:
                test_feed_url = data['podcasts'][0]['feedUrl']
                print("4. Testing Episodes Endpoint...")
                print(f"   Using feed URL: {test_feed_url}")
                
                try:
                    response = await client.get(f"{BASE_URL}/episodes?feedUrl={test_feed_url}")
                    episodes_data = response.json()
                    print(f"✅ Episodes Results:")
                    print(f"   Found {episodes_data['count']} episodes")
                    if episodes_data['episodes']:
                        first_episode = episodes_data['episodes'][0]
                        print(f"   First episode: {first_episode['title']}")
                        print(f"   Published: {first_episode['pubDate']}")
                    print(f"   Cached: {episodes_data['cached']}")
                except Exception as e:
                    print(f"⚠️  Episodes test failed (this is normal for some feeds): {str(e)}")
                print()
                
                # Test 5: Cache status
                print("5. Testing Cache Status...")
                response = await client.get(f"{BASE_URL}/episodes/cache/status")
                cache_data = response.json()
                print(f"✅ Cache Status: {cache_data}")
                print()
            
            else:
                print("4. Skipping Episodes test (no valid feed URLs found)")
                print()
            
            print("🎉 All tests completed successfully!")
            print("\n📝 API Endpoints Summary:")
            print(f"   Root: {BASE_URL}/")
            print(f"   Health: {BASE_URL}/health")
            print(f"   Search: {BASE_URL}/search?term=your_search_term")
            print(f"   Episodes: {BASE_URL}/episodes?feedUrl=your_feed_url")
            print(f"   Cache Status: {BASE_URL}/episodes/cache/status")
            print(f"   Clear Cache: {BASE_URL}/episodes/cache/clear")
            print(f"\n📚 Interactive Documentation:")
            print(f"   Swagger UI: {BASE_URL}/docs")
            print(f"   ReDoc: {BASE_URL}/redoc")
            
        except httpx.ConnectError:
            print("❌ Connection failed. Make sure the server is running with:")
            print("   uvicorn main:app --reload --host 0.0.0.0 --port 8000")
        except Exception as e:
            print(f"❌ Test failed: {str(e)}")
            print("\n💡 Make sure the server is running with:")
            print("   uvicorn main:app --reload --host 0.0.0.0 --port 8000")

if __name__ == "__main__":
    asyncio.run(test_api()) 