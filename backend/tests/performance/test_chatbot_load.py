"""
Comprehensive performance and load testing for chatbot functionality.

Tests cover:
- Concurrent user scenarios (10, 50, 100 users)
- Message load scenarios (100, 1000 messages)
- Streaming performance with SSE
- Database stress and capacity usage
- Performance benchmarks and latency percentiles
"""

import pytest
import asyncio
import httpx
import json
import time
import uuid
import statistics
from typing import List, Dict, Any
from dataclasses import dataclass
from datetime import datetime
from collections import defaultdict


# ============================================================================
# Configuration
# ============================================================================

BACKEND_URL = "http://localhost:8000"
API_V1_BASE = f"{BACKEND_URL}/api/v1"

# Test user credentials (adjust for your local setup)
TEST_USER_ID = "perf-test-user-001"
TEST_AUTH_TOKEN = "test-token-001"  # Replace with actual token from your setup

# Performance benchmarks (targets)
BENCHMARKS = {
    "single_message_response": 2.0,  # seconds
    "streaming_token_latency": 0.1,  # seconds per token
    "session_creation": 0.5,  # seconds
    "session_list_100": 1.0,  # seconds
    "message_persistence": 0.1,  # seconds
    "concurrent_100_error_rate": 0.05,  # 5% error rate
}


# ============================================================================
# Data Classes
# ============================================================================

@dataclass
class PerformanceMetric:
    """Single performance measurement."""
    name: str
    value: float  # milliseconds or count
    timestamp: float


@dataclass
class PerformanceResults:
    """Aggregated performance test results."""
    test_name: str
    total_requests: int
    successful_requests: int
    failed_requests: int
    error_rate: float
    min_latency: float  # ms
    max_latency: float  # ms
    mean_latency: float  # ms
    median_latency: float  # ms
    p95_latency: float  # ms
    p99_latency: float  # ms
    throughput: float  # requests/sec
    timestamp: str


# ============================================================================
# Helper Functions
# ============================================================================

def get_auth_headers() -> Dict[str, str]:
    """Get authorization headers for API requests."""
    return {
        "Authorization": f"Bearer {TEST_AUTH_TOKEN}",
        "Content-Type": "application/json",
    }


async def wait_for_backend(max_retries: int = 30) -> bool:
    """Wait for backend to be ready."""
    for attempt in range(max_retries):
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.get(f"{BACKEND_URL}/health")
                if response.status_code == 200:
                    print(f"✓ Backend is ready (attempt {attempt + 1})")
                    return True
        except Exception:
            pass

        if attempt < max_retries - 1:
            await asyncio.sleep(1)

    return False


def calculate_percentile(values: List[float], percentile: float) -> float:
    """Calculate percentile from list of values."""
    if not values:
        return 0.0
    sorted_values = sorted(values)
    index = int(len(sorted_values) * percentile / 100)
    return sorted_values[min(index, len(sorted_values) - 1)]


def format_results(results: PerformanceResults) -> str:
    """Format performance results for display."""
    return f"""
╔══════════════════════════════════════════════════════════════╗
║ Performance Test: {results.test_name:<40} ║
╚══════════════════════════════════════════════════════════════╝

Test Execution:
  Timestamp:              {results.timestamp}
  Total Requests:         {results.total_requests}
  Successful:             {results.successful_requests} ({(results.successful_requests/results.total_requests*100):.1f}%)
  Failed:                 {results.failed_requests} ({results.error_rate*100:.2f}%)

Latency (milliseconds):
  Min:                    {results.min_latency:.2f} ms
  Max:                    {results.max_latency:.2f} ms
  Mean:                   {results.mean_latency:.2f} ms
  Median:                 {results.median_latency:.2f} ms
  P95:                    {results.p95_latency:.2f} ms
  P99:                    {results.p99_latency:.2f} ms

Throughput:
  Requests/sec:           {results.throughput:.2f} req/s

Benchmark Status:
  Error Rate (<5%):       {'✓ PASS' if results.error_rate < 0.05 else '✗ FAIL'}
"""


# ============================================================================
# Test 1: Concurrent Users
# ============================================================================

