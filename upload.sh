#!/bin/bash
pandoc --from=markdown --to=rst --output=README.rst README.md
if [ $# -eq 1 ]; then
    rm -rf dist/
    python setup.py sdist bdist_wheel
    twine upload dist/*
fi
