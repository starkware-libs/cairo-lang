import marshmallow_dataclass

from starkware.starkware_utils.config_base import Config


@marshmallow_dataclass.dataclass
class GeneralConfigBase(Config):
    pass
