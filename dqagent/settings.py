from pathlib import Path

from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="DQ_", env_file=".env", extra="ignore")
    api_token: SecretStr = SecretStr("")
    diagnostic_token: SecretStr = SecretStr("")
    data_dir: Path = Path("data")
    source_url: SecretStr = SecretStr("")
    openai_api_key: SecretStr = SecretStr("")
    openai_model: str = ""

    def require_auth(self):
        tokens = [self.api_token.get_secret_value(), self.diagnostic_token.get_secret_value()]
        if any(len(t) < 32 for t in tokens) or tokens[0] == tokens[1]:
            raise ValueError("Generate two distinct tokens of at least 32 characters with dqagent init")
