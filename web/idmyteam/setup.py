from setuptools import setup
import os

version = os.getenv("VERSION")
if not version:
    print("missing VERSION env variable")
    quit(1)


setup(include_package_data=True, version=version)
