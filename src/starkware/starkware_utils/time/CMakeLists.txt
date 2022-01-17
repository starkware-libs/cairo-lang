python_lib(starkware_utils_time_lib
    PREFIX starkware/starkware_utils/time

    FILES
    __init__.py
    fastforward.py
    synchronous_executor.py
    time.py
)

python_lib(starkware_utils_time_test_lib
    PREFIX starkware/starkware_utils/time

    FILES
    time_test.py
)
