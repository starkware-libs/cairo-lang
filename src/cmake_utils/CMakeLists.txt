python_lib(gen_solidity_lib
    FILES
    gen_solidity_env.py
    LIBS
    pip_mypy_extensions
)

python_venv(gen_solidity_venv
    PYTHON python3.7
    LIBS
    gen_solidity_lib
)

python_exe(gen_solidity_exe
    VENV gen_solidity_venv
    MODULE gen_solidity_env
)
