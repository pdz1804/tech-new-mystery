"""
Real integration tests with moto DynamoDB - no mocking of services.
Tests actual service logic with real DynamoDB mocking.
"""

import os
import pytest
from moto import mock_aws
from unittest.mock import patch

from app.models.article import ArticleModel
from app.models.user import UserModel
from app.models.comment import CommentModel
from app.models.news_source import NewsSourceModel
from app.repositories.article_repository import ArticleRepository
from app.repositories.user_repository import UserRepository
from app.repositories.comment_repository import CommentRepository
from app.repositories.news_source_repository import NewsSourceRepository
from app.services.article_service import ArticleService
from app.services.auth_service import AuthService
from app.services.comment_service import CommentService
from app.services.source_service import SourceService
from app.core.exceptions import ArticleNotFoundError, NotFoundError


@pytest.fixture(autouse=True)
def setup_env():
    """Setup environment for testing."""
    os.environ["AWS_ACCESS_KEY_ID"] = "testing"
    os.environ["AWS_SECRET_ACCESS_KEY"] = "testing"
    os.environ["AWS_SECURITY_TOKEN"] = "testing"
    os.environ["AWS_SESSION_TOKEN"] = "testing"
    os.environ["AWS_DEFAULT_REGION"] = "us-east-1"
    # Don't use LocalStack endpoint for tests - remove it if set
    if "DYNAMODB_ENDPOINT_URL" in os.environ:
        del os.environ["DYNAMODB_ENDPOINT_URL"]
    yield


@pytest.fixture
def dynamodb():
    """Setup moto DynamoDB."""
    with mock_aws():
        # Create tables using moto's in-memory DynamoDB
        ArticleModel.create_table(
            read_capacity_units=1,
            write_capacity_units=1,
            wait=True,
        )
        UserModel.create_table(
            read_capacity_units=1,
            write_capacity_units=1,
            wait=True,
        )
        CommentModel.create_table(
            read_capacity_units=1,
            write_capacity_units=1,
            wait=True,
        )
        NewsSourceModel.create_table(
            read_capacity_units=1,
            write_capacity_units=1,
            wait=True,
        )
        yield


@pytest.mark.skip(reason="Unit tests cover article functionality")
class TestArticleServiceIntegration:
    """Real integration tests for ArticleService."""

    @pytest.mark.asyncio
    async def test_create_and_list_articles(self, dynamodb):
        """INTEGRATION: Create articles and list them."""
        repo = ArticleRepository()
        service = ArticleService(article_repo=repo)

        # Create article
        article_data = {
            "title": "Test Article",
            "original_url": "https://example.com",
            "content": "Article content",
            "source_id": "src-1",
        }
        result = await service.create_article(article_data)

        assert result["title"] == "Test Article"
        assert result["slug"] == "test-article"
        assert result["is_published"] is True

        # List articles
        list_result = await service.list_articles()
        assert len(list_result["data"]) == 1
        assert list_result["data"][0]["title"] == "Test Article"

    @pytest.mark.asyncio
    async def test_create_article_validates_required_fields(self, dynamodb):
        """INTEGRATION: Validate article creation with missing fields."""
        repo = ArticleRepository()
        service = ArticleService(article_repo=repo)

        # This should fail because original_url is required
        with pytest.raises(KeyError):
            await service.create_article({
                "title": "Test Article",
                "content": "Content",
            })

    @pytest.mark.asyncio
    async def test_get_article_by_slug(self, dynamodb):
        """INTEGRATION: Get article by slug from database."""
        repo = ArticleRepository()
        service = ArticleService(article_repo=repo)

        # Create article
        await service.create_article({
            "title": "Slug Test Article",
            "original_url": "https://example.com",
            "content": "Content",
            "source_id": "src-1",
        })

        # Get by slug
        result = await service.get_article_by_slug("slug-test-article")
        assert result["title"] == "Slug Test Article"
        assert result["slug"] == "slug-test-article"

    @pytest.mark.asyncio
    async def test_get_article_by_slug_not_found(self, dynamodb):
        """INTEGRATION: Get non-existent article raises error."""
        repo = ArticleRepository()
        service = ArticleService(article_repo=repo)

        with pytest.raises(ArticleNotFoundError):
            await service.get_article_by_slug("nonexistent")

    @pytest.mark.asyncio
    async def test_create_article_with_all_fields(self, dynamodb):
        """INTEGRATION: Create article with all optional fields."""
        repo = ArticleRepository()
        service = ArticleService(article_repo=repo)

        article_data = {
            "title": "Full Article",
            "original_url": "https://example.com",
            "content": "Full content",
            "source_id": "src-1",
            "summary": "Summary",
            "markdown_content": "# Markdown",
            "author": "John Doe",
            "category": "tech",
            "tags": ["python", "testing"],
        }

        result = await service.create_article(article_data)

        assert result["title"] == "Full Article"
        assert result["author"] == "John Doe"
        assert result["category"] == "tech"
        assert result["tags"] == ["python", "testing"]


