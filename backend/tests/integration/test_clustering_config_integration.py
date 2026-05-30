"""Integration tests for clustering configuration endpoints with mocked DynamoDB."""

import pytest
from app.models.clustering import ClusteringParamsModel


@pytest.fixture(scope="function", autouse=True)
def setup_clustering_tables(mock_ddb):
    """Set up clustering tables for integration tests."""
    # Create tables in mocked DynamoDB
    ClusteringParamsModel.create_table(wait=True)


class TestClusteringConfigEndpointsIntegration:
    """Integration tests for clustering config endpoints."""

    def test_get_config_defaults(self, client):
        """Test getting default configuration when none exists."""
        from app.core.security import create_access_token

        token = create_access_token(
            data={
                "sub": "test-admin-user",
                "is_admin": True,
                "email": "admin@test.com",
            }
        )

        response = client.get(
            "/v1/admin/clustering/config",
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == 200
        data = response.json()

        # Should return defaults
        assert data["silhouette_weight"] == 0.5
        assert data["davies_bouldin_weight"] == 0.3
        assert data["calinski_harabasz_weight"] == 0.2
        assert data["min_cluster_size"] == 5
        assert data["min_samples"] == 3
        assert data["quality_threshold"] == 0.6
        assert "last_updated" in data

    def test_get_config_requires_admin(self, client):
        """Test that GET config requires admin role."""
        from app.core.security import create_access_token

        # Create non-admin token
        token = create_access_token(
            data={
                "sub": "test-user",
                "is_admin": False,
                "email": "user@test.com",
            }
        )

        response = client.get(
            "/v1/admin/clustering/config",
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == 403

    def test_update_config_valid(self, client):
        """Test updating configuration with valid values."""
        from app.core.security import create_access_token

        token = create_access_token(
            data={
                "sub": "test-admin-user",
                "is_admin": True,
                "email": "admin@test.com",
            }
        )

        update_payload = {
            "silhouette_weight": 0.6,
            "davies_bouldin_weight": 0.2,
            "calinski_harabasz_weight": 0.2,
            "quality_threshold": 0.7,
            "min_cluster_size": 8,
            "min_samples": 4,
        }

        response = client.put(
            "/v1/admin/clustering/config",
            json=update_payload,
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == 200
        data = response.json()

        assert data["silhouette_weight"] == 0.6
        assert data["davies_bouldin_weight"] == 0.2
        assert data["calinski_harabasz_weight"] == 0.2
        assert data["quality_threshold"] == 0.7
        assert data["min_cluster_size"] == 8
        assert data["min_samples"] == 4

    def test_update_config_invalid_weight_sum(self, client):
        """Test that invalid weight sums are rejected."""
        from app.core.security import create_access_token

        token = create_access_token(
            data={
                "sub": "test-admin-user",
                "is_admin": True,
                "email": "admin@test.com",
            }
        )

        update_payload = {
            "silhouette_weight": 0.7,  # Sum will be 1.2, invalid
            "davies_bouldin_weight": 0.3,
            "calinski_harabasz_weight": 0.2,
            "quality_threshold": 0.6,
            "min_cluster_size": 5,
            "min_samples": 3,
        }

        response = client.put(
            "/v1/admin/clustering/config",
            json=update_payload,
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == 400
        assert "sum to 1.0" in response.json()["detail"]

    def test_update_config_weight_out_of_bounds(self, client):
        """Test that out-of-bounds weights are rejected."""
        from app.core.security import create_access_token

        token = create_access_token(
            data={
                "sub": "test-admin-user",
                "is_admin": True,
                "email": "admin@test.com",
            }
        )

        update_payload = {
            "silhouette_weight": 1.5,  # > 1.0
            "davies_bouldin_weight": 0.0,
            "calinski_harabasz_weight": -0.5,  # Negative
            "quality_threshold": 0.6,
            "min_cluster_size": 5,
            "min_samples": 3,
        }

        response = client.put(
            "/v1/admin/clustering/config",
            json=update_payload,
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == 400

    def test_update_config_quality_threshold_bounds(self, client):
        """Test quality threshold bounds validation."""
        from app.core.security import create_access_token

        token = create_access_token(
            data={
                "sub": "test-admin-user",
                "is_admin": True,
                "email": "admin@test.com",
            }
        )

        # Too high
        update_payload = {
            "silhouette_weight": 0.5,
            "davies_bouldin_weight": 0.3,
            "calinski_harabasz_weight": 0.2,
            "quality_threshold": 1.5,  # Invalid
            "min_cluster_size": 5,
            "min_samples": 3,
        }

        response = client.put(
            "/v1/admin/clustering/config",
            json=update_payload,
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == 400
        assert "quality_threshold" in response.json()["detail"]

    def test_update_config_min_cluster_size_bounds(self, client):
        """Test min_cluster_size bounds validation."""
        from app.core.security import create_access_token

        token = create_access_token(
            data={
                "sub": "test-admin-user",
                "is_admin": True,
                "email": "admin@test.com",
            }
        )

        # Too small
        update_payload = {
            "silhouette_weight": 0.5,
            "davies_bouldin_weight": 0.3,
            "calinski_harabasz_weight": 0.2,
            "quality_threshold": 0.6,
            "min_cluster_size": 2,  # < 3
            "min_samples": 3,
        }

        response = client.put(
            "/v1/admin/clustering/config",
            json=update_payload,
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == 400
        assert "min_cluster_size" in response.json()["detail"]

    def test_update_config_min_samples_bounds(self, client):
        """Test min_samples bounds validation."""
        from app.core.security import create_access_token

        token = create_access_token(
            data={
                "sub": "test-admin-user",
                "is_admin": True,
                "email": "admin@test.com",
            }
        )

        # Too small
        update_payload = {
            "silhouette_weight": 0.5,
            "davies_bouldin_weight": 0.3,
            "calinski_harabasz_weight": 0.2,
            "quality_threshold": 0.6,
            "min_cluster_size": 5,
            "min_samples": 0,  # < 1
        }

        response = client.put(
            "/v1/admin/clustering/config",
            json=update_payload,
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == 400
        assert "min_samples" in response.json()["detail"]

    def test_update_and_retrieve(self, client):
        """Test updating config and then retrieving it."""
        from app.core.security import create_access_token

        token = create_access_token(
            data={
                "sub": "test-admin-user",
                "is_admin": True,
                "email": "admin@test.com",
            }
        )

        # Update
        update_payload = {
            "silhouette_weight": 0.4,
            "davies_bouldin_weight": 0.4,
            "calinski_harabasz_weight": 0.2,
            "quality_threshold": 0.5,
            "min_cluster_size": 10,
            "min_samples": 5,
        }

        response = client.put(
            "/v1/admin/clustering/config",
            json=update_payload,
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 200

        # Retrieve and verify
        response = client.get(
            "/v1/admin/clustering/config",
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["silhouette_weight"] == 0.4
        assert data["davies_bouldin_weight"] == 0.4
        assert data["calinski_harabasz_weight"] == 0.2
        assert data["quality_threshold"] == 0.5
        assert data["min_cluster_size"] == 10
        assert data["min_samples"] == 5

    def test_reset_config(self, client):
        """Test resetting configuration to defaults."""
        from app.core.security import create_access_token

        token = create_access_token(
            data={
                "sub": "test-admin-user",
                "is_admin": True,
                "email": "admin@test.com",
            }
        )

        # First update to non-default
        update_payload = {
            "silhouette_weight": 0.7,
            "davies_bouldin_weight": 0.2,
            "calinski_harabasz_weight": 0.1,
            "quality_threshold": 0.8,
            "min_cluster_size": 20,
            "min_samples": 10,
        }

        response = client.put(
            "/v1/admin/clustering/config",
            json=update_payload,
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 200

        # Reset
        response = client.post(
            "/v1/admin/clustering/config/reset",
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == 200
        data = response.json()

        # Check defaults restored
        assert data["silhouette_weight"] == 0.5
        assert data["davies_bouldin_weight"] == 0.3
        assert data["calinski_harabasz_weight"] == 0.2
        assert data["quality_threshold"] == 0.6
        assert data["min_cluster_size"] == 5
        assert data["min_samples"] == 3

    def test_reset_config_requires_admin(self, client):
        """Test that reset requires admin role."""
        from app.core.security import create_access_token

        # Non-admin token
        token = create_access_token(
            data={
                "sub": "test-user",
                "is_admin": False,
                "email": "user@test.com",
            }
        )

        response = client.post(
            "/v1/admin/clustering/config/reset",
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == 403

    def test_update_config_requires_admin(self, client):
        """Test that update requires admin role."""
        from app.core.security import create_access_token

        # Non-admin token
        token = create_access_token(
            data={
                "sub": "test-user",
                "is_admin": False,
                "email": "user@test.com",
            }
        )

        update_payload = {
            "silhouette_weight": 0.5,
            "davies_bouldin_weight": 0.3,
            "calinski_harabasz_weight": 0.2,
            "quality_threshold": 0.6,
            "min_cluster_size": 5,
            "min_samples": 3,
        }

        response = client.put(
            "/v1/admin/clustering/config",
            json=update_payload,
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == 403

    def test_weight_normalization_with_equal_weights(self, client):
        """Test weight normalization with equal distribution."""
        from app.core.security import create_access_token

        token = create_access_token(
            data={
                "sub": "test-admin-user",
                "is_admin": True,
                "email": "admin@test.com",
            }
        )

        update_payload = {
            "silhouette_weight": 0.333333,
            "davies_bouldin_weight": 0.333333,
            "calinski_harabasz_weight": 0.333334,
            "quality_threshold": 0.6,
            "min_cluster_size": 5,
            "min_samples": 3,
        }

        response = client.put(
            "/v1/admin/clustering/config",
            json=update_payload,
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == 200
        data = response.json()

        # Verify weights sum to 1.0
        weight_sum = (
            data["silhouette_weight"]
            + data["davies_bouldin_weight"]
            + data["calinski_harabasz_weight"]
        )
        assert abs(weight_sum - 1.0) < 0.001

    def test_multiple_updates_overwrite(self, client):
        """Test that multiple updates overwrite previous values."""
        from app.core.security import create_access_token

        token = create_access_token(
            data={
                "sub": "test-admin-user",
                "is_admin": True,
                "email": "admin@test.com",
            }
        )

        # First update
        update_payload = {
            "silhouette_weight": 0.6,
            "davies_bouldin_weight": 0.2,
            "calinski_harabasz_weight": 0.2,
            "quality_threshold": 0.7,
            "min_cluster_size": 8,
            "min_samples": 4,
        }

        response = client.put(
            "/v1/admin/clustering/config",
            json=update_payload,
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 200

        # Second update
        update_payload = {
            "silhouette_weight": 0.4,
            "davies_bouldin_weight": 0.4,
            "calinski_harabasz_weight": 0.2,
            "quality_threshold": 0.5,
            "min_cluster_size": 10,
            "min_samples": 5,
        }

        response = client.put(
            "/v1/admin/clustering/config",
            json=update_payload,
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 200

        # Retrieve and verify second update was applied
        response = client.get(
            "/v1/admin/clustering/config",
            headers={"Authorization": f"Bearer {token}"},
        )

        data = response.json()
        assert data["silhouette_weight"] == 0.4
        assert data["quality_threshold"] == 0.5
