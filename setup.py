#!/usr/bin/env python3

import setuptools

with open('README.md') as f_in:
    long_description = f_in.read()

install_requires = [
    'boto3>=1.16.5',
    'flask-restful>=0.3.8',
    'google-auth>=1.22.1',
    'google-cloud-speech>=2.0.0',
    'google-resumable-media>=1.1.0',
    'proto-plus>=1.8.0',
]

setuptools.setup(
    name='mod9-asr',
    version='0.1.0',
    description='Wrappers over Mod9 ASR Engine TCP Server.',
    long_description=long_description,
    long_description_content_type='text/markdown',
    author='Mod9 Technologies',
    author_email='support@mod9.com',
    license='BSD 2-Clause',
    url='http://mod9.io/python-sdk',
    # TODO: classifiers?
    # TODO: platforms?
    packages=setuptools.PEP420PackageFinder.find(),
    # TODO: namespace_packages?
    install_requires=install_requires,
    # TODO: extras_require?
    # TODO: python_requires?
    # TODO: scripts?
    # TODO: include_package_data?
    # TODO: zip_safe?

    # Installs executable under user's PATH.
    entry_points={
        'console_scripts': ['mod9-rest-server = mod9.rest.server:main'],
    },
)
