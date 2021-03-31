python_lib(cairo_tracer_lib
    PREFIX starkware/cairo/lang/tracer

    FILES
    favicon.png
    index.html
    profile.py
    profiler.py
    third_party/profile_pb2.py
    tracer_data.py
    tracer.css
    tracer.js
    tracer.py

    LIBS
    cairo_compile_lib
    cairo_vm_lib
    pip_protobuf
)

full_python_test(cairo_tracer_test
    PREFIX starkware/cairo/lang/tracer
    PYTHON python3.7
    TESTED_MODULES starkware/cairo/lang/tracer

    FILES
    tracer_data_test.py

    LIBS
    cairo_run_lib
    cairo_tracer_lib
    pip_pytest
)