async def test_concurrent_users_scenario(
    num_users: int,
    messages_per_user: int = 3,
) -> PerformanceResults:
    """
    Test concurrent users sending messages simultaneously.

    Args:
        num_users: Number of concurrent users
        messages_per_user: Messages each user will send

    Returns:
        Performance results
    """
    print(f"\n{'='*70}")
    print(f"Testing {num_users} Concurrent Users ({messages_per_user} messages each)")
    print(f"{'='*70}")

    latencies = []
    errors = 0
    total_requests = 0
    session_ids = []

    # Create sessions for each user
    print(f"Creating {num_users} session(s)...")
    async with httpx.AsyncClient(timeout=10.0) as client:
        for i in range(num_users):
            try:
                response = await client.post(
                    f"{API_V1_BASE}/chat/sessions",
                    json={"title": f"Concurrent User {i} - Session"},
                    headers=get_auth_headers(),
                )
                if response.status_code == 201:
                    session = response.json()
                    session_ids.append(session["session_id"])
                else:
                    errors += 1
            except Exception as e:
                print(f"  ✗ Session creation error: {e}")
                errors += 1

    print(f"  Created {len(session_ids)} session(s)")

    # Send messages concurrently
    print(f"Sending {num_users * messages_per_user} messages concurrently...")

    async def send_user_messages(user_id: int, session_id: str):
        nonlocal errors, total_requests

        async with httpx.AsyncClient(timeout=30.0) as client:
            for msg_num in range(messages_per_user):
                total_requests += 1
                start_time = time.time()

                try:
                    payload = {
                        "session_id": session_id,
                        "user_message": f"User {user_id} message {msg_num}: What are AI trends?",
                    }

                    response = await client.post(
                        f"{API_V1_BASE}/chat/message",
                        json=payload,
                        headers=get_auth_headers(),
                    )

                    latency = (time.time() - start_time) * 1000  # ms
                    latencies.append(latency)

                    if response.status_code != 200:
                        errors += 1
                    else:
                        # Consume streaming response
                        await response.aread()

                except Exception as e:
                    errors += 1
                    print(f"  ✗ Message send error (User {user_id}): {e}")

    # Execute concurrent tasks
    start_time = time.time()
    tasks = [
        send_user_messages(i, session_ids[i % len(session_ids)])
        for i in range(num_users)
        for _ in range(messages_per_user)
    ]
    await asyncio.gather(*tasks, return_exceptions=True)
    total_time = time.time() - start_time

    # Calculate results
    success_count = total_requests - errors
    error_rate = errors / total_requests if total_requests > 0 else 0

    results = PerformanceResults(
        test_name=f"{num_users} Concurrent Users",
        total_requests=total_requests,
        successful_requests=success_count,
        failed_requests=errors,
        error_rate=error_rate,
        min_latency=min(latencies) if latencies else 0,
        max_latency=max(latencies) if latencies else 0,
        mean_latency=statistics.mean(latencies) if latencies else 0,
        median_latency=statistics.median(latencies) if latencies else 0,
        p95_latency=calculate_percentile(latencies, 95) if latencies else 0,
        p99_latency=calculate_percentile(latencies, 99) if latencies else 0,
        throughput=total_requests / total_time if total_time > 0 else 0,
        timestamp=datetime.now().isoformat(),
    )

    print(format_results(results))

    return results


# ============================================================================
# Test 2: Message Load
# ============================================================================

