from setuptools import setup, find_packages

with open('requirements.txt') as f:
    required = f.read().splitlines()

setup(
    name='pyge',
    version='0.1',
    description='A simple Python game engine built around pygame and PyOpenGL.',
    url='https://github.com/DCubix/pyge',
    author='Diego Lopes',
    author_email='diego95lopes@gmail.com',
    license='MIT',
    packages=find_packages(),
    install_requires=required,
    include_package_data=True,
    keywords=['python', 'game', 'engine', '3d', 'graphics', 'gamedev']
)
