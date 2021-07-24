#!/usr/bin/env python3

import setuptools

from mod9.reformat import config

with open('README.md') as f_in:
    long_description = f_in.read()

install_requires = [
    'boto3>=1.9.0',
    'flask-restful>=0.3.9',
    'google-auth>=1.22.0',
    'google-cloud-speech>=2.0.0',
    'google-resumable-media>=1.0.0',
    'packaging>=15.0',
    'proto-plus>=1.4.0',
    'websockets>=8.0',
]

setuptools.setup(
    name='mod9-asr',
    version=config.WRAPPER_VERSION,
    description='Mod9 ASR Python SDK, REST API, and Websocket Interface:'
                ' high-level interfaces to the Mod9 ASR Engine.',
    long_description=long_description,
    long_description_content_type='text/markdown',
    author='Mod9 Technologies',
    author_email='support@mod9.com',
    license='BSD 2-Clause',
    url='https://github.com/mod9-asr/python-sdk',
    # TODO: classifiers?
    # TODO: platforms?
    packages=setuptools.PEP420PackageFinder.find(exclude=('test',)),
    # TODO: namespace_packages?
    install_requires=install_requires,
    # TODO: extras_require?
    # TODO: python_requires?
    # TODO: scripts?
    # TODO: include_package_data?
    # TODO: zip_safe?

    # Installs executable under user's PATH.
    entry_points={
        'console_scripts': [
            'mod9-asr-rest-api = mod9.rest.server:main',
            'mod9-asr-websocket-client = mod9.websocket.client:main',
            'mod9-asr-websocket-server = mod9.websocket.server:main',
        ],
    },
)
