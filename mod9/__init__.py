"""
Python SDK and REST wrappers for the Mod9 ASR Engine TCP Server.

Requires a Mod9 ASR Engine TCP server backend to work. Contact
sales@mod9.com for licensing inquiries.

More documentation and example usage can be found at
http://mod9.io/python-sdk and http://mod9.io/rest

Within you will find a number of modules. A brief summary of wrappers
follows.

``mod9.asr`` implements Python SDK wrappers around the Mod9 ASR Engine
TCP Server. Two wrappers are currently offered within this module, both
of which are drop-in replacements for the Google STT Python Client
Library. The first, ``mod9.asr.speech``, uses Google's objects for input
and output and offers a strict subset of Google functionality. The
second, ``mod9.asr.speech_mod9``, extends Google's functionality with
Mod9-exclusive options, such as phrase alternatives.

``mod9.rest.server`` implements the Mod9 ASR REST API, a
fully-compatible drop-in replacement for the Google Cloud STT REST API.
Run ``mod9-rest-server`` from the command line to launch a REST server.
This is a script which ``pip` installs. Note that on some environments,
``pip`` may not install the script within the users path; it will emit
a warning at install time if this is the case. Please see
http://mod9.io/rest for more information about the Mod9 ASR REST API
server.

``mod9.reformat`` contains the internals that power these wrappers. For
example, ``mod9.reformat.google`` converts input and output between Mod9
and Google forms and ``mod9.reformat.utils`` handles communicating with
the Mod9 ASR Engine TCP Server.
"""
