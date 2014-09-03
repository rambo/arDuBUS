from distutils.core import setup
import subprocess

git_version = str(subprocess.check_output(['git', 'rev-parse', '--verify', '--short', 'HEAD'])).strip()

setup(
    name='ardubus',
    version='0.5.dev-%s' % git_version,
    author='Eero "rambo" af Heurlin',
    author_email='rambo@iki.fi',
    packages=['ardubus',],
    license='GNU LGPL',
    long_description=open('README.md').read(),
    install_requires=[
        'pyserial>=2.7',
        'dbushelpers>=0.1', 
        'PyGObject>=2.0', # You will most likely need this from the distro packages
        'PyYAML>=3.0', # This will be more performant if you install distro package compiled against libyaml
    ],
    url='https://github.com/rambo/python-ardubus',
)

