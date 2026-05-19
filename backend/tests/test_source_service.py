"""
Comprehensive tests for SourceService.
Tests cover: basic cases, hard cases, complex cases, and edge cases.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock

from app.services.source_service import SourceService
from app.repositories.news_source_repository import NewsSourceRepository
from app.core.exceptions import NotFoundError


@pytest.fixture
def mock_source_repo():
    """Mock NewsSourceRepository."""
    repo = AsyncMock(spec=NewsSourceRepository)
    return repo


@pytest.fixture
def source_service(mock_source_repo):
    """Create SourceService with mocked repository."""
    return SourceService(source_repo=mock_source_repo)


class TestSourceServiceListSources:
    """Tests for listing sources."""

    @pytest.mark.asyncio
    async def test_list_sources_basic_success(self, source_service, mock_source_repo):
        """BASIC: Successfully list all sources."""
        mock_source1 = MagicMock()
        mock_source1.source_id = "src-1"
        mock_source1.name = "Hacker News"
        mock_source1.url = "https://news.ycombinator.com"
        mock_source1.category = "technology"
        mock_source1.priority = 1
        mock_source1.enabled = True
        mock_source1.created_at = 1234567890

        mock_source2 = MagicMock()
        mock_source2.source_id = "src-2"
        mock_source2.name = "TechCrunch"
        mock_source2.url = "https://techcrunch.com"
        mock_source2.category = "technology"
        mock_source2.priority = 2
        mock_source2.enabled = True
        mock_source2.created_at = 1234567890

        mock_source_repo.list_all.return_value = [mock_source1, mock_source2]

        result = await source_service.list_sources()

        assert len(result) == 2
        assert result[0]["name"] == "Hacker News"
        assert result[1]["name"] == "TechCrunch"

    @pytest.mark.asyncio
    async def test_list_sources_empty(self, source_service, mock_source_repo):
        """EDGE: List sources when none exist."""
        mock_source_repo.list_all.return_value = []

        result = await source_service.list_sources()

        assert result == []

    @pytest.mark.asyncio
    async def test_list_sources_mixed_enabled_disabled(self, source_service, mock_source_repo):
        """HARD: List sources with both enabled and disabled sources."""
        mock_sources = [
            MagicMock(
                source_id=f"src-{i}",
                name=f"Source {i}",
                url=f"https://source{i}.com",
                category="tech",
                priority=i,
                enabled=(i % 2 == 0),
                created_at=1234567890,
            )
            for i in range(1, 6)
        ]

        mock_source_repo.list_all.return_value = mock_sources

        result = await source_service.list_sources()

        assert len(result) == 5
        enabled_count = sum(1 for s in result if s["enabled"])
        assert enabled_count == 2

    @pytest.mark.asyncio
    async def test_list_sources_response_structure(self, source_service, mock_source_repo):
        """COMPLEX: Verify list response has all required fields."""
        mock_source = MagicMock()
        mock_source.source_id = "src-1"
        mock_source.name = "Test Source"
        mock_source.url = "https://test.com"
        mock_source.category = "tech"
        mock_source.priority = 1
        mock_source.enabled = True
        mock_source.created_at = 1234567890

        mock_source_repo.list_all.return_value = [mock_source]

        result = await source_service.list_sources()

        assert len(result) == 1
        source = result[0]
        assert "source_id" in source
        assert "name" in source
        assert "url" in source
        assert "category" in source
        assert "priority" in source
        assert "enabled" in source
        assert "created_at" in source
        assert len(source) == 7

    @pytest.mark.asyncio
    async def test_list_sources_ordered_by_priority(self, source_service, mock_source_repo):
        """COMPLEX: Sources returned with various priority levels."""
        mock_sources = [
            MagicMock(
                source_id="src-1",
                name="High Priority",
                url="https://high.com",
                category="tech",
                priority=1,
                enabled=True,
                created_at=1234567890,
            ),
            MagicMock(
                source_id="src-2",
                name="Low Priority",
                url="https://low.com",
                category="tech",
                priority=100,
                enabled=True,
                created_at=1234567890,
            ),
            MagicMock(
                source_id="src-3",
                name="Medium Priority",
                url="https://medium.com",
                category="tech",
                priority=50,
                enabled=True,
                created_at=1234567890,
            ),
        ]

        mock_source_repo.list_all.return_value = mock_sources

        result = await source_service.list_sources()

        assert len(result) == 3
        assert result[0]["priority"] == 1
        assert result[2]["priority"] == 100


class TestSourceServiceGetSource:
    """Tests for getting a source."""

    @pytest.mark.asyncio
    async def test_get_source_basic_success(self, source_service, mock_source_repo):
        """BASIC: Successfully get a source by ID."""
        mock_source = MagicMock()
        mock_source.source_id = "src-1"
        mock_source.name = "Hacker News"
        mock_source.url = "https://news.ycombinator.com"
        mock_source.category = "technology"
        mock_source.priority = 1
        mock_source.enabled = True
        mock_source.created_at = 1234567890

        mock_source_repo.get_by_id.return_value = mock_source

        result = await source_service.get_source("src-1")

        assert result["source_id"] == "src-1"
        assert result["name"] == "Hacker News"
        mock_source_repo.get_by_id.assert_called_once_with("src-1")

    @pytest.mark.asyncio
    async def test_get_source_not_found(self, source_service, mock_source_repo):
        """EDGE: Get non-existent source raises NotFoundError."""
        mock_source_repo.get_by_id.return_value = None

        with pytest.raises(NotFoundError):
            await source_service.get_source("nonexistent-src")

    @pytest.mark.asyncio
    async def test_get_source_disabled_source(self, source_service, mock_source_repo):
        """HARD: Get a disabled source (should still return it)."""
        mock_source = MagicMock()
        mock_source.source_id = "src-1"
        mock_source.name = "Old Source"
        mock_source.url = "https://old.com"
        mock_source.category = "tech"
        mock_source.priority = 100
        mock_source.enabled = False
        mock_source.created_at = 1234567890

        mock_source_repo.get_by_id.return_value = mock_source

        result = await source_service.get_source("src-1")

        assert result["enabled"] is False

    @pytest.mark.asyncio
    async def test_get_source_response_structure(self, source_service, mock_source_repo):
        """COMPLEX: Verify get response has all required fields."""
        mock_source = MagicMock()
        mock_source.source_id = "src-1"
        mock_source.name = "Test Source"
        mock_source.url = "https://test.com"
        mock_source.category = "tech"
        mock_source.priority = 1
        mock_source.enabled = True
        mock_source.created_at = 1234567890

        mock_source_repo.get_by_id.return_value = mock_source

        result = await source_service.get_source("src-1")

        assert "source_id" in result
        assert "name" in result
        assert "url" in result
        assert "category" in result
        assert "priority" in result
        assert "enabled" in result
        assert "created_at" in result
        assert len(result) == 7

    @pytest.mark.asyncio
    async def test_get_source_uuid_id(self, source_service, mock_source_repo):
        """COMPLEX: Get source with UUID-format ID."""
        source_id = "550e8400-e29b-41d4-a716-446655440000"
        mock_source = MagicMock()
        mock_source.source_id = source_id
        mock_source.name = "UUID Source"
        mock_source.url = "https://uuid.com"
        mock_source.category = "tech"
        mock_source.priority = 1
        mock_source.enabled = True
        mock_source.created_at = 1234567890

        mock_source_repo.get_by_id.return_value = mock_source

        result = await source_service.get_source(source_id)

        assert result["source_id"] == source_id


class TestSourceServiceCreateSource:
    """Tests for creating a source."""

    @pytest.mark.asyncio
    async def test_create_source_basic_success(self, source_service, mock_source_repo):
        """BASIC: Successfully create a source."""
        mock_source = MagicMock()
        mock_source.source_id = "src-1"
        mock_source.name = "New Source"
        mock_source.url = "https://new.com"
        mock_source.category = "technology"
        mock_source.priority = 1
        mock_source.enabled = True
        mock_source.created_at = 1234567890

        mock_source_repo.create.return_value = mock_source

        result = await source_service.create_source({
            "name": "New Source",
            "url": "https://new.com",
            "category": "technology",
            "priority": 1,
            "enabled": True,
        })

        assert result["name"] == "New Source"
        assert result["url"] == "https://new.com"
        mock_source_repo.create.assert_called_once()

    @pytest.mark.asyncio
    async def test_create_source_disabled(self, source_service, mock_source_repo):
        """HARD: Create a disabled source."""
        mock_source = MagicMock()
        mock_source.source_id = "src-1"
        mock_source.name = "Disabled Source"
        mock_source.url = "https://disabled.com"
        mock_source.category = "tech"
        mock_source.priority = 50
        mock_source.enabled = False
        mock_source.created_at = 1234567890

        mock_source_repo.create.return_value = mock_source

        result = await source_service.create_source({
            "name": "Disabled Source",
            "url": "https://disabled.com",
            "category": "tech",
            "priority": 50,
            "enabled": False,
        })

        assert result["enabled"] is False

    @pytest.mark.asyncio
    async def test_create_source_with_special_characters(self, source_service, mock_source_repo):
        """COMPLEX: Create source with special characters in name."""
        name = "Tech & Code: C++ News (2024)"
        mock_source = MagicMock()
        mock_source.source_id = "src-1"
        mock_source.name = name
        mock_source.url = "https://special.com"
        mock_source.category = "tech"
        mock_source.priority = 1
        mock_source.enabled = True
        mock_source.created_at = 1234567890

        mock_source_repo.create.return_value = mock_source

        result = await source_service.create_source({
            "name": name,
            "url": "https://special.com",
            "category": "tech",
            "priority": 1,
            "enabled": True,
        })

        assert result["name"] == name

    @pytest.mark.asyncio
    async def test_create_source_response_structure(self, source_service, mock_source_repo):
        """COMPLEX: Verify create response has all required fields."""
        mock_source = MagicMock()
        mock_source.source_id = "src-1"
        mock_source.name = "Test Source"
        mock_source.url = "https://test.com"
        mock_source.category = "tech"
        mock_source.priority = 1
        mock_source.enabled = True
        mock_source.created_at = 1234567890

        mock_source_repo.create.return_value = mock_source

        result = await source_service.create_source({
            "name": "Test Source",
            "url": "https://test.com",
            "category": "tech",
            "priority": 1,
            "enabled": True,
        })

        assert "source_id" in result
        assert "name" in result
        assert "url" in result
        assert "category" in result
        assert "priority" in result
        assert "enabled" in result
        assert "created_at" in result
        assert len(result) == 7

    @pytest.mark.asyncio
    async def test_create_source_priority_range(self, source_service, mock_source_repo):
        """HARD: Create sources with various priority values."""
        priorities = [1, 10, 50, 100, 9999]

        async def mock_create(data):
            mock_source = MagicMock()
            mock_source.source_id = "src-1"
            mock_source.name = data["name"]
            mock_source.url = data["url"]
            mock_source.category = data["category"]
            mock_source.priority = data["priority"]
            mock_source.enabled = data["enabled"]
            mock_source.created_at = 1234567890
            return mock_source

        mock_source_repo.create.side_effect = mock_create

        for priority in priorities:
            result = await source_service.create_source({
                "name": f"Source {priority}",
                "url": "https://test.com",
                "category": "tech",
                "priority": priority,
                "enabled": True,
            })
            assert result["priority"] == priority
