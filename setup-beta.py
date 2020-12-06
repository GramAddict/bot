import setuptools

with open("README.md", "r", errors='ignore') as readme:
    long_description = readme.read()

with open("requirements.txt", "r") as req:
    install_requires = [line.rstrip() for line in req]

setuptools.setup(
    name="gramaddict-beta",
    version="1.2.0b1",
    author="GramAddict Team",
    author_email="maintainers@gramaddict.org",
    description="Completely free and open source human-like Instagram bot. Powered by UIAutomator2 and compatible with basically any android device that can run instagram - real or emulated.",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/GramAddict/bot/",
    packages=setuptools.find_packages(),
    install_requires=install_requires,
    classifiers=[
        "Programming Language :: Python :: 3.6",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Operating System :: OS Independent",
    ],
    python_requires='>=3.6',
    include_package_data=True
)