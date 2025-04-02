from setuptools import setup, find_packages

with open("README.md", "r") as fh:
    long_description = fh.read()

setup(
    name="code-reviewer-tool",
    version="0.1.0",
    author="Shreyas",
    author_email="shreyasrd31@gmail.com",
    description="A tool for code review and documentation generation",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/SRDdev/CodeReviewer",
    packages=find_packages(),
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License", 
        "Operating System :: OS Independent",
    ],
    python_requires='>=3.6',
    install_requires=[
        "astroid",
        "pylint",
        "sphinx",
        "sphinx-rtd-theme",
        "docutils"
    ],
    entry_points={
        'console_scripts': [
            'code-reviewer = code_reviewer.main:main', 
        ],
    },
)
