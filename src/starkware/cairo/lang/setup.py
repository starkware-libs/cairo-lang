import os.path

import setuptools

DIR = os.path.abspath(os.path.dirname(__file__))
requirements = open(os.path.join(DIR, "requirements.txt")).read().splitlines()
version = open(os.path.join(DIR, "starkware/cairo/lang/VERSION")).read().strip()
long_description = open("README.md", "r", encoding="utf-8").read()

setuptools.setup(
    name="cairo-lang",
    version=version,
    author="Starkware",
    author_email="info@starkware.co",
    description="Compiler and runner for the Cairo language",
    install_requires=requirements,
    long_description=long_description,
    long_description_content_type="text/markdown",
    packages=setuptools.find_packages(),
    python_requires=">=3.6",
    setup_requires=["wheel"],
    url="https://cairo-lang.org/",
    package_data={
        "starkware.cairo.common": ["*.cairo", "*/*.cairo"],
        "starkware.cairo.lang.compiler": ["cairo.ebnf", "lib/*.cairo"],
        "starkware.cairo.lang.migrators": ["*.ebnf"],
        "starkware.cairo.lang.tracer": ["*.html", "*.css", "*.js", "*.png"],
        "starkware.cairo.lang": ["VERSION"],
        "starkware.cairo.sharp": ["config.json"],
        "starkware.crypto.signature": ["pedersen_params.json"],
        "starkware.starknet": ["common/*.cairo", "definitions/*.yml"],
        "starkware.starknet.business_logic.execution": ["os_resources.json"],
        "starkware.starknet.compiler.v1": [
            "*.json",
            "corelib/*.cairo",
            "corelib/src/*.cairo",
            "corelib/src/starknet/*.cairo",
            "bin/starknet-sierra-compile",
            "bin/starknet-compile",
        ],
        "starkware.starknet.core.os": ["*/*.cairo", "*.cairo", "*.json"],
        "starkware.starknet.core.test_contract": ["*.cairo", "*.json"],
        "starkware.starknet.security": ["whitelists/*.json"],
        "starkware.starknet.testing": ["*.json"],
        "starkware.starknet.third_party.open_zeppelin": ["account.json"],
    },
    scripts=[
        "starkware/cairo/lang/scripts/cairo-compile",
        "starkware/cairo/lang/scripts/cairo-format",
        "starkware/cairo/lang/scripts/cairo-hash-program",
        "starkware/cairo/lang/scripts/cairo-migrate",
        "starkware/cairo/lang/scripts/cairo-reconstruct-traceback",
        "starkware/cairo/lang/scripts/cairo-run",
        "starkware/cairo/lang/scripts/cairo-sharp",
        "starkware/starknet/scripts/starknet-class-hash",
        "starkware/starknet/scripts/starknet-compile-deprecated",
        "starkware/starknet/scripts/starknet",
    ],
)
