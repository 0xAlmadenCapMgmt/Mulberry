from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setup(
    name="financial-analysis",
    version="0.2.0",
    author="Financial Analysis Team",
    description="Fundamental value analysis and report generator",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/yourusername/financial-analysis",
    packages=find_packages(),
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Financial and Insurance Industry",
        "Topic :: Office/Business :: Financial :: Investment",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
    ],
    python_requires=">=3.9",
    install_requires=[
        "click>=8.1.0",
        "rich>=13.0.0",
        "pandas>=2.0.0",
        "numpy>=1.24.0",
        "yfinance>=0.2.0",
        "plotly>=5.18.0",
        "jinja2>=3.1.0",
        "sqlalchemy>=2.0.0",
        "python-dotenv>=1.0.0",
        "pyyaml>=6.0",
        "requests>=2.31.0",
        "python-dateutil>=2.8.0",
    ],
    extras_require={
        "dev": [
            "pytest>=7.4.0",
            "pytest-asyncio>=0.21.0",
            "pytest-cov>=4.1.0",
        ],
    },
    entry_points={
        "console_scripts": [
            "fa=financial_analysis.cli:cli",
        ],
    },
    include_package_data=True,
    package_data={
        "financial_analysis": ["templates/*.html"],
    },
)
