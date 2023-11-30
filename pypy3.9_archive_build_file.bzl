package(default_visibility = ["//visibility:public"])

EXCLUDE_PATTERN = [
    "**/__pycache__/**",
    "**/*.pyc",
    "**/*.pyc.*",  # During pyc creation, temp files named *.pyc.NNN are created.
    "**/*.dist-info/RECORD",
]
