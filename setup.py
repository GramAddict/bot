import setuptools

with open("GramAddict/version.py", "r") as f:
    cur_version = f.read().split('"')[1]
with open("requirements.txt", "r") as f:
    requirements_list = [x.rstrip() for x in f]
with open("README.md", "r", errors="ignore") as readme:
    long_description = readme.read()
setuptools.setup(
    name="gramaddict",
    version=cur_version,
    author="GramAddict Team",
    author_email="maintainers@gramaddict.org",
    description="Completely free and open source human-like Instagram bot. Powered by UIAutomator2 and compatible with basically any android device that can run instagram - real or emulated.",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/GramAddict/bot/",
    packages=setuptools.find_packages(),
    include_package_data=True,
    install_requires=requirements_list,
    classifiers=[
        "Programming Language :: Python :: 3.6",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Operating System :: OS Independent",
    ],
    python_requires=">=3.6",
)
