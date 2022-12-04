from starkware.cairo.common.alloc import alloc
from starkware.cairo.common.cairo_builtins import BitwiseBuiltin
from starkware.cairo.common.uint256 import Uint256
from starkware.cairo.stark_verifier.core.channel import (
    Channel,
    ChannelSentFelt,
    ChannelUnsentFelt,
    channel_new,
    random_felts_to_prover,
    random_uint256_to_prover,
    read_felt_vector_from_prover,
    read_felts_from_prover,
    read_truncated_hash_from_prover,
)

func test_to{range_check_ptr, bitwise_ptr: BitwiseBuiltin*, blake2s_ptr: felt*}() {
    alloc_locals;
    let channel = Channel(
        digest=Uint256(0xf7685ebd40e852b164633a4acbd3244c, 0xe8e77626586f73b955364c7b4bbf0bb7),
        counter=0,
    );
    with channel {
        let (local elements) = alloc();
        random_felts_to_prover(n_elements=3, elements=elements);
        assert elements[0] = (
            3199910790894706855027093840383592257502485581126271436027309705477370004002
        );
        assert elements[1] = (
            2678311171676075552444787698918310126938416157877134200897080931937186268438
        );
        assert elements[2] = (
            2409925148191156067407217062797240658947927224212800962983204460004996362724
        );
    }
    return ();
}

func test_from{range_check_ptr, bitwise_ptr: BitwiseBuiltin*, blake2s_ptr: felt*}() {
    alloc_locals;
    let (channel) = channel_new(digest=Uint256(0, 0));
    local original_channel: Channel = channel;
    with channel {
        let (unsent_values: ChannelUnsentFelt*) = alloc();

        read_felts_from_prover(n_values=0, values=unsent_values);
        assert channel.digest = original_channel.digest;
        assert channel.counter = original_channel.counter;

        let (value) = read_truncated_hash_from_prover(ChannelUnsentFelt(2 ** 160 - 1));
        assert value = ChannelSentFelt(2 ** 160 - 1);
        assert channel.digest = Uint256(
            264245158129643438725130805500698377532, 273487178329072845015974259185110443467
        );
        assert channel.counter = 0;

        // Read multiple felts.
        let (local unsent_values: ChannelUnsentFelt*) = alloc();
        %{ segments.write_arg(ids.unsent_values.address_, [2, 3, -1]) %}
        let (values: ChannelSentFelt*) = read_felts_from_prover(n_values=3, values=unsent_values);
        assert channel.digest = Uint256(
            242546666571867849760234496042176867468, 276032264349006147573126117370612632439
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
        assert channel.digest = Uint256(
            47489586150803289593519442158772964707, 295510913258162813848457591889478884574
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

func main_test{range_check_ptr, bitwise_ptr: BitwiseBuiltin*, blake2s_ptr: felt*}() -> () {
    test_to();
    test_from();
    return ();
}
