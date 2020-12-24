import setuptools
from idmyteam import __version__

setuptools.setup(
    version=__version__,
    name="idmyteam",
    description="Base django files for idmyteam-client and idmyteam-server",
    url="https://idmy.team/",
    author="Maximilian Mitchell",
    author_email="max@max.me.uk",
    license="BSD-3-Clause",
    include_package_data=True,
    packages=setuptools.find_packages(),
)
