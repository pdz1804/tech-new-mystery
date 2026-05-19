"""Create DynamoDB tables using boto3 for AWS Infrastructure (Group D).

Tables created:
1. articles - article_id PK, slug GSI, with like_count and view_count fields
2. users - user_id PK, username GSI, with role field
3. user_saves - user_id+article_id composite key
4. user_likes - user_id+article_id composite key
5. comments - comment_id PK, article_id GSI
6. news_sources - source_id PK
7. user_preferences - user_id PK

Billing Mode: PAY_PER_REQUEST (on-demand)
Region: us-west-2
"""

import sys
import os

# Add backend directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import boto3
from app.config import settings

# Only pass endpoint_url if it's set (for LocalStack, not for real AWS)
dynamodb_kwargs = {
    'region_name': settings.aws_region,
}
if settings.dynamodb_endpoint_url:
    dynamodb_kwargs['endpoint_url'] = settings.dynamodb_endpoint_url

dynamodb = boto3.client('dynamodb', **dynamodb_kwargs)

# Table name helper with prefix
def table_name(name: str) -> str:
    """Get full table name with prefix."""
    return f"{settings.dynamodb_table_prefix}{name}"

def create_users_table():
    """Create users table with username GSI and role field."""
    try:
        dynamodb.create_table(
            TableName=table_name('users'),
            KeySchema=[
                {'AttributeName': 'user_id', 'KeyType': 'HASH'}
            ],
            AttributeDefinitions=[
                {'AttributeName': 'user_id', 'AttributeType': 'S'},
                {'AttributeName': 'username', 'AttributeType': 'S'}
            ],
            GlobalSecondaryIndexes=[
                {
                    'IndexName': 'username-index',
                    'KeySchema': [
                        {'AttributeName': 'username', 'KeyType': 'HASH'}
                    ],
                    'Projection': {'ProjectionType': 'ALL'}
                }
            ],
            BillingMode='PAY_PER_REQUEST'
        )
        print("[+] Created users table (email, username, password_hash, role, created_at, updated_at)")
    except dynamodb.exceptions.ResourceInUseException:
        print("[+] users table already exists")

def create_articles_table():
    """Create articles table with slug GSI, like_count, and view_count."""
    try:
        dynamodb.create_table(
            TableName=table_name('articles'),
            KeySchema=[
                {'AttributeName': 'article_id', 'KeyType': 'HASH'}
            ],
            AttributeDefinitions=[
                {'AttributeName': 'article_id', 'AttributeType': 'S'},
                {'AttributeName': 'slug', 'AttributeType': 'S'},
                {'AttributeName': 'source_id', 'AttributeType': 'S'},
                {'AttributeName': 'published_at', 'AttributeType': 'N'}
            ],
            GlobalSecondaryIndexes=[
                {
                    'IndexName': 'slug-index',
                    'KeySchema': [
                        {'AttributeName': 'slug', 'KeyType': 'HASH'}
                    ],
                    'Projection': {'ProjectionType': 'ALL'}
                },
                {
                    'IndexName': 'source-date-index',
                    'KeySchema': [
                        {'AttributeName': 'source_id', 'KeyType': 'HASH'},
                        {'AttributeName': 'published_at', 'KeyType': 'RANGE'}
                    ],
                    'Projection': {'ProjectionType': 'ALL'}
                }
            ],
            BillingMode='PAY_PER_REQUEST'
        )
        print("[+] Created articles table (title, content, summary, slug, source_id, published_at, like_count, view_count, created_at)")
    except dynamodb.exceptions.ResourceInUseException:
        print("[+] articles table already exists")

def create_trending_articles_table():
    """Create trending_articles table."""
    try:
        dynamodb.create_table(
            TableName=table_name('trending_articles'),
            KeySchema=[
                {'AttributeName': 'trending_id', 'KeyType': 'HASH'}
            ],
            AttributeDefinitions=[
                {'AttributeName': 'trending_id', 'AttributeType': 'S'}
            ],
            BillingMode='PAY_PER_REQUEST'
        )
        print("[+] Created trending_articles table")
    except dynamodb.exceptions.ResourceInUseException:
        print("[+] trending_articles table already exists")

def create_comments_table():
    """Create comments table with article_id GSI."""
    try:
        dynamodb.create_table(
            TableName=table_name('comments'),
            KeySchema=[
                {'AttributeName': 'comment_id', 'KeyType': 'HASH'}
            ],
            AttributeDefinitions=[
                {'AttributeName': 'comment_id', 'AttributeType': 'S'},
                {'AttributeName': 'article_id', 'AttributeType': 'S'},
                {'AttributeName': 'created_at', 'AttributeType': 'N'}
            ],
            GlobalSecondaryIndexes=[
                {
                    'IndexName': 'article-date-index',
                    'KeySchema': [
                        {'AttributeName': 'article_id', 'KeyType': 'HASH'},
                        {'AttributeName': 'created_at', 'KeyType': 'RANGE'}
                    ],
                    'Projection': {'ProjectionType': 'ALL'}
                }
            ],
            BillingMode='PAY_PER_REQUEST'
        )
        print("[+] Created comments table (user_id, article_id, content, created_at, updated_at)")
    except dynamodb.exceptions.ResourceInUseException:
        print("[+] comments table already exists")