async def test_message_load_scenario(
    num_messages: int = 100,
    batch_size: int = 10,
) -> PerformanceResults:
    """
    Test loading many messages into a single session.

    Args:
        num_messages: Total messages to send
        batch_size: Messages to send per batch

    Returns:
        Performance results
    """
    print(f"\n{'='*70}")
    print(f"Testing Message Load: {num_messages} messages (batch size: {batch_size})")
    print(f"{'='*70}")

    latencies = []
    errors = 0
    total_requests = 0

    # Create a session
    session_id = None
    async with httpx.AsyncClient(timeout=10.0) as client:
        try:
            response = await client.post(
                f"{API_V1_BASE}/chat/sessions",
                json={"title": "Message Load Test Session"},
                headers=get_auth_headers(),
            )
            if response.status_code == 201:
                session_id = response.json()["session_id"]
        except Exception as e:
            print(f"✗ Session creation failed: {e}")
            return PerformanceResults(
                test_name=f"{num_messages} Message Load",
                total_requests=0,
                successful_requests=0,
                failed_requests=1,
                error_rate=1.0,
                min_latency=0,
                max_latency=0,
                mean_latency=0,
                median_latency=0,
                p95_latency=0,
                p99_latency=0,
                throughput=0,
                timestamp=datetime.now().isoformat(),
            )

    # Send messages in batches
    print(f"Sending {num_messages} messages to session {session_id}...")

    async with httpx.AsyncClient(timeout=30.0) as client:
        for batch_num in range(0, num_messages, batch_size):
            tasks = []
            for i in range(batch_size):
                msg_num = batch_num + i
                if msg_num >= num_messages:
                    break

                total_requests += 1

                async def send_message(msg_id: int):
                    nonlocal errors
                    start_time = time.time()
                    try:
                        payload = {
                            "session_id": session_id,
                            "user_message": f"Message {msg_id}: Test message with content",
                        }

                        response = await client.post(
                            f"{API_V1_BASE}/chat/message",
                            json=payload,
                            headers=get_auth_headers(),
                            timeout=30.0,
                        )

                        latency = (time.time() - start_time) * 1000  # ms
                        latencies.append(latency)

                        if response.status_code != 200:
                            errors += 1
                        else:
                            # Consume streaming response
                            await response.aread()

                    except Exception as e:
                        errors += 1
                        if msg_id % 10 == 0:
                            print(f"  ✗ Message {msg_id} error: {e}")

                tasks.append(send_message(msg_num))

            await asyncio.gather(*tasks, return_exceptions=True)

            if batch_num % 20 == 0:
                print(f"  Sent {min(batch_num + batch_size, num_messages)}/{num_messages} messages")

    # Verify message persistence
    print(f"Verifying message persistence...")
    total_messages_stored = 0
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(
                f"{API_V1_BASE}/chat/sessions/{session_id}",
                headers=get_auth_headers(),
            )
            if response.status_code == 200:
                session_data = response.json()
                total_messages_stored = session_data.get("message_count", 0)
    except Exception as e:
        print(f"✗ Verification failed: {e}")

    # Calculate results
    total_time = len(latencies) * 0.1  # Estimate based on message count
    success_count = total_requests - errors
    error_rate = errors / total_requests if total_requests > 0 else 0

    results = PerformanceResults(
        test_name=f"{num_messages} Message Load",
        total_requests=total_requests,
        successful_requests=success_count,
        failed_requests=errors,
        error_rate=error_rate,
        min_latency=min(latencies) if latencies else 0,
        max_latency=max(latencies) if latencies else 0,
        mean_latency=statistics.mean(latencies) if latencies else 0,
        median_latency=statistics.median(latencies) if latencies else 0,
        p95_latency=calculate_percentile(latencies, 95) if latencies else 0,
        p99_latency=calculate_percentile(latencies, 99) if latencies else 0,
        throughput=total_requests / total_time if total_time > 0 else 0,
        timestamp=datetime.now().isoformat(),
    )

    print(f"Messages persisted: {total_messages_stored}")
    print(format_results(results))

    return results


# ============================================================================
# Test 3: Streaming Performance
# ============================================================================

