# ImgSpc-PMT. Copyright 2020 Imaginary Spaces. All Rights Reserved.

from setuptools import find_packages, setup

setup(
    name="PMT",
    version="0.3",
    description="The Imaginary Spaces PMT",
    author="Imaginary Spaces",
    author_email="info@imgspc.com",
    url="https://github.com/imgspc/PMT",
    packages=find_packages(),
    zip_safe=False,
    entry_points={
        "console_scripts": [
            "pmt_dump = pmt.pmt:dump",
            "pmt_read = pmt.pmt:read",
            "script_to_UE4 = connectors.screenplay_to_unreal_project:main",
            "sg_writer = writers.ShotgunWriter.pmt.shotgun.shotgun_writer:main",
        ],
    },
    include_package_data=True,
    install_requires=[
        "appdirs",
        "shotgun_api3@git+git://github.com/shotgunsoftware/python-api.git#egg=shotgun_api3",
    ],
)
