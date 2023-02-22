include(storage_base.cmake)



python_lib(starkware_storage_lib
    PREFIX starkware/storage

    FILES
    gated_storage.py
    names.py

    LIBS
    starkware_abstract_storage_lib
    starkware_imm_storage_lib
    starkware_storage_metric_lib
    starkware_utils_time_lib
    pip_cachetools
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

full_python_test(starkware_storage_test
    PREFIX starkware/storage
    PYTHON ${PYTHON_COMMAND}
    TESTED_MODULES starkware/storage

    FILES
    gated_storage_test.py

    LIBS
    starkware_storage_lib
    starkware_storage_test_utils_lib
    pip_pytest
    pip_pytest_asyncio
)
