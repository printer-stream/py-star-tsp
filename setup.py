from setuptools import setup, find_packages

setup(
    name='py-star-tsp',
    version='0.1.0',
    packages=find_packages(),
    install_requires=['pyusb>=1.2.1', 'Pillow>=9.0.0'],
    python_requires='>=3.8',
    description='Python SDK for Star TSP100 Graphic Mode thermal printers',
    long_description=open('README.md').read(),
    long_description_content_type='text/markdown',
    author='printer-stream',
    url='https://github.com/printer-stream/py-star-tsp',
    classifiers=[
        'Programming Language :: Python :: 3',
        'License :: OSI Approved :: GNU General Public License v3 (GPLv3)',
        'Operating System :: OS Independent',
        'Topic :: Printing',
    ],
)
