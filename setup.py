import os
from setuptools import setup

setup(
    name = "curatory",
    version = "0.0.1",
    author = "Daniel Waterworth",
    author_email = "daniel@manganizeme.com",
    description = "",
    keywords = "machine-learning labelling",
    url = "https://github.com/danielwaterworth/curatory",
    packages=['curatory', 'curatory.app'],
    long_description="",
    classifiers=[],
    install_requires=['requests', 'flask', 'Flask-Bootstrap', 'sortedcollections'],
    include_package_data=True,
)
