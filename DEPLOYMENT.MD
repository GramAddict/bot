# Process for Deploying Releases

- Make sure you are in the `master` branch and do a `git pull` prior to continuing
- Ensure version number in both `__version__.py` and `setup.py` are both set to the new version number, without any `b` designation. e.g. 1.2.0, 1.2.1
- Ensure you have `twine` installed
- Remove any existing distribution data: `rm -rf dist/ gramaddict.egg-info/`
- Run the command: `python3 setup.py sdist`
- Run the command: `twine upload dist/*`
