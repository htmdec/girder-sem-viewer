from pathlib import Path

from setuptools import find_packages, setup

this_directory = Path(__file__).parent
long_description = (this_directory / "README.md").read_text()

setup(
    name="girder-sem-viewer",
    long_description=long_description,
    long_description_content_type="text/markdown",
    version="2.2.2",
    description="Girder Plugin enabling preview of SEM data.",
    packages=find_packages(),
    include_package_data=True,
    license="BSD-3-Clause",
    classifiers=[
        "Development Status :: 4 - Beta",
        "Environment :: Web Environment",
        "License :: OSI Approved :: BSD License",
        "Operating System :: POSIX :: Linux",
        "Programming Language :: Python",
        "Programming Language :: Python :: 3",
    ],
    python_requires=">=3.10",
    setup_requires=["setuptools-git"],
    install_requires=["girder>=5.0.0a5.dev0", "pillow", "python-magic", "numpy"],
    entry_points={"girder.plugin": ["sem_viewer = girder_sem_viewer:SemViewerPlugin"]},
    zip_safe=False,
)
