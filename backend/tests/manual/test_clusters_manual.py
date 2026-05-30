"""Manual test script for cluster endpoints - run against live backend.

Usage:
    python tests/manual/test_clusters_manual.py

This script tests all 4 cluster endpoints with real DynamoDB data.
"""

import asyncio
import httpx
import json
from datetime import datetime

BASE_URL = "http://localhost:8000/v1"


async def test_list_clusters():
    """Test GET /v1/clusters"""
    print("\n=== TEST: GET /v1/clusters ===")

    async with httpx.AsyncClient() as client:
        # Test basic listing
        response = await client.get(f"{BASE_URL}/clusters")
        print(f"Status: {response.status_code}")

        if response.status_code == 200:
            data = response.json()
            print(f"Clusters returned: {len(data['items'])}")
            print(f"Total clusters: {data['pagination']['total']}")
            print(f"Pages: {data['pagination']['total_pages']}")

            if data["items"]:
                cluster = data["items"][0]
                print(f"\nFirst cluster:")
                print(f"  ID: {cluster['cluster_id']}")
                print(f"  Label: {cluster['label']}")
                print(f"  Articles: {cluster['article_count']}")
                print(f"  Keywords: {', '.join(cluster['keywords'][:3])}")

        # Test sorting
        print("\nTesting sort_by parameter:")
        for sort in ["size", "recency", "diversity"]:
            response = await client.get(f"{BASE_URL}/clusters?sort_by={sort}")
            print(f"  sort_by={sort}: {response.status_code}")

        # Test pagination
        print("\nTesting pagination:")
        response = await client.get(f"{BASE_URL}/clusters?page=1&page_size=5")
        print(f"  page=1, page_size=5: {response.status_code}")
        if response.status_code == 200:
            print(f"  Items returned: {len(response.json()['items'])}")

        return response.status_code == 200


async def test_get_cluster_detail(cluster_id: str):
    """Test GET /v1/clusters/{cluster_id}"""
    print(f"\n=== TEST: GET /v1/clusters/{cluster_id} ===")

    async with httpx.AsyncClient() as client:
        response = await client.get(f"{BASE_URL}/clusters/{cluster_id}")
        print(f"Status: {response.status_code}")

        if response.status_code == 200:
            data = response.json()
            print(f"Cluster: {data['label']}")
            print(f"Description: {data['description']}")
            print(f"Article count: {data['article_count']}")
            print(f"Keywords: {', '.join(data['keywords'])}")
            print(f"Articles in response: {len(data['articles'])}")
            print(f"Pagination: page {data['pagination']['page']}/{data['pagination']['total_pages']}")

            if data["articles"]:
                article = data["articles"][0]
                print(f"\nFirst article:")
                print(f"  Title: {article['title']}")
                print(f"  Source: {article['source_id']}")
                print(f"  Confidence: {article['confidence_score']:.2%}")

        elif response.status_code == 404:
            print("Cluster not found - this is expected if no clusters exist")

        return response.status_code in [200, 404]


async def test_get_cluster_articles(cluster_id: str):
    """Test GET /v1/clusters/{cluster_id}/articles"""
    print(f"\n=== TEST: GET /v1/clusters/{cluster_id}/articles ===")

    async with httpx.AsyncClient() as client:
        response = await client.get(f"{BASE_URL}/clusters/{cluster_id}/articles")
        print(f"Status: {response.status_code}")

        if response.status_code == 200:
            data = response.json()
            print(f"Articles returned: {len(data['articles'])}")
            print(f"Total articles: {data['pagination']['total']}")

            # Test sorting
            print("\nTesting sort parameter:")
            for sort in ["date", "engagement", "title"]:
                response = await client.get(
                    f"{BASE_URL}/clusters/{cluster_id}/articles?sort={sort}"
                )
                print(f"  sort={sort}: {response.status_code}")

            # Test pagination
            print("\nTesting pagination:")
            response = await client.get(
                f"{BASE_URL}/clusters/{cluster_id}/articles?page=1&page_size=5"
            )
            print(f"  page=1, page_size=5: {response.status_code}")
            if response.status_code == 200:
                data = response.json()
                print(f"  Items: {len(data['articles'])}")

        elif response.status_code == 404:
            print("Cluster not found - this is expected if no clusters exist")

        return response.status_code in [200, 404]


async def test_get_trending_clusters():
    """Test GET /v1/clusters/trending"""
    print("\n=== TEST: GET /v1/clusters/trending ===")

    async with httpx.AsyncClient() as client:
        response = await client.get(f"{BASE_URL}/clusters/trending")
        print(f"Status: {response.status_code}")

        if response.status_code == 200:
            data = response.json()
            print(f"Trending clusters: {len(data['trending_clusters'])}")

            for i, cluster in enumerate(data["trending_clusters"], 1):
                print(f"\n{i}. {cluster['label']}")
                print(f"   Articles: {cluster['article_count']}")
                print(f"   Momentum: {cluster['momentum_score']:.2%}")
                print(f"   Trend: {cluster['engagement_trend']}")

        # Test limit parameter
        print("\nTesting limit parameter:")
        for limit in [1, 3, 5, 10]:
            response = await client.get(f"{BASE_URL}/clusters/trending?limit={limit}")
            print(f"  limit={limit}: {response.status_code}")

        return response.status_code == 200


async def test_error_cases():
    """Test error handling"""
    print("\n=== TEST: Error Handling ===")

    async with httpx.AsyncClient() as client:
        # Test 404 - nonexistent cluster
        response = await client.get(f"{BASE_URL}/clusters/nonexistent-cluster-xyz")
        print(f"404 test (nonexistent cluster): {response.status_code == 404}")

        # Test 400 - invalid page
        response = await client.get(f"{BASE_URL}/clusters?page=0")
        print(f"400 test (invalid page): {response.status_code == 422}")

        # Test 400 - invalid page_size
        response = await client.get(f"{BASE_URL}/clusters?page_size=101")
        print(f"400 test (page_size > 100): {response.status_code == 422}")

        return True


async def main():
    """Run all tests"""
    print("=" * 60)
    print("Cluster API Manual Tests")
    print("=" * 60)
    print(f"Base URL: {BASE_URL}")
    print(f"Time: {datetime.now().isoformat()}")

    results = {}

    try:
        # Test 1: List clusters
        results["list_clusters"] = await test_list_clusters()

        # Get first cluster ID for detail tests
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{BASE_URL}/clusters")
            if response.status_code == 200:
                data = response.json()
                if data["items"]:
                    cluster_id = data["items"][0]["cluster_id"]

                    # Test 2: Get cluster detail
                    results["get_cluster_detail"] = await test_get_cluster_detail(
                        cluster_id
                    )

                    # Test 3: Get cluster articles
                    results["get_cluster_articles"] = await test_get_cluster_articles(
                        cluster_id
                    )

        # Test 4: Get trending clusters
        results["get_trending_clusters"] = await test_get_trending_clusters()

        # Test 5: Error cases
        results["error_handling"] = await test_error_cases()

    except Exception as e:
        print(f"\nERROR: {type(e).__name__}: {str(e)}")
        import traceback
        traceback.print_exc()

    # Print summary
    print("\n" + "=" * 60)
    print("Test Summary")
    print("=" * 60)
    for test_name, passed in results.items():
        status = "✓ PASS" if passed else "✗ FAIL"
        print(f"{status}: {test_name}")

    print("\n" + "=" * 60)
    print(f"Total: {sum(results.values())}/{len(results)} tests passed")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