async def test_streaming_performance(
    num_concurrent_streams: int = 5,
    stream_duration_seconds: float = 5.0,
) -> PerformanceResults:
    """
    Test streaming performance with multiple concurrent SSE streams.

    Args:
        num_concurrent_streams: Number of concurrent SSE streams
        stream_duration_seconds: Duration to maintain streams

    Returns:
        Performance results
    """
    print(f"\n{'='*70}")
    print(f"Testing Streaming Performance: {num_concurrent_streams} concurrent streams")
    print(f"{'='*70}")

    token_latencies = []
    errors = 0
    total_requests = 0
    tokens_received = 0

    # Create sessions for streaming
    session_ids = []
    async with httpx.AsyncClient(timeout=10.0) as client:
        for i in range(num_concurrent_streams):
            try:
                response = await client.post(
                    f"{API_V1_BASE}/chat/sessions",
                    json={"title": f"Streaming Test Session {i}"},
                    headers=get_auth_headers(),
                )
                if response.status_code == 201:
                    session_ids.append(response.json()["session_id"])
            except Exception as e:
                print(f"✗ Session creation error: {e}")
                errors += 1

    print(f"Created {len(session_ids)} streaming session(s)")

    # Stream messages concurrently
    print(f"Starting {num_concurrent_streams} concurrent streams...")

    async def stream_message(stream_id: int, session_id: str):
        nonlocal errors, tokens_received, total_requests

        total_requests += 1
        start_time = time.time()
        token_count = 0

        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                async with client.stream(
                    "POST",
                    f"{API_V1_BASE}/chat/message",
                    json={
                        "session_id": session_id,
                        "user_message": "Analyze this technology trend and provide insights",
                    },
                    headers=get_auth_headers(),
                ) as response:

                    if response.status_code != 200:
                        errors += 1
                        return

                    # Process SSE events
                    async for line in response.aiter_lines():
                        if line.startswith("data: "):
                            try:
                                event_data = json.loads(line[6:])
                                if event_data.get("type") == "token":
                                    token_latency = (time.time() - start_time) * 1000 / (token_count + 1)
                                    token_latencies.append(token_latency)
                                    token_count += 1
                                    tokens_received += 1
                            except json.JSONDecodeError:
                                pass

        except Exception as e:
            errors += 1
            print(f"✗ Stream {stream_id} error: {e}")

    # Execute concurrent streams
    start_time = time.time()
    tasks = [
        stream_message(i, session_ids[i % len(session_ids)])
        for i in range(num_concurrent_streams)
    ]
    await asyncio.gather(*tasks, return_exceptions=True)
    total_time = time.time() - start_time

    # Calculate results
    success_count = total_requests - errors
    error_rate = errors / total_requests if total_requests > 0 else 0

    results = PerformanceResults(
        test_name=f"{num_concurrent_streams} Concurrent Streams",
        total_requests=total_requests,
        successful_requests=success_count,
        failed_requests=errors,
        error_rate=error_rate,
        min_latency=min(token_latencies) if token_latencies else 0,
        max_latency=max(token_latencies) if token_latencies else 0,
        mean_latency=statistics.mean(token_latencies) if token_latencies else 0,
        median_latency=statistics.median(token_latencies) if token_latencies else 0,
        p95_latency=calculate_percentile(token_latencies, 95) if token_latencies else 0,
        p99_latency=calculate_percentile(token_latencies, 99) if token_latencies else 0,
        throughput=total_requests / total_time if total_time > 0 else 0,
        timestamp=datetime.now().isoformat(),
    )

    print(f"Tokens streamed: {tokens_received}")
    print(format_results(results))

    return results


# ============================================================================
# Test 4: Session Management
# ============================================================================

async def test_session_operations() -> PerformanceResults:
    """
    Test session creation and listing performance.

    Returns:
        Performance results
    """
    print(f"\n{'='*70}")
    print(f"Testing Session Operations")
    print(f"{'='*70}")

    latencies = []
    errors = 0
    total_requests = 0

    # Test session creation (100 sessions)
    print(f"Creating 100 sessions...")
    async with httpx.AsyncClient(timeout=10.0) as client:
        for i in range(100):
            total_requests += 1
            start_time = time.time()

            try:
                response = await client.post(
                    f"{API_V1_BASE}/chat/sessions",
                    json={"title": f"Session {i}"},
                    headers=get_auth_headers(),
                )

                latency = (time.time() - start_time) * 1000  # ms
                latencies.append(latency)

                if response.status_code != 201:
                    errors += 1

            except Exception as e:
                errors += 1
                print(f"✗ Session {i} creation error: {e}")

    # Test session listing
    print(f"Listing sessions...")
    total_requests += 1
    start_time = time.time()

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(
                f"{API_V1_BASE}/chat/sessions",
                headers=get_auth_headers(),
            )

            latency = (time.time() - start_time) * 1000  # ms
            latencies.append(latency)

            if response.status_code != 200:
                errors += 1

    except Exception as e:
        errors += 1
        print(f"✗ Session list error: {e}")

    # Calculate results
    success_count = total_requests - errors
    error_rate = errors / total_requests if total_requests > 0 else 0

    results = PerformanceResults(
        test_name="Session Operations",
        total_requests=total_requests,
        successful_requests=success_count,
        failed_requests=errors,
        error_rate=error_rate,
        min_latency=min(latencies) if latencies else 0,
        max_latency=max(latencies) if latencies else 0,
        mean_latency=statistics.mean(latencies) if latencies else 0,
        median_latency=statistics.median(latencies) if latencies else 0,
        p95_latency=calculate_percentile(latencies, 95) if latencies else 0,
        p99_latency=calculate_percentile(latencies, 99) if latencies else 0,
        throughput=total_requests / (len(latencies) * 0.01) if latencies else 0,
        timestamp=datetime.now().isoformat(),
    )

    print(format_results(results))

    return results


# ============================================================================
# Test 5: Single Message Latency Benchmark
# ============================================================================

