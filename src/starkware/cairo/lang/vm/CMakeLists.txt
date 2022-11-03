python_lib(cairo_relocatable_lib
    PREFIX starkware/cairo/lang/vm

    FILES
    relocatable.py
    relocatable_fields.py

    LIBS
    starkware_python_utils_lib
    pip_marshmallow
)

python_lib(cairo_vm_crypto_lib
    PREFIX starkware/cairo/lang/vm

    FILES
    crypto.py

    LIBS
    starkware_crypto_lib
    ${CAIRO_VM_CRYPTO_ADDITIONAL_LIBS}
)

python_lib(cairo_vm_lib
    PREFIX starkware/cairo/lang/vm

    FILES
    air_public_input.py
    builtin_runner.py
    cairo_pie.py
    memory_dict.py
    memory_dict_backend.py
    memory_segments.py
    output_builtin_runner.py
    security.py
    trace_entry.py
    utils.py
    validated_memory_dict.py
    virtual_machine_base.py
    vm.py
    vm_consts.py
    vm_core.py
    vm_exceptions.py

    LIBS
    cairo_all_builtins_lib
    cairo_compile_lib
    cairo_relocatable_lib
    cairo_vm_crypto_lib
    starknet_security_lib
    starkware_python_utils_lib
)

python_lib(cairo_run_lib
    PREFIX starkware/cairo/lang/vm

    FILES
    cairo_run.py
    cairo_runner.py

    LIBS
    cairo_compile_lib
    cairo_instances_lib
    cairo_run_builtins_lib
    cairo_tracer_lib
    cairo_version_lib
    cairo_vm_lib
    starkware_utils_lib
    starkware_python_utils_lib
)

python_lib(cairo_vm_utils_lib
    PREFIX starkware/cairo/lang/vm

    FILES
    reconstruct_traceback.py

    LIBS
    cairo_compile_lib
    cairo_version_lib
)

python_exe(cairo_run_exe
    VENV cairo_lang_venv
    MODULE starkware.cairo.lang.vm.cairo_run
)

python_lib(cairo_vm_test_utils_lib
    PREFIX starkware/cairo/lang/vm

    FILES
    test_utils.py

    LIBS
    cairo_compile_lib
    cairo_run_lib
    cairo_vm_lib
)

full_python_test(cairo_vm_test
    PREFIX starkware/cairo/lang/vm
    PYTHON ${PYTHON_COMMAND}
    TESTED_MODULES starkware/cairo/lang/vm

    FILES
    cairo_pie_test.py
    cairo_runner_test.py
    memory_dict_test.py
    memory_segments_test.py
    output_builtin_runner_test.py
    reconstruct_traceback_test.py
    relocatable_fields_test.py
    relocatable_test.py
    security_test.py
    test.cairo
    trace_entry_test.py
    validated_memory_dict_test.py
    vm_consts_test.py
    vm_test.py

    LIBS
    cairo_common_lib
    cairo_compile_lib
    cairo_constants_lib
    cairo_run_lib
    cairo_vm_lib
    cairo_vm_test_utils_lib
    cairo_vm_utils_lib
    starkware_dataclasses_field_utils_lib
    starkware_python_utils_lib
    starkware_python_test_utils_lib
    pip_marshmallow_dataclass
    pip_pytest
)
