from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    notion_token: str | None = None
    notion_database_id: str | None = None

    # Notion database property names (create these in your Notion DB)
    notion_prop_title: str = "Name"
    notion_prop_source_url: str = "Source URL"
    notion_prop_description: str = "Description"
    notion_prop_industry: str = "Industry"
    notion_prop_location: str = "Location"
    notion_prop_emails: str = "Emails"
    notion_prop_phones: str = "Phones"
    notion_prop_social: str = "Social"
    notion_prop_funding: str = "Funding / size"
    notion_prop_coverage: str = "Coverage"
    notion_prop_scraped_at: str = "Scraped at"
    notion_prop_method: str = "Method"

    openai_api_key: str | None = None
    openai_model: str = "gpt-4o-mini"
    llm_coverage_threshold: float = 0.35

    http_user_agent: str = "CRM-SignalsBot/1.0 (+https://example.local)"
    http_timeout_seconds: float = 20.0


@lru_cache
def get_settings() -> Settings:
    return Settings()