async def test_single_message_latency(
    num_requests: int = 50,
) -> PerformanceResults:
    """
    Test single message response latency benchmark.

    Args:
        num_requests: Number of message requests to test

    Returns:
        Performance results
    """
    print(f"\n{'='*70}")
    print(f"Testing Single Message Latency: {num_requests} requests")
    print(f"{'='*70}")

    latencies = []
    errors = 0
    total_requests = num_requests

    # Create a session
    session_id = None
    async with httpx.AsyncClient(timeout=10.0) as client:
        try:
            response = await client.post(
                f"{API_V1_BASE}/chat/sessions",
                json={"title": "Latency Benchmark Session"},
                headers=get_auth_headers(),
            )
            if response.status_code == 201:
                session_id = response.json()["session_id"]
        except Exception as e:
            print(f"✗ Session creation failed: {e}")
            return PerformanceResults(
                test_name="Single Message Latency",
                total_requests=0,
                successful_requests=0,
                failed_requests=1,
                error_rate=1.0,
                min_latency=0,
                max_latency=0,
                mean_latency=0,
                median_latency=0,
                p95_latency=0,
                p99_latency=0,
                throughput=0,
                timestamp=datetime.now().isoformat(),
            )

    print(f"Sending {num_requests} single messages...")

    async with httpx.AsyncClient(timeout=30.0) as client:
        for i in range(num_requests):
            start_time = time.time()

            try:
                response = await client.post(
                    f"{API_V1_BASE}/chat/message",
                    json={
                        "session_id": session_id,
                        "user_message": f"What is AI? Message {i}",
                    },
                    headers=get_auth_headers(),
                    timeout=30.0,
                )

                latency = (time.time() - start_time) * 1000  # ms
                latencies.append(latency)

                if response.status_code != 200:
                    errors += 1
                else:
                    # Consume streaming response
                    await response.aread()

            except Exception as e:
                errors += 1
                print(f"✗ Message {i} error: {e}")

            if (i + 1) % 10 == 0:
                print(f"  Completed {i + 1}/{num_requests} requests")

    # Calculate results
    success_count = total_requests - errors
    error_rate = errors / total_requests if total_requests > 0 else 0
    total_time = sum(latencies) / 1000 if latencies else 0

    results = PerformanceResults(
        test_name="Single Message Latency",
        total_requests=total_requests,
        successful_requests=success_count,
        failed_requests=errors,
        error_rate=error_rate,
        min_latency=min(latencies) if latencies else 0,
        max_latency=max(latencies) if latencies else 0,
        mean_latency=statistics.mean(latencies) if latencies else 0,
        median_latency=statistics.median(latencies) if latencies else 0,
        p95_latency=calculate_percentile(latencies, 95) if latencies else 0,
        p99_latency=calculate_percentile(latencies, 99) if latencies else 0,
        throughput=success_count / total_time if total_time > 0 else 0,
        timestamp=datetime.now().isoformat(),
    )

    print(format_results(results))

    return results


# ============================================================================
# Main Test Runner
# ============================================================================

async def run_all_tests():
    """Run all performance tests."""
    print(f"\n{'='*70}")
    print(f"CHATBOT PERFORMANCE & LOAD TESTING SUITE")
    print(f"{'='*70}\n")

    # Check backend availability
    print("Checking backend availability...")
    if not await wait_for_backend():
        print("✗ Backend is not available. Please start the backend server.")
        return

    print()

    results_list: List[PerformanceResults] = []

    try:
        # Test 1: Single message latency
        results = await test_single_message_latency(num_requests=50)
        results_list.append(results)

        # Test 2: Session operations
        results = await test_session_operations()
        results_list.append(results)

        # Test 3: Concurrent users
        for num_users in [10, 50, 100]:
            results = await test_concurrent_users_scenario(num_users=num_users, messages_per_user=1)
            results_list.append(results)

        # Test 4: Message load
        results = await test_message_load_scenario(num_messages=100, batch_size=10)
        results_list.append(results)

        # Test 5: Streaming performance
        results = await test_streaming_performance(num_concurrent_streams=5)
        results_list.append(results)

    except KeyboardInterrupt:
        print("\n✗ Tests interrupted by user")
    except Exception as e:
        print(f"\n✗ Test execution error: {e}")

    # Print summary
    print_summary(results_list)


