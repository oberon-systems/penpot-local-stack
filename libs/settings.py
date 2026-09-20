"""Settings: defaults, .penpot.yaml in the working directory, then PENPOT_* variables."""

from pathlib import Path

from pydantic_settings import (
    BaseSettings,
    PydanticBaseSettingsSource,
    SettingsConfigDict,
    YamlConfigSettingsSource,
)

FILE = ".penpot.yaml"
WILDCARD = ("0.0.0.0", "::")  # noqa: S104


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="PENPOT_", yaml_file=FILE, extra="forbid")

    templates: Path = Path("templates")
    host: str = "127.0.0.1"
    port: int = 9001
    project: str = "penpot-local"
    version: str = "2.17.2"
    email: str = "designer@example.com"
    password: str = "penpot-local"  # noqa: S105

    @property
    def url(self) -> str:
        # A wildcard bind is still reached as localhost by the browser opened on this machine.
        host = "localhost" if self.host in (*WILDCARD, "127.0.0.1") else self.host
        return f"http://{host}:{self.port}"

    @classmethod
    def settings_customise_sources(
        cls,
        settings_cls: type[BaseSettings],
        init_settings: PydanticBaseSettingsSource,
        env_settings: PydanticBaseSettingsSource,
        dotenv_settings: PydanticBaseSettingsSource,
        file_secret_settings: PydanticBaseSettingsSource,
    ) -> tuple[PydanticBaseSettingsSource, ...]:
        return (init_settings, env_settings, YamlConfigSettingsSource(settings_cls))


def settings() -> Settings:
    return Settings()
