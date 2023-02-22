python_lib(starkware_crypto_lib
    PREFIX starkware/crypto

    FILES
    signature/fast_pedersen_hash.py
    signature/math_utils.py
    signature/nothing_up_my_sleeve_gen.py
    signature/pedersen_params.json
    signature/signature.py

    LIBS
    starkware_python_utils_lib
    pip_ecdsa
    pip_fastecdsa
    pip_mpmath
    pip_sympy
)
