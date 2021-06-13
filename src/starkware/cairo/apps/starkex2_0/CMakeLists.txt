# ***********************************************************************
# * This code is licensed under the Cairo Program License.              *
# * The license can be found in: licenses/CairoProgramLicense.txt       *
# ***********************************************************************

full_python_test(starkex2_0_program_test
    PREFIX starkware/cairo/apps/starkex2_0
    PYTHON python3.7
    TESTED_MODULES starkware/cairo/apps/starkex2_0

    FILES
    __start__.cairo
    common/cairo_builtins.cairo
    common/dict.cairo
    common/merkle_multi_update.cairo
    common/merkle_update.cairo
    common/registers.cairo
    dex_constants.cairo
    dex_context.cairo
    execute_batch.cairo
    execute_false_full_withdrawal.cairo
    execute_limit_order.cairo
    execute_modification.cairo
    execute_settlement.cairo
    execute_transfer.cairo
    hash_vault_ptr_dict.cairo
    main.cairo
    starkex2_0_program_test.py
    vault_update.cairo
    verify_order_id.cairo
    verify_order_signature.cairo

    LIBS
    starkware_python_utils_lib
    pip_pytest

    PY_EXE_DEPENDENCIES
    cairo_compile_exe
    cairo_hash_program_exe
)

