import dataclasses
import re
from typing import Optional

import marshmallow.fields as mfields


class IntAsHex(mfields.Field):
    """
    A field that behaves like an integer, but serializes to hex string. Usually, this applies to
    field elements.
    """

    default_error_messages = {'invalid': 'Expected hex string, got: "{input}".'}

    def _serialize(self, value, attr, obj, **kwargs):
        if value is None:
            return None
        assert isinstance(value, int)
        return hex(value)

    def _deserialize(self, value, attr, data, **kwargs):
        if re.match('^0x[0-9a-f]+$', value) is None:
            self.fail('invalid', input=value)

        return int(value, 16)


@dataclasses.dataclass
class MemorySegmentAddresses:
    # Represents the address of the beginning of the memory segment.
    begin_addr: int

    # Represents the location of the segment pointer after the program is completed. This is not
    # the end of the segment. For example, for the program segment, it will point to the last
    # instruction executed, rather than the end of the program segment.
    stop_ptr: Optional[int]
