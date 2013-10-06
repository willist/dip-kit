from os import path

from setuptools import setup

from dip_kit import __version__


CLASSIFIERS = [
    'Development Status :: 3 - Alpha',
    'Intended Audience :: Developers',
    'License :: OSI Approved :: BSD License',
    'Operating System :: OS Independent',
    'Programming Language :: Python',
    'Programming Language :: Python',
    'Programming Language :: Python :: 2',
    'Programming Language :: Python :: 2.7',
    'Programming Language :: Python',
    'Programming Language :: Python :: 3',
    'Programming Language :: Python :: 3.3',
    'Topic :: Software Development :: Libraries :: Python Modules']


README = 'README.rst'
with open(path.join(path.dirname(__file__), README)) as fd:
    long_description = '\n' + fd.read()


setup(
    name='dip-kit',
    version=__version__,
    url='https://github.com/rduplain/dip-kit',
    license='BSD',
    author='Ron DuPlain',
    author_email='ron.duplain@gmail.com',
    description='dependency injection (dip) kit with Flask implementation',
    long_description=long_description,
    packages=['dip_kit', 'flask_kit'],
    install_requires=[
        'Flask>=0.10',
        'Flask-Mail>=0.9',
        'SQLAlchemy>=0.6',
        'docopt>=0.6',
        'jeni>=0.2',
    ],
    entry_points={
        'console_scripts': ['dip-kit = dip_kit.command:main'],
    },
    classifiers=CLASSIFIERS)
