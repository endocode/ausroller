from setuptools import setup, find_packages
# To use a consistent encoding
from codecs import open
from os import path

here = path.abspath(path.dirname(__file__))

# Get the long description from the README file
with open(path.join(here, 'README.md'), encoding='utf-8') as f:
    long_description = f.read()

setup(
    name='ausroller',
    version='0.2.0-alpha',
    description='Deploy applications to kubernetes clusters',
    long_description=long_description,

    url='https://github.com/endocode/ausroller',

    # Author details
    author='Markus Herpich',
    author_email='markus@endocode.com',

    # Choose your license
    license='GPLv3',

    # See https://pypi.python.org/pypi?%3Aaction=list_classifiers
    classifiers=[
        # How mature is this project? Common values are
        #   3 - Alpha
        #   4 - Beta
        #   5 - Production/Stable
        'Development Status :: 3 - Alpha',

        # Indicate who your project is intended for
        'Intended Audience :: System Administrators',
        'Topic :: System',

        # Pick your license as you wish (should match "license" above)
        'License :: OSI Approved :: GNU General Public License v3 (GPLv3)',

        # Specify the Python versions you support here. In particular, ensure
        # that you indicate whether you support Python 2, Python 3 or both.
        'Programming Language :: Python :: 2.7',
    ],

    keywords='kubernetes k8s microservice deployment',

    packages=find_packages(exclude=['tests']),

    install_requires=['gbp',
                      'dateutils',
                      'jinja2'],

    # List additional groups of dependencies here (e.g. development
    # dependencies). You can install these using the following syntax,
    # for example:
    # $ pip install -e .[dev]
    extras_require={
        'dev': ['nose', 'nose-cov']
    },

    # To provide executable scripts, use entry points in preference to the
    # "scripts" keyword. Entry points provide cross-platform support and allow
    # pip to create the appropriate form of executable for the target platform.
    entry_points={
        'console_scripts': [
            'ausroller=ausroller.main:main',
        ],
    },
)
