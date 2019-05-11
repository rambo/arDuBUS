"""Packaging script for ardubus"""
import os
import subprocess

import setuptools

GIT_VERSION = 'UNKNOWN'
try:
    GIT_VERSION = subprocess.check_output(['git', 'rev-parse', '--verify', '--short', 'HEAD']).decode('ascii').strip()
except subprocess.CalledProcessError:
    pass

setuptools.setup(
    name='ardubus',
    version=os.getenv('PACKAGE_VERSION', '0.1.0+git.%s' % GIT_VERSION),
    author='Eero "rambo" af Heurlin',
    author_email='eero.afheurlin@iki.fi',
    packages=setuptools.find_packages(),
    license='MIT',
    long_description=open('README.md', 'rt', encoding='utf-8').read(),
    long_description_content_type='text/markdown',
    description='ArDuBUS for python3',
    install_requires=open('requirements.txt', 'rt', encoding='utf-8').readlines(),
    url='https://github.com/rambo/ardubus',
)
