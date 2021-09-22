import dataclasses
import logging
import logging.config
from typing import Optional, Type, TypeVar

import marshmallow
import yaml

from starkware.starkware_utils.validated_dataclass import ValidatedMarshmallowDataclass

logger = logging.getLogger(__name__)

TConfig = TypeVar("TConfig", bound="Config")


# General utilities.


def load_config(
    config_file_path: Optional[str] = None, load_logging_config: Optional[bool] = True
) -> dict:
    if config_file_path is None:
        config_file_path = "/config.yml"

    config = yaml.safe_load(open(config_file_path, "r"))
    if load_logging_config:
        logging.config.dictConfig(config.get("LOGGING", {}))

    return config


def fetch_application_config(global_config: dict) -> dict:
    return global_config.get("application", {})


def fetch_service_config(global_config: dict) -> dict:
    return fetch_application_config(global_config).get("config", {})


# Base class for config schemas.


class Config(ValidatedMarshmallowDataclass):
    @classmethod
    def load(cls: Type[TConfig], data: dict) -> TConfig:
        config_instance = super().load(data)
        log_fields(config=config_instance)
        return config_instance

    @marshmallow.post_dump
    def remove_none_values(self, data, many=False):
        return {key: value for key, value in data.items() if value is not None}


def log_fields(config: Config):
    for field in dataclasses.fields(config):
        logger.info(
            f"Initialized {field.name} configuration with value: {getattr(config, field.name)}"
        )
