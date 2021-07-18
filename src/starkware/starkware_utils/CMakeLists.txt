add_subdirectory(time)

python_lib(starkware_serializability_utils_lib
    PREFIX starkware/starkware_utils

    FILES
    serializable.py
)

python_lib(starkware_utils_lib
    PREFIX starkware/starkware_utils

    FILES
    custom_raising_dict.py
    error_handling.py
    field_validators.py
    marshmallow_dataclass_fields.py
    subsequence.py
    validated_dataclass.py
    validated_fields.py
    ${STARKWARE_UTILS_LIBS_ADDITIONAL_FILES}

    LIBS
    starkware_python_utils_lib
    starkware_serializability_utils_lib
    pip_frozendict
    pip_marshmallow
    pip_marshmallow_dataclass
    pip_typeguard
    pip_web3
    ${STARKWARE_UTILS_LIBS_ADDITIONAL_LIBS}
)
