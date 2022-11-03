python_lib(starknet_os_config_hash_lib
    PREFIX starkware/starknet/core/os/os_config

    FILES
    os_config_hash.py

    LIBS
    cairo_common_lib
    starknet_general_config_lib
)

full_python_test(starknet_os_config_hash_test
    PREFIX starkware/starknet/core/os/os_config
    PYTHON ${PYTHON_COMMAND}
    TESTED_MODULES starkware/starknet/core/os

    FILES
    os_config_hash_test.py
    os_config_hash.json

    LIBS
    cairo_common_lib
    cairo_function_runner_lib
    starknet_os_config_hash_lib
    starknet_general_config_lib
    starknet_os_utils_lib
    starkware_python_test_utils_lib
    starkware_python_utils_lib
    pip_pytest
    pip_pytest_asyncio
)

python_exe(starknet_os_config_hash_fix
    VENV starknet_os_config_hash_test_venv
    MODULE starkware.starknet.core.os.os_config.os_config_hash_test
    ARGS "--fix"
)
