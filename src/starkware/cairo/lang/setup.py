import os.path

import setuptools

DIR = os.path.abspath(os.path.dirname(__file__))
requirements = open(os.path.join(DIR, 'requirements.txt')).read().splitlines()

setuptools.setup(
    name='cairo-starkware',
    version='0.0.1',
    author='Starkware',
    author_email='info@starkware.co',
    description='Compiler and runner for the Cairo language',
    packages=setuptools.find_packages(),
    python_requires='>=3.6',
    setup_requires=['wheel'],
    install_requires=requirements,
    package_data={
        'starkware.cairo.lang.compiler': ['cairo.ebnf'],
        'starkware.cairo.lang.tracer': ['*.html', '*.css', '*.js', '*.png'],
        'starkware.cairo.common': ['*.cairo'],
        'starkware.crypto.signature': ['pedersen_params.json'],
    },
    scripts=[
        'starkware/cairo/lang/scripts/cairo-format',
        'starkware/cairo/lang/scripts/cairo-compile',
        'starkware/cairo/lang/scripts/cairo-run',
    ]
)
