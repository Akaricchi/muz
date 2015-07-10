#!/usr/bin/env python

from setuptools import setup

setup(
    name='muz',
    version="0.01-prepreprealpha",
    description='A mania-style rhythm game',
    url='http://github.com/nexAkari/muz',
    author='Andrew "Akari" Alexeyew"',
    author_email='akari@alienslab.net',
    license='WTFPL',
    packages=['muz'],
    #install_requires=['pygame>=1.9.1'],
    zip_safe=False,
    include_package_data=True
)
