python_lib(starkware_storage_metric_lib
    PREFIX starkware/storage

    FILES
    metrics.py

    LIBS
    pip_prometheus_client
)

python_lib(starkware_storage_lib
    PREFIX starkware/storage

    FILES
    __init__.py
    batch_store.py
    dict_storage.py
    gated_storage.py
    imm_storage.py
    names.py
    storage.py

    LIBS
    starkware_config_utils_lib
    starkware_python_utils_lib
    starkware_serializability_utils_lib
    starkware_storage_metric_lib
    starkware_utils_time_lib
    pip_cachetools
    pip_marshmallow
)

python_lib(starkware_storage_utils_lib
    PREFIX starkware/storage

    FILES
    storage_utils.py

    LIBS
    starkware_commitment_tree_facts_lib
    starkware_python_utils_lib
    starkware_storage_lib
)

python_lib(starkware_storage_test_utils_lib
    PREFIX starkware/storage

    FILES
    test_utils.py

    LIBS
    starkware_storage_lib
)

full_python_test(starkware_storage_test
    PREFIX starkware/storage
    PYTHON python3.7
    TESTED_MODULES starkware/storage

    FILES
    batch_store_test.py
    gated_storage_test.py
    storage_test.py

    LIBS
    starkware_storage_lib
    starkware_storage_test_utils_lib
    pip_pytest
    pip_pytest_asyncio
)
