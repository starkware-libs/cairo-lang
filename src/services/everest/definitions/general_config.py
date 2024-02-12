import marshmallow_dataclass

from services.config.general_config import GeneralConfigBase


@marshmallow_dataclass.dataclass(frozen=True)
class EverestGeneralConfig(GeneralConfigBase):
    pass
