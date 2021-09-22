#!/usr/bin/env python3

"""
Converts a list of interpreter specific library dependencies, to a list of united library target
names.
Example:
  Input: a b python:c pypy:c pypy:d
  Output: a b c d
"""

import sys

sys.stdout.write(" ".join(sorted(set(x.split(":")[-1] for x in sys.argv[1:]))))
