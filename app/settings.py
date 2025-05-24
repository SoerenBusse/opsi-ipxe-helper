from typing import List, Annotated

from pydantic import BaseModel, AnyUrl, computed_field, IPvAnyAddress, AfterValidator, SecretStr, DirectoryPath
from pydantic_settings import BaseSettings, SettingsConfigDict, PydanticBaseSettingsSource, YamlConfigSettingsSource


def _validator_host_is_ip(value: AnyUrl):
    try:
        IPvAnyAddress(value.host)
    except ValueError:
        raise ValueError("Host of URL needs to be an ip-address")

    return value


class SchemaUrl(AnyUrl):
    @computed_field
    @property
    def without_scheme(self) -> str:
        return str(self).replace(self.scheme, "").replace("://", "")


class OpsiSettings(BaseModel):
    rpc_url: str
    username: str
    password: SecretStr
    depot: str
    domain: str
    netboot_efi_url: Annotated[AnyUrl, AfterValidator(_validator_host_is_ip)]


class ToolEntrySetting(BaseModel):
    key: str
    description: str
    url: SchemaUrl
    replace: bool = False
    require_login: bool = False

    @computed_field
    @property
    def url_scheme(self) -> str:
        return self.url.scheme

    @computed_field
    @property
    def url_without_scheme(self) -> str:
        return str(self.url).replace(self.url.scheme, "").replace("://", "")


class ToolsSettings(BaseModel):
    entries: List[ToolEntrySetting]


class IPxeSettings(BaseModel):
    external_address: SchemaUrl
    tools: ToolsSettings
    username: str
    password: SecretStr


class StaticDirectoriesSetting(BaseModel):
    public: DirectoryPath


class DirectoriesSettings(BaseSettings):
    static: StaticDirectoriesSetting


class Settings(BaseSettings):
    opsi: OpsiSettings
    ipxe: IPxeSettings
    directories: DirectoriesSettings
    model_config = SettingsConfigDict(yaml_file="config.yml")

    @classmethod
    def settings_customise_sources(
            cls,
            settings_cls: type[BaseSettings],
            init_settings: PydanticBaseSettingsSource,
            env_settings: PydanticBaseSettingsSource,
            dotenv_settings: PydanticBaseSettingsSource,
            file_secret_settings: PydanticBaseSettingsSource,
    ) -> tuple[PydanticBaseSettingsSource, ...]:
        return (YamlConfigSettingsSource(settings_cls),)
