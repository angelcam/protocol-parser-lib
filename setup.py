#!/usr/bin/env python

from setuptools import setup, find_packages

setup(
    name="protocolparser",
    version='1.0',
    description="Angelcam HTTP/RTSP parser library",
    keywords="asyncio HTTP RTSP",
    author="Angelcam",
    author_email="dev@angelcam.com",
    url="https://bitbucket.org/angelcam/protocol-parser-lib/",
    license="MIT",
    packages=find_packages(),
    long_description=open('README.md').read(),
    test_requirements=['pytest', ],
    include_package_data=True,
    platforms='any',
)
