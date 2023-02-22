python_lib(starkware_abstract_storage_lib
    PREFIX starkware/storage

    FILES
    __init__.py
    storage.py

    LIBS
    starkware_config_utils_lib
    starkware_python_utils_lib
    starkware_serializability_utils_lib
)

python_lib(starkware_storage_metric_lib
    PREFIX starkware/storage

    FILES
    metrics.py

    LIBS
    pip_prometheus_client
)

python_lib(starkware_dict_storage_lib
    PREFIX starkware/storage

    FILES
    dict_storage.py

    LIBS
    starkware_abstract_storage_lib
    starkware_storage_metric_lib
    pip_cachetools
)

python_lib(starkware_imm_storage_lib
    PREFIX starkware/storage

    FILES
    imm_storage.py

    LIBS
    starkware_abstract_storage_lib
)

python_lib(starkware_storage_test_utils_lib
    PREFIX starkware/storage

    FILES
    test_utils.py

    LIBS
    starkware_abstract_storage_lib
)

full_python_test(starkware_abstract_storage_test
    PREFIX starkware/storage
    PYTHON ${PYTHON_COMMAND}
    TESTED_MODULES starkware/storage

    FILES
    storage_test.py

    LIBS
    starkware_abstract_storage_lib
    starkware_dict_storage_lib
    starkware_storage_test_utils_lib
    pip_pytest
    pip_pytest_asyncio
)
