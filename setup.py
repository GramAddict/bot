import setuptools

with open("GramAddict/version.py", "r") as f:
    cur_version = f.read().split('"')[1]
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
    install_requires=[
        "colorama==0.4.4",
        "ConfigArgParse==1.4",
        "numpy>=1.19.5,<=1.20.3",
        "PyYAML==5.4",
        "uiautomator2==2.16.0",
        "urllib3==1.26.5",
        "emoji==1.2.0",
        "langdetect==1.0.9",
    ],
    extras_require={
        "telegram-reports": ["pandas==1.2.4"],
        "analytics": ["matplotlib==3.4.2"],
    },
    classifiers=[
        "Programming Language :: Python :: 3.6",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Operating System :: OS Independent",
    ],
    python_requires=">=3.6",
)
