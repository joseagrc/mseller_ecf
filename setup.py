from setuptools import find_packages, setup

from mseller_ecf import __version__ as version

with open("requirements.txt") as f:
    install_requires = f.read().strip().splitlines()

setup(
    name="mseller_ecf",
    version=version,
    description="Frappe/ERPNext integration for MSeller e-CF electronic invoicing",
    author="MSeller ECF Integration",
    author_email="support@example.com",
    packages=find_packages(),
    zip_safe=False,
    include_package_data=True,
    install_requires=install_requires,
)
