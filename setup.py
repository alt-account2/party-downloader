from setuptools import setup, find_packages

setup(
    name='party-downloader',
    version='0.0.4',
    # description='A description of your package',
    packages=find_packages(),
    install_requires=[
        'requests',
        'tqdm',
        'beautifulsoup4',
    ],
)
