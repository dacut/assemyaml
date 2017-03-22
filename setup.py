#!/usr/bin/env python
from __future__ import absolute_import, division, print_function
from setuptools import setup

setup(
    name="Assemyaml",
    version="0.1",
    packages=["assemyaml"],
    entry_points={"console_scripts": ["assemyaml=assemyaml:main"]},
    install_requires=["PyYAML>=3.0", "six>=1.10.0"],
    tests_require=["coverage>=4.0", "moto>=0.4", "nose>=1.0", "testfixtures>=4"],
    test_suite="tests",

    # PyPI information
    author="David Cuthbert",
    author_email="dacut@kanga.org",
    description="Assemble and merge multiple YAML documents",
    license="Apache",
    classifiers=[
        'Development Status :: 4 - Beta',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: Apache Software License',
        'Programming Language :: Python',
        'Topic :: Software Development :: Libraries :: Python Modules',
        'Topic :: Text Processing',
    ],
    keywords=['yaml'],
    url="http://assemyaml.nz/",
    zip_safe=False,
)
