**Version 0.1.0**, last updated December 14, 2020.

# Mod9 ASR Python Wrappers

By default, requests to the Mod9 ASR Engine TCPServer must be through a TCP socket.
The *Mod9 ASR Python wrappers*  are a set of wrappers for the Engine that provide another interface.

Included are a fully-compatible drop-in replacement for the
[Google Cloud STT Python Client Library](https://cloud.google.com/speech-to-text/docs/libraries#client-libraries-install-python),
as well as for the
[Google Cloud STT REST API](https://cloud.google.com/speech-to-text/docs/reference/rest).

For tutorials, please refer to the documentation at
[mod9.io/python-sdk](http://mod9.io/python-sdk)
and
[mod9.io/rest](http://mod9.io/rest),
respectively.

There are a few methods to install the Mod9 ASR Python Wrappers.

If you have access to the internet, the easiest method is to use
```
pip3 install mod9-asr
```
which will retrieve the necessary files from PyPI and install.

If you have a Python wheel (i.e. a `.whl` file),
for example, named `mod9-asr-0.1.0-py3-none-any.whl`,
you can install it with
```
pip3 install mod9-asr-0.1.0-py3-none-any.whl
```
One way to get this `.whl` file, if you have a Docker image of the
Engine, is to copy the `.whl` from within that Docker image.
For example, if the container is being run with the name
`mod9-asr-8k`, and the current version of the Mod9 ASR Python
Wrappers package is 0.1.0, use
```
docker cp mod9-asr-8k:/opt/mod9/mod9-asr-0.1.0-py3-none-any.whl .
```
to copy the `.whl` onto the bare metal host.

Finally, if you have the source code, you can navigate to the
`wrappers/python/` directory containing the `setup.py` file
and run
```
pip3 install .
```
