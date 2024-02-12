from starkware.cairo.common.alloc import alloc
from starkware.cairo.common.cairo_builtins import BitwiseBuiltin, PoseidonBuiltin
from starkware.cairo.stark_verifier.core.channel import (
    Channel,
    ChannelSentFelt,
    ChannelUnsentFelt,
    channel_new,
    random_felts_to_prover,
    read_felt_from_prover,
    read_felt_vector_from_prover,
)

func test_to{range_check_ptr, poseidon_ptr: PoseidonBuiltin*}() {
    alloc_locals;
    let channel = Channel(
        digest=0xf7685ebd40e852b164633a4acbd3244ce8e77626586f73b955364c7b4bbf0bb7, counter=0
    );
    with channel {
        let (local elements) = alloc();
        random_felts_to_prover(n_elements=3, elements=elements);
        assert elements[0] = (
            3533027684628956165978305876325630627835096878181671876090486602645253128476
        );
        assert elements[1] = (
            2370447022038372734218915542001411042819539837715200287809352900631960083160
        );
        assert elements[2] = (
            1778214449671764181199601003651150149450981695342251013132258932091844223356
        );
    }
    return ();
}

func test_from{
    range_check_ptr,
    bitwise_ptr: BitwiseBuiltin*,
    poseidon_ptr: PoseidonBuiltin*,
    blake2s_ptr: felt*,
}() {
    alloc_locals;
    let (channel) = channel_new(digest=0);
    local original_channel: Channel = channel;
    with channel {
        let (unsent_values: ChannelUnsentFelt*) = alloc();
        let (value) = read_felt_from_prover(ChannelUnsentFelt(2 ** 160 - 1));
        assert value = ChannelSentFelt(2 ** 160 - 1);
        assert channel.digest = (
            2404923971468808986284442513933980719024739752676849841176381572976693688852
        );
        assert channel.counter = 0;

        // Read multiple felts.
        let (local unsent_values: ChannelUnsentFelt*) = alloc();
        %{ segments.write_arg(ids.unsent_values.address_, [2, 3, -1]) %}
        let (values: ChannelSentFelt*) = read_felt_vector_from_prover(
            n_values=3, values=unsent_values
        );

        assert channel.digest = (
            1848207095114937558943660674287355925302688287066418881756845813317170906578
        );
        assert channel.counter = 0;
        %{
            assert memory[ids.values.address_ + 0] == 2
            assert memory[ids.values.address_ + 1] == 3
            assert memory[ids.values.address_ + 2] == PRIME - 1
        %}

        // Read a felt vector.
        let (values: ChannelSentFelt*) = read_felt_vector_from_prover(
            n_values=3, values=unsent_values
        );
        assert channel.digest = (
            2811328047807283001311630152648722329959705504374865176374307731762269234748
        );
        assert channel.counter = 0;
        %{
            assert memory[ids.values.address_ + 0] == 2
            assert memory[ids.values.address_ + 1] == 3
            assert memory[ids.values.address_ + 2] == PRIME - 1
        %}
        ap += 0;
    }
    return ();
}

func main_test{
    range_check_ptr,
    bitwise_ptr: BitwiseBuiltin*,
    poseidon_ptr: PoseidonBuiltin*,
    blake2s_ptr: felt*,
}() -> () {
    test_to();
    test_from();
    return ();
}
