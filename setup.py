import setuptools

with open("README.md", "r", errors="ignore") as readme:
    long_description = readme.read()

setuptools.setup(
    name="gramaddict",
    version="1.3",
    author="GramAddict Team",
    author_email="maintainers@gramaddict.org",
    description="Completely free and open source human-like Instagram bot. Powered by UIAutomator2 and compatible with basically any android device that can run instagram - real or emulated.",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/GramAddict/bot/",
    packages=setuptools.find_packages(),
    include_package_data=True,
    install_requires=[
        "colorama==0.4.3",
        "ConfigArgParse==1.2.3",
        "matplotlib==3.3.3",
        "numpy==1.19.3",
        "PyYAML==5.3.1",
        "uiautomator2==2.13.2",
        "urllib3==1.26.2",
        "emoji==1.2.0",
    ],
    classifiers=[
        "Programming Language :: Python :: 3.6",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Operating System :: OS Independent",
    ],
    python_requires=">=3.6",
)
