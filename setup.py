# Always prefer setuptools over distutils
from setuptools import setup, find_packages
# To use a consistent encoding
from codecs import open
from os import path

here = path.abspath(path.dirname(__file__))

# Get the long description from the README file
with open(path.join(here, 'README.md'), encoding='utf-8') as f:
    long_description = f.read()


setup(

  name = 'gitconsensus',

  version = '0.0.1.dev1',
  packages=find_packages(),

  description = 'Automate Github Pull Requests using Reactions',
  long_description=long_description,
  python_requires='>=3',

  author = 'Robert Hafner',
  author_email = 'tedivm@tedivm.com',
  url = 'https://github.com/tedivm/gitconsensus',
  download_url = 'https://github.com/tedivm/gitconsensus/archive/0.1.tar.gz',
  keywords = 'automation github consensus git',

  classifiers = [
    'Development Status :: 4 - Beta',
    'License :: OSI Approved :: MIT License',

    'Intended Audience :: Developers',
    'Intended Audience :: System Administrators',
    'Topic :: Software Development :: Version Control'

    'Programming Language :: Python :: 3',
    'Environment :: Console',
  ],

  install_requires=[
    'click>=5.0,<6.0',
    'github3.py==0.9.6,<0.10',
    'PyYAML>=3.12,<3.13',
    'requests>=2.18.0,<2.19',
  ],

  extras_require={
    'dev': [
      'wheel',
      'twine'
    ],
  },

  entry_points={
    'console_scripts': [
      'gitconsensus=gitconsensus.gitconsensus:cli',
    ],
  },

)
