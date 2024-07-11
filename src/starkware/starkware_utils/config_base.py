import dataclasses
import logging
import logging.config
from importlib import import_module
from typing import Any, Optional, Type, TypeVar

import marshmallow
import yaml

from starkware.starkware_utils.validated_dataclass import ValidatedMarshmallowDataclass

logger = logging.getLogger(__name__)

TConfig = TypeVar("TConfig", bound="ConfigWithNone")


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


def get_object_by_path(path: str) -> Any:
    """
    Imports an object definition from a given path.
    Returns the object, not the instance!
    """
    parts = path.rsplit(".", 1)
    return getattr(import_module(parts[0]), parts[1])


# Base class for config schemas.


class ConfigWithNone(ValidatedMarshmallowDataclass):
    """
    The difference between Config and ConfigWithNone classes is that ConfigWithNone class does not
    remove None values when using dump.
    For example:
        @marshmallow_dataclass.dataclass(frozen=True)
        class WithNone(ConfigWithNone):
            a: Optional[int] = None
            b: int = 2

        @marshmallow_dataclass.dataclass(frozen=True)
        class WithoutNone(Config):
            a: Optional[int] = None
            b: int = 2

        WithNone().dumps() == '{"a": null, "b": 2}'

        WithoutNone().dumps() == '{"b": 2}'
    """

    @classmethod
    def load(cls: Type[TConfig], data: dict) -> TConfig:
        config_instance = super().load(data=data)
        log_fields(config=config_instance)
        return config_instance

    @classmethod
    def from_file(
        cls: Type[TConfig], config_file_path: str, load_logging_config: Optional[bool] = True
    ) -> TConfig:
        raw_config = load_config(
            config_file_path=config_file_path, load_logging_config=load_logging_config
        )
        return cls.load(data=raw_config)


class Config(ConfigWithNone):
    @marshmallow.post_dump
    def remove_none_values(self, data, many=False):
        return {key: value for key, value in data.items() if value is not None}


def log_fields(config: ConfigWithNone):
    for field in dataclasses.fields(config):
        logger.info(
            f"Initialized {field.name} configuration with value: {getattr(config, field.name)}"
        )
