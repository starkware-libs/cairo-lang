python_lib(everest_definitions_lib
    PREFIX services/everest/definitions

    FILES
    constants.py
    fields.py

    LIBS
    starkware_dataclasses_utils_lib
    starkware_error_handling_lib
    pip_marshmallow
    pip_web3
)
