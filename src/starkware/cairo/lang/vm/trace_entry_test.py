from starkware.cairo.lang.vm.trace_entry import TraceEntry


def test_trace_entry_serialization():
    # Test serialization of a TraceEntry (values taken from the instruction
    # "[ap] = [ap - 1] + 2, ap++;").
    entry = TraceEntry(ap=0x66, fp=0x64, pc=0xA)
    serialized = entry.serialize()
    assert len(serialized) == TraceEntry.serialization_size()
    assert (
        serialized.hex()
        == """
66 00 00 00 00 00 00 00
64 00 00 00 00 00 00 00
0a 00 00 00 00 00 00 00
""".replace(
            " ", ""
        ).replace(
            "\n", ""
        )
    )

    # Test deserialization.
    assert TraceEntry.deserialize(serialized).serialize() == serialized
