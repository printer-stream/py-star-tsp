from setuptools import setup, find_packages
from py_star_tsp.version import __version__

setup(
    name='py-star-tsp',
    version=__version__,
    packages=find_packages(),
    install_requires=['pyusb>=1.3.0', 'Pillow>=12.0.0'],
    python_requires='>=3.8',
    description='Python SDK for Star TSP100 Graphic Mode thermal printers',
    long_description=open('README.md').read(),
    long_description_content_type='text/markdown',
    author='Pavel Kim',
    author_email="hello@pavelkim.com",
    url='https://github.com/printer-stream/py-star-tsp',
    classifiers=[
        'Programming Language :: Python :: 3',
        'License :: OSI Approved :: GNU General Public License v3 (GPLv3)',
        'Operating System :: OS Independent',
        'Topic :: Printing',
    ],
)
