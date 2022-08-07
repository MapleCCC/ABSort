import setuptools

from absort import __version__

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setuptools.setup(
    name="ABSort",
    author="MapleCCC",
    author_email="littlelittlemaple@gmail.com",
    description="A command line utility to sort Python source code by abstraction levels",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/MapleCCC/ABSort",
    version=__version__,
    packages=setuptools.find_packages(),
    license="MIT",
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    python_requires=">=3.10",
    install_requires=open("requirements/install.txt", "r").read().splitlines(),
    entry_points={"console_scripts": ["absort=absort.__main__:main"]},
)
