#!/usr/bin/env python3
"""
GraphRAG Test Runner
Tests the HR Policy chatbot with 20 predefined test cases.
Measures response quality and latency.
"""

import json
import time
import requests
from datetime import datetime

# Configuration
BASE_URL = "http://localhost:18000"
ACCESS_URL = "hr-policy"

def get_token():
    """Get authentication token."""
    response = requests.post(
        f"{BASE_URL}/api/v1/auth/login",
        json={"email": "admin@example.com", "password": "Admin123456"}
    )
    return response.json()["access_token"]

def create_session():
    """Create a new chat session."""
    response = requests.post(f"{BASE_URL}/api/v1/chat/{ACCESS_URL}/sessions")
    if response.status_code != 200:
        print(f"Failed to create session: {response.text}")
        return None
    return response.json()["id"]

def send_message(session_id: str, message: str):
    """Send a message and get response (non-streaming)."""
    start_time = time.time()

    response = requests.post(
        f"{BASE_URL}/api/v1/chat/{ACCESS_URL}/sessions/{session_id}/messages",
        json={"content": message, "stream": False},
        timeout=180
    )

    end_time = time.time()
    latency = end_time - start_time

    if response.status_code != 200:
        return None, latency, f"Error: {response.status_code}"

    data = response.json()
    return data.get("content", ""), latency, data.get("sources", [])

def check_keywords(response: str, expected_keywords: list) -> tuple:
    """Check if response contains expected keywords."""
    found = []
    missing = []
    response_lower = response.lower()

    for keyword in expected_keywords:
        if keyword.lower() in response_lower:
            found.append(keyword)
        else:
            missing.append(keyword)

    score = len(found) / len(expected_keywords) if expected_keywords else 0
    return score, found, missing

def run_tests():
    """Run all test cases and collect results."""
    # Load test cases
    with open("/home/magic/work/GraphRAG/test_cases.json", "r") as f:
        test_data = json.load(f)

    test_cases = test_data["test_cases"]
    results = []

    print("=" * 80)
    print("GraphRAG HR Policy Bot Test Run")
    print(f"Started at: {datetime.now().isoformat()}")
    print("=" * 80)
    print()

    total_latency = 0
    total_score = 0

    for i, test_case in enumerate(test_cases, 1):
        print(f"\n[Test {i}/{len(test_cases)}] {test_case['category']} - {test_case['difficulty']}")
        print(f"Question: {test_case['question']}")
        print("-" * 60)

        # Create new session for each test
        session_id = create_session()
        if not session_id:
            print("Failed to create session, skipping...")
            continue

        # Send message
        response, latency, sources = send_message(session_id, test_case["question"])

        if response is None:
            print(f"Error: {sources}")
            results.append({
                "id": test_case["id"],
                "category": test_case["category"],
                "difficulty": test_case["difficulty"],
                "question": test_case["question"],
                "response": None,
                "latency": latency,
                "score": 0,
                "error": str(sources)
            })
            continue

        # Check keywords
        score, found, missing = check_keywords(response, test_case["expected_keywords"])

        total_latency += latency
        total_score += score

        print(f"Response ({latency:.2f}s):")
        print(response[:500] + "..." if len(response) > 500 else response)
        print()
        print(f"Keyword Score: {score*100:.1f}%")
        print(f"  Found: {found}")
        print(f"  Missing: {missing}")
        if sources:
            print(f"  Sources: {len(sources)} citations")

        results.append({
            "id": test_case["id"],
            "category": test_case["category"],
            "difficulty": test_case["difficulty"],
            "question": test_case["question"],
            "response": response,
            "latency": latency,
            "score": score,
            "found_keywords": found,
            "missing_keywords": missing,
            "sources": sources
        })

    # Summary
    print("\n" + "=" * 80)
    print("TEST SUMMARY")
    print("=" * 80)

    successful = [r for r in results if r.get("response") is not None]
    failed = [r for r in results if r.get("response") is None]

    print(f"Total Tests: {len(test_cases)}")
    print(f"Successful: {len(successful)}")
    print(f"Failed: {len(failed)}")

    if successful:
        avg_latency = sum(r["latency"] for r in successful) / len(successful)
        avg_score = sum(r["score"] for r in successful) / len(successful)

        print(f"\nLatency Statistics:")
        print(f"  Average: {avg_latency:.2f}s")
        print(f"  Min: {min(r['latency'] for r in successful):.2f}s")
        print(f"  Max: {max(r['latency'] for r in successful):.2f}s")

        print(f"\nQuality Statistics:")
        print(f"  Average Keyword Score: {avg_score*100:.1f}%")

        # By difficulty
        for difficulty in ["easy", "medium", "hard"]:
            diff_results = [r for r in successful if r["difficulty"] == difficulty]
            if diff_results:
                diff_avg_score = sum(r["score"] for r in diff_results) / len(diff_results)
                diff_avg_latency = sum(r["latency"] for r in diff_results) / len(diff_results)
                print(f"\n  {difficulty.upper()}:")
                print(f"    Count: {len(diff_results)}")
                print(f"    Avg Score: {diff_avg_score*100:.1f}%")
                print(f"    Avg Latency: {diff_avg_latency:.2f}s")

        # By category
        print("\nBy Category:")
        categories = set(r["category"] for r in successful)
        for category in sorted(categories):
            cat_results = [r for r in successful if r["category"] == category]
            cat_avg_score = sum(r["score"] for r in cat_results) / len(cat_results)
            print(f"  {category}: {cat_avg_score*100:.1f}%")

    # Save results
    with open("/home/magic/work/GraphRAG/test_results.json", "w") as f:
        json.dump({
            "timestamp": datetime.now().isoformat(),
            "summary": {
                "total": len(test_cases),
                "successful": len(successful),
                "failed": len(failed),
                "avg_latency": avg_latency if successful else 0,
                "avg_score": avg_score if successful else 0
            },
            "results": results
        }, f, ensure_ascii=False, indent=2)

    print(f"\nResults saved to: /home/magic/work/GraphRAG/test_results.json")
    print("=" * 80)

    return results

if __name__ == "__main__":
    run_tests()
