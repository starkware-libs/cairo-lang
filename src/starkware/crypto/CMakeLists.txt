python_lib(starkware_crypto_lib
    FILES
    starkware/crypto/signature/fast_pedersen_hash.py
    starkware/crypto/signature/math_utils.py
    starkware/crypto/signature/nothing_up_my_sleeve_gen.py
    starkware/crypto/signature/pedersen_params.json
    starkware/crypto/signature/signature.py
    ${STARKWARE_CRYPTO_LIB_ADDITIONAL_FILES}

    LIBS
    pip_ecdsa
    pip_fastecdsa
    pip_mpmath
    pip_sympy
    ${STARKWARE_CRYPTO_LIB_ADDITIONAL_LIBS}
)
