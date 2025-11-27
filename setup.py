"""
Скрипт установки и упаковки приложения.
"""
from setuptools import setup, find_packages
from pathlib import Path

# Чтение README для длинного описания
readme_file = Path(__file__).parent / "README.md"
long_description = ""
if readme_file.exists():
    with open(readme_file, "r", encoding="utf-8") as f:
        long_description = f.read()

setup(
    name="voice-input-utility",
    version="1.0.0",
    description="Утилита голосового ввода для Windows с распознаванием речи",
    long_description=long_description,
    long_description_content_type="text/markdown",
    author="Voice Input Utility",
    packages=find_packages(),
    install_requires=[
        "PyAudio==0.2.14",
        "vosk==0.3.45",
        "pywin32==306",
        "pystray==0.19.5",
        "keyboard==0.13.5",
        "Pillow==10.1.0",
    ],
    python_requires=">=3.8",
    entry_points={
        "console_scripts": [
            "voice-input=src.main:main",
        ],
    },
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: End Users/Desktop",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Operating System :: Microsoft :: Windows",
    ],
)

