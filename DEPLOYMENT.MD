# Process for Deploying Betas
- Rename GramAddict folder to GramAddict_beta
- Ensure version number in both `__version__.py` and `setup-beta.py` are both set to the new version number, followed by b\[n\] e.g. 1.2.0b1 or 1.2.1b2
- Ensure you have `twine` installed
- Run the command: `python3 setup-beta.py sdist bdist_wheel`
- Run the command: `twine upload dist/*`

# Process for Deploying Releases
- Rename GramAddict_beta folder to GramAddict (if needed)
- Ensure version number in both `__version__.py` and `setup-beta.py` are both set to the new version number, without any `b` designation. e.g. 1.2.0, 1.2.1
- Ensure you have `twine` installed
- Run the command: `python3 setup-beta.py sdist bdist_wheel`
- Run the command: `twine upload dist/*`