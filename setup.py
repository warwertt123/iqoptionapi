"""The python wrapper for IQ Option API package setup."""
from setuptools import (setup, find_packages)

setup(
    name="iqoptionapi",
    version="3.9.5",
    packages=find_packages(),
    install_requires=["pylint","requests","websocket-client==0.47"],
    include_package_data = True,
    description="Best IQ Option API for python",
    long_description="Best IQ Option API for python",
    url="https://github.com/Lu-Yi-Hsun/iqoptionapi",
    author="Lu-Yi-Hsun",
    author_email="yihsun1992@gmail.com",
    zip_safe=False
)
