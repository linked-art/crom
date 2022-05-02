from setuptools import setup
import sys

install_requires = ['rdflib', 'PyLD']

setup(
    name = 'cromulent',
    packages = ['cromulent'],
    package_data = {
        'cromulent': ['data/crm_vocab.tsv', 'data/overrides.json', 
        'data/key_order.json', 'data/linked-art.json', 
        'data/cidoc-extension.json', 'data/crm-profile.json']
    },
    test_suite="tests",
    version = '0.17.1',
    description = 'A library for mapping CIDOC-CRM (v7.1) classes to Python objects',
    author = 'Rob Sanderson',
    author_email = 'robert.sanderson@yale.edu',
    url = 'https://github.com/linked-art/crom',
    install_requires=install_requires,
    classifiers = [
        "Programming Language :: Python",
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: Apache Software License",
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Developers",
        "Operating System :: OS Independent",
        "Topic :: Software Development :: Libraries :: Python Modules",
    ]
)
