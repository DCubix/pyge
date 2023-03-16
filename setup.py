VERSION = '0.1.2'

from setuptools import setup, find_packages, Command
import shutil, glob, os

with open('requirements.txt') as f:
    required = f.read().splitlines()

with open('README.md') as f:
    long_description = '\n'.join(f.readlines())

class CleanCommand(Command):
    """Custom clean command to tidy up the project root."""
    CLEAN_FILES = './build ./dist ./*.pyc ./*.tgz ./*.egg-info'.split(' ')

    user_options = []

    def initialize_options(self):
        pass

    def finalize_options(self):
        pass

    def run(self):
        global here

        for path_spec in self.CLEAN_FILES:
            # Make paths absolute and relative to this path
            abs_paths = glob.glob(os.path.normpath(os.path.join(here, path_spec)))
            for path in [str(p) for p in abs_paths]:
                if not path.startswith(here):
                    # Die if path in CLEAN_FILES is absolute + outside this directory
                    raise ValueError("%s is not a path inside %s" % (path, here))
                print('removing %s' % os.path.relpath(path))
                shutil.rmtree(path)

setup(
    cmdclass={
        'cleanup': CleanCommand
    },
    name='pygex',
    version=VERSION,
    description='A simple Python game engine built around pygame and PyOpenGL.',
    long_description=long_description,
    long_description_content_type="text/markdown",
    url='https://github.com/DCubix/pyge',
    author='Diego Lopes',
    author_email='diego95lopes@gmail.com',
    license='MIT',
    packages=find_packages(),
    install_requires=required,
    include_package_data=True,
    keywords=['python', 'game', 'engine', '3d', 'graphics', 'gamedev']
)
