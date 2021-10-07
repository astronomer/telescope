#!/usr/bin/env python
import pathlib

from pkg_resources import parse_requirements
from setuptools import setup, find_packages

with pathlib.Path('requirements.txt').open() as requirements_txt:
    install_requires = [str(requirement) for requirement in parse_requirements(requirements_txt)]

VERSION = '0.0.1'
repo = 'fritz-astronomer/telescope'

setup(
    name='telescope',
    version=VERSION,
    description='',
    long_description=open("README.md").read(),
    url=f'git@github.com:{repo}.git',
    packages=find_packages(),
    include_package_data=True,
    install_requires=install_requires,
    entry_points={'console_scripts': ['telescope=telescope.coordinator:cli']}
)
