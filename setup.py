from setuptools import setup, find_packages

setup(
    name="eveterminal",
    version="1.0.0",
    description="Multi-tab & tiled terminal client for EVE-NG, GNS3, and Cisco network labs",
    author="EveTerminal Developers",
    packages=find_packages(),
    scripts=["bin/eveterminal", "bin/securecrt-linux"],
    install_requires=[
        "PyQt6>=6.4.0",
        "paramiko>=2.10.0",
        "pyserial>=3.5",
    ],
    classifiers=[
        "Programming Language :: Python :: 3",
        "Operating System :: POSIX :: Linux",
        "Topic :: Terminals :: Terminal Emulators/X Terminals",
        "Topic :: System :: Networking",
    ],
    python_requires=">=3.9",
)
