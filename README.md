**Version 0.3.1**

# Mod9 ASR Python Wrappers

By default, requests to the Mod9 ASR Engine TCPServer must be through a TCP socket.
The *Mod9 ASR Python wrappers*  are a set of wrappers for the Engine that provide another interface.

Included are a fully-compatible drop-in replacement for the
[Google Cloud STT Python Client Library](https://cloud.google.com/speech-to-text/docs/libraries#client-libraries-install-python),
as well as for the
[Google Cloud STT REST API](https://cloud.google.com/speech-to-text/docs/reference/rest).

For tutorials, please refer to the documentation at
[mod9.io/python-sdk](https://mod9.io/python-sdk)
and
[mod9.io/rest-api](https://mod9.io/rest-api),
respectively.

There are a few methods to install the Mod9 ASR Python Wrappers.
To install the Mod9 ASR Python wrappers using PyPI, use
```
pip3 install mod9-asr
```
which will retrieve the necessary files from PyPI and install.

Alternatively, if you have the source code, you can navigate to the
`wrappers/python/` directory containing the `setup.py` file
and run
```
pip3 install .
```
