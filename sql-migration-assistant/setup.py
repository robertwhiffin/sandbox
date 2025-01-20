from pathlib import Path

from setuptools import setup, find_packages

# Read the version from version.py
version_file = Path("src/sql_migration_assistant/version.py").read_text()
__version__ = "" # This is for the linter to stop complaining about undefined variables
exec(version_file)  # This will define __version__

# Read the requirements.txt file
def load_requirements(filename="requirements.txt"):
    with open(filename, "r") as file:
        return file.read().splitlines()


setup(
    name="sql_migration_assistant",
    use_scm_version={
        "root": "../",  # Specify the parent directory as the Git root
        "relative_to": __file__,  # Ensure paths are resolved relative to this file
    },
    packages=find_packages(where="src"),  # Specify src as the package directory
    package_dir={"": "src"},
    include_package_data=True,  # Include files specified in MANIFEST.in
    package_data={
        "sql_migration_assistant": ["config.yml"],  # Include YAML file
    },
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    install_requires=load_requirements(),
    setup_requires=["setuptools", "setuptools-scm"],
    python_requires=">=3.10",
)
