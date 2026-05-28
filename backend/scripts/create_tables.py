"""Script to create DynamoDB tables using PynamoDB."""

from app.models.user import UserModel
from app.models.article import ArticleModel
from app.models.news_source import NewsSourceModel
from app.models.comment import CommentModel
from app.models.submission import SubmissionModel
from app.models.user_saves import UserSavesModel
from app.models.user_preferences import UserPreferencesModel
from app.models.trending_article import TrendingArticleModel
from app.models.article_embedding import ArticleEmbeddingModel


def create_tables() -> None:
    """Create all DynamoDB tables."""
    models = [
        UserModel,
        ArticleModel,
        NewsSourceModel,
        CommentModel,
        SubmissionModel,
        UserSavesModel,
        UserPreferencesModel,
        TrendingArticleModel,
        ArticleEmbeddingModel,
    ]

    for model in models:
        if not model.exists():
            print(f"Creating table: {model.Meta.table_name}")
            model.create_table(wait=True)
        else:
            print(f"Table already exists: {model.Meta.table_name}")


if __name__ == "__main__":
    create_tables()
    print("All tables created successfully!")
