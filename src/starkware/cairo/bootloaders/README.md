# Bootloader program hashes and their provenance

The bootloader program writes its config to the output as a single Pedersen hash, which the
on-chain verifier stores and checks: `serialize_bootloader_config` in
`bootloader/run_bootloader.cairo` computes it, and `combine_bootloader_config_hash` in
`supported_bootloaders_hash.py` is its Python mirror. The hash folds four values, all of which
derive from files committed in this directory:

| Field in `bootloader/bootloader_config_hash.json` | Derived from | Checked by |
| --- | --- | --- |
| `supported_simple_bootloader_hash_list_hash` | The Poseidon and Blake2s program hashes of the compiled `simple_bootloader` and `no_builtin_simulation_simple_bootloader` programs in `simple_bootloader/`. | `supported_bootloaders_hash_test` |
| `circuit_applicative_bootloader_config_program_hash` | The Blake2s program hash of the compiled `circuit_applicative_bootloader/` program. | `supported_bootloaders_hash_test` |
| `circuit_applicative_config_commitment` | The circuit verifier program hash in `circuit_applicative_bootloader/circuit_verifier_program_hash.json` and the multiverifier and leaf verifier circuit hashes in `circuit_applicative_bootloader/production_circuit_registry.json`, hashed as in `config_commitment.cairo` (Python mirror: `config_commitment.py`). | `bootloader/bootloader_config_hash_test` |
| `supported_cairo_verifier_hash_list_hash` | The verifier program hashes listed in `bootloader/supported_program_hashes.json`. | `bootloader/bootloader_config_hash_test` |

`bootloader/bootloader_config_hash_test` recomputes every field from these files and compares the
result with the committed JSON, so the config hash can be verified from this repository alone:

```
bazel test //src/starkware/cairo/bootloaders/bootloader:cairo_bootloader_config_hash_test
```

## Where the committed artifacts come from

The verifier list in `bootloader/supported_program_hashes.json` has two kinds of entries. The
per-layout Cairo verifier programs are compiled from `src/starkware/cairo/cairo_verifier` in this
repository. The stwo verifier programs, and the inputs of the config commitment, are copies of
artifacts built from the [starkware-libs/proving](https://github.com/starkware-libs/proving)
repository and published by its `upload artifacts` workflow,
`.github/workflows/upload-artifacts-workflow.yml`, which records the exact build commands. They
are pinned to these commits:

- Proving commit: `e0035ffc8e08da270b8cb4a71f3708af70c2c775`
- Frozen verifier commit: `770d4da27995779eaee8929a776bbd7845192b41` (the `cairo-verifier-frozen`
  branch)

| Committed artifact | Built at | Workflow job |
| --- | --- | --- |
| `circuit_applicative_bootloader/production_circuit_registry.json`, the `production` circuit registry (`circuit_params --registry`). | The proving commit ([workflow file](https://github.com/starkware-libs/proving/blob/e0035ffc8e08da270b8cb4a71f3708af70c2c775/.github/workflows/upload-artifacts-workflow.yml)) | `supported-circuits-registry-push` |
| `circuit_applicative_bootloader/circuit_verifier_program_hash.json`, the program hash of the `stwo_circuit_verifier` package. | The proving commit (same workflow file) | `cairo-verifiers-push` |
| The stwo Cairo verifier hashes in `bootloader/supported_program_hashes.json`: the `stwo_cairo_verifier` package in its default, Poseidon and Blake2s-packing flavors. | The frozen verifier commit, same workflow file on the `cairo-verifier-frozen` branch | `cairo-verifiers-push` |