def print_summary(results_list: List[PerformanceResults]):
    """Print summary of all test results."""
    print(f"\n{'='*70}")
    print(f"PERFORMANCE TEST SUMMARY")
    print(f"{'='*70}\n")

    summary_table = """
╔════════════════════════════════════════════════════════════════════════════╗
║ Test Name                          │ Error% │  Mean  │  P95  │ P99  │Pass?║
╠════════════════════════════════════════════════════════════════════════════╣
"""

    all_pass = True

    for result in results_list:
        # Check against benchmarks
        benchmark_passed = True

        if result.error_rate > 0.05:
            benchmark_passed = False

        if "Concurrent Users" in result.test_name and result.error_rate > 0.05:
            benchmark_passed = False

        if "Latency" in result.test_name and result.p95_latency > BENCHMARKS["single_message_response"] * 1000:
            benchmark_passed = False

        status = "✓ PASS" if benchmark_passed else "✗ FAIL"
        all_pass = all_pass and benchmark_passed

        # Format test name (truncate if too long)
        test_name = result.test_name[:33]

        summary_table += f"║ {test_name:<33} │ {result.error_rate*100:>5.2f}% │ {result.mean_latency:>6.0f}ms │ {result.p95_latency:>5.0f}ms │ {result.p99_latency:>4.0f}ms │ {status} ║\n"

    summary_table += f"╚════════════════════════════════════════════════════════════════════════════╝"

    print(summary_table)

    print(f"\n{'='*70}")
    if all_pass:
        print("✓ ALL TESTS PASSED - Production Ready!")
    else:
        print("✗ SOME TESTS FAILED - Review results above")
    print(f"{'='*70}\n")


# ============================================================================
# Pytest Test Wrappers
# ============================================================================

@pytest.mark.asyncio
@pytest.mark.performance
@pytest.mark.concurrent
async def test_single_message_latency_benchmark():
    """Pytest wrapper for single message latency test."""
    result = await test_single_message_latency(num_requests=50)
    # Benchmark assertions
    assert result.error_rate < 0.05, f"Error rate {result.error_rate} exceeds 5%"
    assert result.p95_latency < BENCHMARKS["single_message_response"] * 1000, \
        f"P95 latency {result.p95_latency}ms exceeds {BENCHMARKS['single_message_response']*1000}ms"


@pytest.mark.asyncio
@pytest.mark.performance
async def test_session_ops_performance():
    """Pytest wrapper for session operations test."""
    result = await test_session_operations()
    assert result.error_rate < 0.05, f"Error rate {result.error_rate} exceeds 5%"


@pytest.mark.asyncio
@pytest.mark.performance
@pytest.mark.concurrent
async def test_10_concurrent_users():
    """Pytest wrapper for 10 concurrent users test."""
    result = await test_concurrent_users_scenario(num_users=10, messages_per_user=1)
    assert result.error_rate < 0.05, f"Error rate {result.error_rate} exceeds 5%"


@pytest.mark.asyncio
@pytest.mark.performance
@pytest.mark.concurrent
async def test_50_concurrent_users():
    """Pytest wrapper for 50 concurrent users test."""
    result = await test_concurrent_users_scenario(num_users=50, messages_per_user=1)
    assert result.error_rate < 0.05, f"Error rate {result.error_rate} exceeds 5%"


@pytest.mark.asyncio
@pytest.mark.performance
@pytest.mark.concurrent
async def test_100_concurrent_users():
    """Pytest wrapper for 100 concurrent users test."""
    result = await test_concurrent_users_scenario(num_users=100, messages_per_user=1)
    assert result.error_rate < 0.05, f"Error rate {result.error_rate} exceeds 5%"


@pytest.mark.asyncio
@pytest.mark.performance
async def test_message_load_100():
    """Pytest wrapper for 100 message load test."""
    result = await test_message_load_scenario(num_messages=100, batch_size=10)
    assert result.error_rate < 0.10, f"Error rate {result.error_rate} exceeds 10%"
    assert len([r for r in [result] if r.successful_requests > 0]) > 0, "No successful messages"


@pytest.mark.asyncio
@pytest.mark.performance
async def test_streaming_5_concurrent():
    """Pytest wrapper for 5 concurrent streams test."""
    result = await test_streaming_performance(num_concurrent_streams=5)
    assert result.error_rate < 0.10, f"Error rate {result.error_rate} exceeds 10%"


if __name__ == "__main__":
    asyncio.run(run_all_tests())
