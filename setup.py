from distutils.core import setup

setup(
    name="protocolparser",
    version='1.0',
    description="Angelcam HTTP/RTSP parser library",
    keywords="asyncio HTTP RTSP",
    author="Angelcam",
    author_email="dev@angelcam.com",
    url="https://bitbucket.org/angelcam/protocol-parser-lib/",
    license="MIT",
    long_description=open('README.md').read(),
    test_requirements=['pytest', ]
)