def create_submissions_table():
    """Create submissions table with user_id GSI."""
    try:
        dynamodb.create_table(
            TableName=table_name('submissions'),
            KeySchema=[
                {'AttributeName': 'submission_id', 'KeyType': 'HASH'}
            ],
            AttributeDefinitions=[
                {'AttributeName': 'submission_id', 'AttributeType': 'S'},
                {'AttributeName': 'user_id', 'AttributeType': 'S'},
                {'AttributeName': 'submitted_at', 'AttributeType': 'N'}
            ],
            GlobalSecondaryIndexes=[
                {
                    'IndexName': 'user-date-index',
                    'KeySchema': [
                        {'AttributeName': 'user_id', 'KeyType': 'HASH'},
                        {'AttributeName': 'submitted_at', 'KeyType': 'RANGE'}
                    ],
                    'Projection': {'ProjectionType': 'ALL'}
                }
            ],
            BillingMode='PAY_PER_REQUEST'
        )
        print("[+] Created submissions table")
    except dynamodb.exceptions.ResourceInUseException:
        print("[+] submissions table already exists")

def create_user_saves_table():
    """Create user_saves table with composite key (user_id + article_id)."""
    try:
        dynamodb.create_table(
            TableName=table_name('user_saves'),
            KeySchema=[
                {'AttributeName': 'user_id', 'KeyType': 'HASH'},
                {'AttributeName': 'article_id', 'KeyType': 'RANGE'}
            ],
            AttributeDefinitions=[
                {'AttributeName': 'user_id', 'AttributeType': 'S'},
                {'AttributeName': 'article_id', 'AttributeType': 'S'}
            ],
            BillingMode='PAY_PER_REQUEST'
        )
        print("[+] Created user_saves table (saved_at, updated_at)")
    except dynamodb.exceptions.ResourceInUseException:
        print("[+] user_saves table already exists")

def create_user_likes_table():
    """Create user_likes table with composite key (user_id + article_id)."""
    try:
        dynamodb.create_table(
            TableName=table_name('user_likes'),
            KeySchema=[
                {'AttributeName': 'user_id', 'KeyType': 'HASH'},
                {'AttributeName': 'article_id', 'KeyType': 'RANGE'}
            ],
            AttributeDefinitions=[
                {'AttributeName': 'user_id', 'AttributeType': 'S'},
                {'AttributeName': 'article_id', 'AttributeType': 'S'}
            ],
            BillingMode='PAY_PER_REQUEST'
        )
        print("[+] Created user_likes table (liked_at)")
    except dynamodb.exceptions.ResourceInUseException:
        print("[+] user_likes table already exists")

def create_user_preferences_table():
    """Create user_preferences table."""
    try:
        dynamodb.create_table(
            TableName=table_name('user_preferences'),
            KeySchema=[
                {'AttributeName': 'user_id', 'KeyType': 'HASH'}
            ],
            AttributeDefinitions=[
                {'AttributeName': 'user_id', 'AttributeType': 'S'}
            ],
            BillingMode='PAY_PER_REQUEST'
        )
        print("[+] Created user_preferences table (preferred_categories, theme, notifications_enabled, updated_at)")
    except dynamodb.exceptions.ResourceInUseException:
        print("[+] user_preferences table already exists")

def create_news_sources_table():
    """Create news_sources table."""
    try:
        dynamodb.create_table(
            TableName=table_name('news_sources'),
            KeySchema=[
                {'AttributeName': 'source_id', 'KeyType': 'HASH'}
            ],
            AttributeDefinitions=[
                {'AttributeName': 'source_id', 'AttributeType': 'S'}
            ],
            BillingMode='PAY_PER_REQUEST'
        )
        print("[+] Created news_sources table (name, url, category, description, created_at)")
    except dynamodb.exceptions.ResourceInUseException:
        print("[+] news_sources table already exists")

def create_all_tables():
    """Create all DynamoDB tables for AWS infrastructure."""
    print("Creating DynamoDB tables using boto3 (us-west-2, PAY_PER_REQUEST)...")
    print("=" * 60)

    create_users_table()
    create_articles_table()
    create_comments_table()
    create_user_saves_table()
    create_user_likes_table()
    create_user_preferences_table()
    create_news_sources_table()
    create_trending_articles_table()
    create_submissions_table()

    print("=" * 60)
    print("\n[SUCCESS] All tables created successfully!")
    print("\nTable Summary:")
    print("  1. users - PK: user_id | GSI: username-index | Fields: role")
    print("  2. articles - PK: article_id | GSI: slug-index, source-date-index | Fields: like_count, view_count")
    print("  3. comments - PK: comment_id | GSI: article-date-index")
    print("  4. user_saves - PK: user_id + article_id")
    print("  5. user_likes - PK: user_id + article_id")
    print("  6. user_preferences - PK: user_id")
    print("  7. news_sources - PK: source_id")
    print("  8. trending_articles - PK: trending_id")
    print("  9. submissions - PK: submission_id | GSI: user-date-index")

if __name__ == "__main__":
    create_all_tables()
