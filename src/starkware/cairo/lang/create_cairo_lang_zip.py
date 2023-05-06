"""
This script is run by the target create_cairo_lang_package_zip to create the cairo-lang package
zip file.
"""

import os
import shutil
import subprocess
import sys

from starkware.python.utils import get_build_dir_path

INIT_FILE_CONTENT = "__path__ = __import__('pkgutil').extend_path(__path__, __name__)\n"


def add_init_files(path: str):
    """
    Adds __init__.py files (with INIT_FILE_CONTENT) to every directory which does not have an init
    file and contains a ".py" file or a sub directory.
    """

    for path, directories, files in os.walk(path):
        if "__init__.py" in files:
            continue

        if len(directories) > 0 or any(file_name.endswith(".py") for file_name in files):
            with open(os.path.join(path, "__init__.py"), "w") as init_file:
                init_file.write(INIT_FILE_CONTENT)


if __name__ == "__main__":
    dst_dir = get_build_dir_path("src")

    # Add init files.
    add_init_files(os.path.join(dst_dir, "starkware"))
    add_init_files(os.path.join(dst_dir, "services"))

    shutil.copy("src/starkware/cairo/lang/setup.py", dst_dir)
    shutil.copy("src/starkware/cairo/lang/MANIFEST.in", dst_dir)
    shutil.copy("scripts/requirements-gen.txt", os.path.join(dst_dir, "requirements.txt"))
    shutil.copy("README.md", dst_dir)

    # Run setup.py.
    subprocess.check_call([sys.executable, "setup.py", "sdist", "--format=zip"], cwd=dst_dir)

    with open("src/starkware/cairo/lang/VERSION", "r") as f:
        version = f.read().strip("\n")
    shutil.copy(f"{dst_dir}/dist/cairo-lang-{version}.zip", ".")
