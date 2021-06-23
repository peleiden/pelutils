# Contributing

- Make your changes and add tests as necessary.
- Make sure tests pass on Python 3.7 using `pytest --cov=pelutils`.
- Optionally add an example to `examples`.
- Briefly describe changes in `HISTORY.md`.
- Commit changes and make sure that the commit references the issue(s) that have been solved.
- Make a pull request into `master`.

# Updating Version on PyPi

Run the following commands to update version on PyPi.

```
rm -rf dist
python setup.py sdist bdist_wheel  # Requires 3.8 or later
twine upload dist/*
```

# Install

Install locally by running `pip install -e --upgrade ./` from the root of the repository:
