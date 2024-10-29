from setuptools import setup, find_packages

setup(
    name='msiAlign',
    version='0.1',
    packages=find_packages(),
    url='https://github.com/weimin-liu/msiAlign',
    install_requires=[
        'numpy',
        'pillow',
    ]
)