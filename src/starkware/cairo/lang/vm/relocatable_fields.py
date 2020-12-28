import marshmallow.fields as mfields

from starkware.cairo.lang.vm.relocatable import RelocatableValue


class MaybeRelocatableField(mfields.Field):
    """
    A field that behaves like a MaybeRelocatable, but serializes to a tuple.
    See RelocatableValue.to_tuple() and RelocatableValue.from_tuple().
    """

    def _serialize(self, value, attr, obj, **kwargs):
        if value is None:
            return None
        return RelocatableValue.to_tuple(value)

    def _deserialize(self, value, attr, data, **kwargs):
        return RelocatableValue.from_tuple(value)


class MaybeRelocatableDictField(mfields.Field):
    """
    A field that behaves like a MaybeRelocatable dict, but MaybeRelocatable objects serialize to
    tuples. See RelocatableValue.to_tuple() and RelocatableValue.from_tuple().
    """

    def _serialize(self, value, attr, obj, **kwargs):
        if value is None:
            return None
        return [
            (RelocatableValue.to_tuple(x), RelocatableValue.to_tuple(y))
            for x, y in value.items()]

    def _deserialize(self, value, attr, data, **kwargs):
        return {
            RelocatableValue.from_tuple(x): RelocatableValue.from_tuple(y)
            for x, y in value}
