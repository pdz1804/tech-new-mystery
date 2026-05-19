"""Comment business logic service."""

from app.repositories.comment_repository import CommentRepository


class CommentService:
    """Comment service for business logic."""

    def __init__(self, comment_repo: CommentRepository) -> None:
        """Initialize service."""
        self._comment_repo = comment_repo

    async def get_article_comments(self, article_id: str, limit: int = 20) -> list[dict]:
        """Get comments for article."""
        comments = await self._comment_repo.get_by_article(article_id, limit=limit)
        return [
            {
                "comment_id": c.comment_id,
                "user_id": c.user_id,
                "content": c.content,
                "created_at": c.created_at,
            }
            for c in comments
        ]

    async def create_comment(self, article_id: str, user_id: str, content: str) -> dict:
        """Create a comment."""
        comment = await self._comment_repo.create(
            {
                "article_id": article_id,
                "user_id": user_id,
                "content": content,
            }
        )
        return {
            "comment_id": comment.comment_id,
            "user_id": comment.user_id,
            "content": comment.content,
            "created_at": comment.created_at,
        }

    async def delete_comment(self, comment_id: str) -> bool:
        """Delete a comment."""
        return await self._comment_repo.delete(comment_id)
