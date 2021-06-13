python_lib(everest_definitions_lib
    PREFIX services/everest/definitions

    FILES
    fields.py

    LIBS
    starkware_utils_lib
    pip_marshmallow
)
