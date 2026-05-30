"""Unit tests for clustering configuration repository."""

import pytest
from app.repositories.clustering_config_repository import ClusteringConfigRepository


class TestClusteringConfigRepositoryValidation:
    """Tests for configuration validation."""

    def test_validate_default_weights(self):
        """Test that default weights pass validation."""
        config = {
            "silhouette_weight": 0.5,
            "davies_bouldin_weight": 0.3,
            "calinski_harabasz_weight": 0.2,
            "quality_threshold": 0.6,
            "min_cluster_size": 5,
            "min_samples": 3,
        }
        result = ClusteringConfigRepository._validate_and_normalize(config)
        assert result["silhouette_weight"] == 0.5
        assert result["davies_bouldin_weight"] == 0.3
        assert result["calinski_harabasz_weight"] == 0.2

    def test_validate_weights_sum_to_one(self):
        """Test validation that weights sum to 1.0."""
        config = {
            "silhouette_weight": 0.6,
            "davies_bouldin_weight": 0.2,
            "calinski_harabasz_weight": 0.2,
            "quality_threshold": 0.6,
            "min_cluster_size": 5,
            "min_samples": 3,
        }
        result = ClusteringConfigRepository._validate_and_normalize(config)
        assert abs(
            result["silhouette_weight"]
            + result["davies_bouldin_weight"]
            + result["calinski_harabasz_weight"]
            - 1.0
        ) < 0.01

    def test_validate_weights_sum_invalid(self):
        """Test that invalid weight sums raise ValueError."""
        config = {
            "silhouette_weight": 0.7,
            "davies_bouldin_weight": 0.2,
            "calinski_harabasz_weight": 0.2,  # Sum = 1.1, invalid
            "quality_threshold": 0.6,
            "min_cluster_size": 5,
            "min_samples": 3,
        }
        with pytest.raises(ValueError, match="weights must sum to 1.0"):
            ClusteringConfigRepository._validate_and_normalize(config)

    def test_validate_individual_weight_bounds(self):
        """Test individual weight bounds validation."""
        # Test silhouette_weight too high
        config = {
            "silhouette_weight": 1.5,  # Invalid
            "davies_bouldin_weight": 0.0,
            "calinski_harabasz_weight": 0.0,
            "quality_threshold": 0.6,
            "min_cluster_size": 5,
            "min_samples": 3,
        }
        with pytest.raises(ValueError, match="silhouette_weight must be between"):
            ClusteringConfigRepository._validate_and_normalize(config)

        # Test negative weight
        config = {
            "silhouette_weight": -0.1,  # Invalid
            "davies_bouldin_weight": 0.5,
            "calinski_harabasz_weight": 0.6,
            "quality_threshold": 0.6,
            "min_cluster_size": 5,
            "min_samples": 3,
        }
        with pytest.raises(ValueError, match="silhouette_weight must be between"):
            ClusteringConfigRepository._validate_and_normalize(config)

    def test_validate_quality_threshold_bounds(self):
        """Test quality threshold bounds validation."""
        # Too high
        config = {
            "silhouette_weight": 0.5,
            "davies_bouldin_weight": 0.3,
            "calinski_harabasz_weight": 0.2,
            "quality_threshold": 1.5,  # Invalid
            "min_cluster_size": 5,
            "min_samples": 3,
        }
        with pytest.raises(ValueError, match="quality_threshold must be between"):
            ClusteringConfigRepository._validate_and_normalize(config)

        # Negative
        config["quality_threshold"] = -0.1
        with pytest.raises(ValueError, match="quality_threshold must be between"):
            ClusteringConfigRepository._validate_and_normalize(config)

    def test_validate_min_cluster_size_bounds(self):
        """Test min_cluster_size bounds validation."""
        # Too small
        config = {
            "silhouette_weight": 0.5,
            "davies_bouldin_weight": 0.3,
            "calinski_harabasz_weight": 0.2,
            "quality_threshold": 0.6,
            "min_cluster_size": 2,  # Invalid, < 3
            "min_samples": 3,
        }
        with pytest.raises(ValueError, match="min_cluster_size must be between"):
            ClusteringConfigRepository._validate_and_normalize(config)

        # Too large
        config["min_cluster_size"] = 101
        with pytest.raises(ValueError, match="min_cluster_size must be between"):
            ClusteringConfigRepository._validate_and_normalize(config)

    def test_validate_min_samples_bounds(self):
        """Test min_samples bounds validation."""
        # Too small
        config = {
            "silhouette_weight": 0.5,
            "davies_bouldin_weight": 0.3,
            "calinski_harabasz_weight": 0.2,
            "quality_threshold": 0.6,
            "min_cluster_size": 5,
            "min_samples": 0,  # Invalid, < 1
        }
        with pytest.raises(ValueError, match="min_samples must be between"):
            ClusteringConfigRepository._validate_and_normalize(config)

        # Too large
        config["min_samples"] = 21
        with pytest.raises(ValueError, match="min_samples must be between"):
            ClusteringConfigRepository._validate_and_normalize(config)

    def test_validate_with_tolerance(self):
        """Test that validation allows 1% tolerance on weight sum."""
        # Sum = 1.005 (within 1% tolerance)
        config = {
            "silhouette_weight": 0.5025,
            "davies_bouldin_weight": 0.3,
            "calinski_harabasz_weight": 0.2,
            "quality_threshold": 0.6,
            "min_cluster_size": 5,
            "min_samples": 3,
        }
        result = ClusteringConfigRepository._validate_and_normalize(config)
        assert result is not None

    def test_validate_type_conversion(self):
        """Test that validation converts string inputs to correct types."""
        config = {
            "silhouette_weight": "0.5",  # String
            "davies_bouldin_weight": "0.3",
            "calinski_harabasz_weight": "0.2",
            "quality_threshold": "0.6",
            "min_cluster_size": "5",  # String
            "min_samples": "3",  # String
        }
        result = ClusteringConfigRepository._validate_and_normalize(config)
        assert isinstance(result["silhouette_weight"], float)
        assert isinstance(result["min_cluster_size"], int)

    def test_default_params_structure(self):
        """Test that default params have correct structure."""
        defaults = ClusteringConfigRepository._default_params()
        assert defaults["param_id"] == "default"
        assert defaults["silhouette_weight"] == 0.5
        assert defaults["davies_bouldin_weight"] == 0.3
        assert defaults["calinski_harabasz_weight"] == 0.2
        assert defaults["min_cluster_size"] == 5
        assert defaults["min_samples"] == 3
        assert defaults["quality_threshold"] == 0.6
        assert "last_updated" in defaults

    def test_normalize_edge_cases(self):
        """Test edge case values."""
        # All zeros for weights except one
        config = {
            "silhouette_weight": 1.0,
            "davies_bouldin_weight": 0.0,
            "calinski_harabasz_weight": 0.0,
            "quality_threshold": 0.0,
            "min_cluster_size": 3,
            "min_samples": 1,
        }
        result = ClusteringConfigRepository._validate_and_normalize(config)
        assert result["silhouette_weight"] == 1.0

    def test_normalize_equal_weights(self):
        """Test equal weight distribution."""
        config = {
            "silhouette_weight": 0.333333,
            "davies_bouldin_weight": 0.333333,
            "calinski_harabasz_weight": 0.333334,  # Accounts for floating point
            "quality_threshold": 0.6,
            "min_cluster_size": 5,
            "min_samples": 3,
        }
        result = ClusteringConfigRepository._validate_and_normalize(config)
        assert result is not None


class TestClusteringConfigRepositoryDefaults:
    """Tests for default values."""

    def test_default_weights_normalize(self):
        """Test that default weights normalize correctly."""
        defaults = ClusteringConfigRepository._default_params()
        weight_sum = (
            defaults["silhouette_weight"]
            + defaults["davies_bouldin_weight"]
            + defaults["calinski_harabasz_weight"]
        )
        assert abs(weight_sum - 1.0) < 0.01

    def test_defaults_within_bounds(self):
        """Test that all default values are within bounds."""
        defaults = ClusteringConfigRepository._default_params()

        # Check weights
        assert 0 <= defaults["silhouette_weight"] <= 1
        assert 0 <= defaults["davies_bouldin_weight"] <= 1
        assert 0 <= defaults["calinski_harabasz_weight"] <= 1

        # Check thresholds
        assert 0 <= defaults["quality_threshold"] <= 1

        # Check cluster parameters
        assert 3 <= defaults["min_cluster_size"] <= 100
        assert 1 <= defaults["min_samples"] <= 20
