from setuptools import setup

setup(name='qwerasdf',
      version='0.2.0',
      description='GUI Drawing Program for creating string mandala designs',
      author='nat',
      license='MIT',
      packages=['qwerasdf'],
      install_requires=['numpy', 'pygame'],
      entry_points={
          'console_script': [ 'qwerasdf=qwerasdf:main' ],
          'gui_scripts': [ 'qwerasdf=qwerasdf:main' ],
      },
      include_package_data = True,
      zip_safe=False)

