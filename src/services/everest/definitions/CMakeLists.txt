python_lib(everest_definitions_lib
    PREFIX services/everest/definitions

    FILES
    constants.py
    fields.py

    LIBS
    starkware_utils_lib
    pip_marshmallow
    pip_web3
)
