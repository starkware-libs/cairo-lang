import marshmallow_dataclass

from services.config.general_config import GeneralConfigBase


@marshmallow_dataclass.dataclass
class EverestGeneralConfig(GeneralConfigBase):
    pass
