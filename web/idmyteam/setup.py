import setuptools
import os

version = os.getenv("VERSION")
if not version:
    print("missing VERSION env variable")
    quit(1)

setuptools.setup(
    name="idmyteam",
    description="Base django files for idmyteam-client and idmyteam-server",
    version=version,
    url="https://idmy.team/",
    author="Maximilian Mitchell",
    author_email="max@max.me.uk",
    license="BSD-3-Clause",
    include_package_data=True,
    packages=setuptools.find_packages()
)
