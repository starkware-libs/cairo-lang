# WARNING: This library is used by the Cairo playground hint server. Please don't add files
# unless they should be there.
python_lib(cairo_relocatable
    PREFIX starkware/cairo/lang/vm

    FILES
    relocatable.py
    relocatable_fields.py

    LIBS
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
    memory_segments.py
    output_builtin_runner.py
    security.py
    trace_entry.py
    utils.py
    validated_memory_dict.py
    vm.py
    vm_consts.py

    LIBS
    cairo_compile_lib
    cairo_relocatable
    cairo_vm_crypto_lib
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
    starkware_python_utils_lib
)

python_exe(cairo_run_exe
    VENV cairo_lang_venv
    MODULE starkware.cairo.lang.vm.cairo_run
)

full_python_test(cairo_vm_test
    PREFIX starkware/cairo/lang/vm
    PYTHON python3.7
    TESTED_MODULES starkware/cairo/lang/vm

    FILES
    cairo_pie_test.py
    cairo_runner_test.py
    memory_dict_test.py
    memory_segments_test.py
    output_builtin_runner_test.py
    relocatable_fields_test.py
    relocatable_test.py
    security_test.py
    test.cairo
    trace_entry_test.py
    validated_memory_dict_test.py
    vm_consts_test.py
    vm_test.py

    LIBS
    cairo_constants_lib
    cairo_run_lib
    cairo_vm_lib
    starkware_python_utils_lib
    pip_marshmallow
    pip_marshmallow_dataclass
    pip_pytest
)
