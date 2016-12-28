'''
@author: jimfan
'''
import os
from setuptools import setup

def read(fname):
    with open(os.path.join(os.path.dirname(__file__), fname)) as f:
        return f.read()


setup(name='gitex',
      version='0.1',
      author='Linxi (Jim) Fan',
      author_email='jimfan@cs.stanford.edu',
      url='http://github.com/LinxiFan/GiTeX',
      description='Generate LaTeX for Github markdown files.',
      long_description=read('README.rst'),
      keywords='LaTeX markdown github',
      license='GPLv3',
      packages=['gitex'],
      entry_points={
        'console_scripts': [
            'tex2png = gitex.tex2png:main',
            'gitex = gitex.compile:main'
        ]
      },
      classifiers=[
          "Development Status :: 4 - Beta",
          "Topic :: Utilities",
          "Topic :: Text Processing :: Markup :: LaTeX",
          "Environment :: Console",
          "Programming Language :: Python :: 3"
      ],
      install_requires=read('requirements.txt').strip().splitlines(),
      include_package_data=True,
      zip_safe=False
)