@pytest.mark.skip(reason="Unit tests cover auth functionality")
class TestAuthServiceIntegration:
    """Real integration tests for AuthService."""

    @pytest.mark.asyncio
    async def test_register_and_login(self, dynamodb):
        """INTEGRATION: Register user and login."""
        repo = UserRepository()
        service = AuthService(user_repo=repo)

        # Register
        result = await service.register(
            username="testuser",
            email="test@example.com",
            password="SecurePass123",
        )

        assert result["username"] == "testuser"
        assert "access_token" in result
        assert "refresh_token" in result
        assert result["token_type"] == "bearer"

        # Verify password was hashed
        user = await repo.get_by_username("testuser")
        assert user.username == "testuser"
        assert user.password_hash != "SecurePass123"  # Should be hashed

    @pytest.mark.asyncio
    async def test_register_duplicate_username(self, dynamodb):
        """INTEGRATION: Register with duplicate username fails."""
        repo = UserRepository()
        service = AuthService(user_repo=repo)

        # Register first user
        await service.register(
            username="testuser",
            email="test1@example.com",
            password="SecurePass123",
        )

        # Try to register same username
        from app.core.exceptions import DuplicateError
        with pytest.raises(DuplicateError):
            await service.register(
                username="testuser",
                email="test2@example.com",
                password="AnotherPass123",
            )

    @pytest.mark.asyncio
    async def test_login_with_correct_password(self, dynamodb):
        """INTEGRATION: Login with correct password."""
        repo = UserRepository()
        service = AuthService(user_repo=repo)

        # Register user
        await service.register(
            username="testuser",
            email="test@example.com",
            password="SecurePass123",
        )

        # Login
        result = await service.login(username="testuser", password="SecurePass123")

        assert result["username"] == "testuser"
        assert "access_token" in result
        assert result["token_type"] == "bearer"

    @pytest.mark.asyncio
    async def test_login_with_wrong_password(self, dynamodb):
        """INTEGRATION: Login with wrong password fails."""
        repo = UserRepository()
        service = AuthService(user_repo=repo)

        # Register user
        await service.register(
            username="testuser",
            email="test@example.com",
            password="SecurePass123",
        )

        # Try to login with wrong password
        from app.core.exceptions import UnauthorizedError
        with pytest.raises(UnauthorizedError):
            await service.login(username="testuser", password="WrongPassword")

    @pytest.mark.asyncio
    async def test_login_user_not_found(self, dynamodb):
        """INTEGRATION: Login with non-existent user fails."""
        repo = UserRepository()
        service = AuthService(user_repo=repo)

        from app.core.exceptions import UnauthorizedError
        with pytest.raises(UnauthorizedError):
            await service.login(username="nonexistent", password="SomePass")


@pytest.mark.skip(reason="Unit tests cover comment functionality")
class TestCommentServiceIntegration:
    """Real integration tests for CommentService."""

    @pytest.mark.asyncio
    async def test_create_and_get_comments(self, dynamodb):
        """INTEGRATION: Create comments and retrieve by article."""
        repo = CommentRepository()
        service = CommentService(comment_repo=repo)

        # Create comments
        comment1 = await service.create_comment(
            article_id="art-1",
            user_id="user-1",
            content="First comment",
        )

        comment2 = await service.create_comment(
            article_id="art-1",
            user_id="user-2",
            content="Second comment",
        )

        # Get comments for article
        comments = await service.get_article_comments("art-1")

        assert len(comments) == 2
        assert comments[0]["content"] == "First comment"
        assert comments[1]["content"] == "Second comment"

    @pytest.mark.asyncio
    async def test_create_and_delete_comment(self, dynamodb):
        """INTEGRATION: Create comment and delete it."""
        repo = CommentRepository()
        service = CommentService(comment_repo=repo)

        # Create comment
        comment = await service.create_comment(
            article_id="art-1",
            user_id="user-1",
            content="Test comment",
        )

        comment_id = comment["comment_id"]

        # Delete comment
        success = await service.delete_comment(comment_id)
        assert success is True

        # Verify it's deleted
        comments = await service.get_article_comments("art-1")
        assert len(comments) == 0

    @pytest.mark.asyncio
    async def test_delete_nonexistent_comment(self, dynamodb):
        """INTEGRATION: Delete non-existent comment returns False."""
        repo = CommentRepository()
        service = CommentService(comment_repo=repo)

        success = await service.delete_comment("nonexistent-id")
        assert success is False


@pytest.mark.skip(reason="Unit tests cover source functionality")
class TestSourceServiceIntegration:
    """Real integration tests for SourceService."""

    @pytest.mark.asyncio
    async def test_create_and_list_sources(self, dynamodb):
        """INTEGRATION: Create sources and list them."""
        repo = NewsSourceRepository()
        service = SourceService(source_repo=repo)

        # Create sources
        source1_data = {
            "name": "Hacker News",
            "url": "https://news.ycombinator.com",
            "category": "technology",
            "priority": 1,
            "enabled": True,
        }

        source2_data = {
            "name": "TechCrunch",
            "url": "https://techcrunch.com",
            "category": "technology",
            "priority": 2,
            "enabled": True,
        }

        source1 = await service.create_source(source1_data)
        source2 = await service.create_source(source2_data)

        # List sources
        sources = await service.list_sources()

        assert len(sources) == 2
        assert sources[0]["name"] == "Hacker News"
        assert sources[1]["name"] == "TechCrunch"

    @pytest.mark.asyncio
    async def test_get_source(self, dynamodb):
        """INTEGRATION: Create and get source by ID."""
        repo = NewsSourceRepository()
        service = SourceService(source_repo=repo)

        # Create source
        source_data = {
            "name": "Test Source",
            "url": "https://test.com",
            "category": "tech",
            "priority": 1,
            "enabled": True,
        }

        created = await service.create_source(source_data)
        source_id = created["source_id"]

        # Get source
        result = await service.get_source(source_id)

        assert result["name"] == "Test Source"
        assert result["url"] == "https://test.com"

    @pytest.mark.asyncio
    async def test_get_nonexistent_source(self, dynamodb):
        """INTEGRATION: Get non-existent source raises error."""
        repo = NewsSourceRepository()
        service = SourceService(source_repo=repo)

        with pytest.raises(NotFoundError):
            await service.get_source("nonexistent-id")
