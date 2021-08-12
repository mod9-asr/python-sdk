# Mod9 ASR Python SDK

The *Mod9 ASR Python SDK* is a higher-level interface than the protocol described in the [TCP reference](https://mod9.io/tcp) documentation for the [Mod9 ASR Engine](https://mod9.io).
This software is designed as a compatible drop-in replacement for:

- [Google Cloud STT Python Client Library](https://cloud.google.com/speech-to-text/docs/libraries#client-libraries-install-python)
- [Google Cloud STT REST API](https://cloud.google.com/speech-to-text/docs/reference/rest)

Please refer to
[mod9.io/python](https://mod9.io/python)
and
[mod9.io/rest](https://mod9.io/rest)
for further documentation and examples.

In addition, this package provides a WebSocket interface:
see [mod9.io/websocket](https://mod9.io/websocket) for a demonstration.

To install the Mod9 ASR Python SDK, if an Internet connection is available:
```bash
pip3 install mod9-asr
```

Alternatively, to install from local source:
```bash
tar xzf mod9-asr-$VERSION.tar.gz
pip3 install ./mod9-asr-$VERSION
```
