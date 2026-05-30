"""Manual test script for clustering configuration endpoints.

This script tests the clustering configuration endpoints with mocked DynamoDB.
Run with: python -m pytest tests/manual/test_clustering_config_manual.py -v -s
"""

import asyncio
from app.repositories.clustering_config_repository import ClusteringConfigRepository
from app.models.clustering import ClusteringParamsModel


async def test_repository_get_defaults():
    """Test getting default configuration."""
    print("\n[TEST] Getting default config...")
    repo = ClusteringConfigRepository()
    config = await repo.get_config()

    assert config["silhouette_weight"] == 0.5
    assert config["davies_bouldin_weight"] == 0.3
    assert config["calinski_harabasz_weight"] == 0.2
    assert config["quality_threshold"] == 0.6
    assert config["min_cluster_size"] == 5
    assert config["min_samples"] == 3
    print("  PASS: Default config loaded correctly")


async def test_repository_update():
    """Test updating configuration."""
    print("\n[TEST] Updating config...")
    repo = ClusteringConfigRepository()

    new_config = {
        "silhouette_weight": 0.6,
        "davies_bouldin_weight": 0.2,
        "calinski_harabasz_weight": 0.2,
        "quality_threshold": 0.7,
        "min_cluster_size": 8,
        "min_samples": 4,
    }

    updated = await repo.update_config(new_config)
    assert updated["silhouette_weight"] == 0.6
    assert updated["min_cluster_size"] == 8
    print("  PASS: Config updated successfully")


async def test_repository_reset():
    """Test resetting configuration."""
    print("\n[TEST] Resetting config...")
    repo = ClusteringConfigRepository()

    reset_config = await repo.reset_config()
    assert reset_config["silhouette_weight"] == 0.5
    assert reset_config["davies_bouldin_weight"] == 0.3
    assert reset_config["calinski_harabasz_weight"] == 0.2
    print("  PASS: Config reset successfully")


async def test_validation_weights_sum():
    """Test weight sum validation."""
    print("\n[TEST] Validating weight sum...")
    repo = ClusteringConfigRepository()

    # Valid weights
    try:
        result = repo._validate_and_normalize({
            "silhouette_weight": 0.5,
            "davies_bouldin_weight": 0.3,
            "calinski_harabasz_weight": 0.2,
            "quality_threshold": 0.6,
            "min_cluster_size": 5,
            "min_samples": 3,
        })
        assert result is not None
        print("  PASS: Valid weights accepted")
    except ValueError as e:
        raise AssertionError(f"Should have accepted valid weights: {e}")

    # Invalid weights
    try:
        repo._validate_and_normalize({
            "silhouette_weight": 0.7,
            "davies_bouldin_weight": 0.2,
            "calinski_harabasz_weight": 0.2,
            "quality_threshold": 0.6,
            "min_cluster_size": 5,
            "min_samples": 3,
        })
        raise AssertionError("Should have rejected invalid weights")
    except ValueError as e:
        assert "sum to 1.0" in str(e)
        print("  PASS: Invalid weights rejected")


async def test_validation_bounds():
    """Test parameter bounds validation."""
    print("\n[TEST] Validating parameter bounds...")
    repo = ClusteringConfigRepository()

    # Test min_cluster_size bounds
    for invalid_size in [2, 101]:
        try:
            repo._validate_and_normalize({
                "silhouette_weight": 0.5,
                "davies_bouldin_weight": 0.3,
                "calinski_harabasz_weight": 0.2,
                "quality_threshold": 0.6,
                "min_cluster_size": invalid_size,
                "min_samples": 3,
            })
            raise AssertionError(f"Should have rejected min_cluster_size={invalid_size}")
        except ValueError as e:
            assert "min_cluster_size" in str(e)

    # Test min_samples bounds
    for invalid_samples in [0, 21]:
        try:
            repo._validate_and_normalize({
                "silhouette_weight": 0.5,
                "davies_bouldin_weight": 0.3,
                "calinski_harabasz_weight": 0.2,
                "quality_threshold": 0.6,
                "min_cluster_size": 5,
                "min_samples": invalid_samples,
            })
            raise AssertionError(f"Should have rejected min_samples={invalid_samples}")
        except ValueError as e:
            assert "min_samples" in str(e)

    print("  PASS: All bounds validated correctly")


async def test_validation_quality_threshold():
    """Test quality threshold validation."""
    print("\n[TEST] Validating quality threshold...")
    repo = ClusteringConfigRepository()

    # Test valid threshold
    result = repo._validate_and_normalize({
        "silhouette_weight": 0.5,
        "davies_bouldin_weight": 0.3,
        "calinski_harabasz_weight": 0.2,
        "quality_threshold": 0.0,
        "min_cluster_size": 5,
        "min_samples": 3,
    })
    assert result["quality_threshold"] == 0.0
    print("  PASS: Threshold 0.0 accepted")

    result = repo._validate_and_normalize({
        "silhouette_weight": 0.5,
        "davies_bouldin_weight": 0.3,
        "calinski_harabasz_weight": 0.2,
        "quality_threshold": 1.0,
        "min_cluster_size": 5,
        "min_samples": 3,
    })
    assert result["quality_threshold"] == 1.0
    print("  PASS: Threshold 1.0 accepted")

    # Test invalid thresholds
    try:
        repo._validate_and_normalize({
            "silhouette_weight": 0.5,
            "davies_bouldin_weight": 0.3,
            "calinski_harabasz_weight": 0.2,
            "quality_threshold": 1.5,
            "min_cluster_size": 5,
            "min_samples": 3,
        })
        raise AssertionError("Should have rejected quality_threshold=1.5")
    except ValueError as e:
        assert "quality_threshold" in str(e)
        print("  PASS: Threshold 1.5 rejected")


async def main():
    """Run all manual tests."""
    print("\n" + "=" * 60)
    print("CLUSTERING CONFIG MANUAL TESTS")
    print("=" * 60)

    try:
        await test_repository_get_defaults()
        await test_repository_update()
        await test_repository_reset()
        await test_validation_weights_sum()
        await test_validation_bounds()
        await test_validation_quality_threshold()

        print("\n" + "=" * 60)
        print("ALL TESTS PASSED")
        print("=" * 60)
    except Exception as e:
        print(f"\nTEST FAILED: {e}")
        raise


if __name__ == "__main__":
    asyncio.run(main())
