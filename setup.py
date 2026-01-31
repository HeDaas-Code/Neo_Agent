#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Neo Agent - Setup Script
"""

from setuptools import setup, find_packages
import os

# Read README for long description
with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

# Read requirements
with open("requirements.txt", "r", encoding="utf-8") as fh:
    requirements = [line.strip() for line in fh if line.strip() and not line.startswith("#")]

# Read version from src/__init__.py
version = {}
with open(os.path.join("src", "__init__.py"), "r", encoding="utf-8") as fh:
    for line in fh:
        if line.startswith("__version__"):
            exec(line, version)
            break

setup(
    name="neo-agent",
    version=version.get("__version__", "1.0.0"),
    author="HeDaas-Code",
    author_email="",
    description="智能对话代理系统 - A LangChain-based intelligent conversation agent system",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/HeDaas-Code/Neo_Agent",
    packages=find_packages(exclude=["tests", "examples"]),
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "Topic :: Software Development :: Libraries :: Python Modules",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
    ],
    python_requires=">=3.8",
    install_requires=requirements,
    entry_points={
        "console_scripts": [
            "neo-agent=main:main",
        ],
    },
    include_package_data=True,
    zip_safe=False,
)
