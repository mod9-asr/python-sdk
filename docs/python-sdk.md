<!--NOTE: This is only expected to properly render correctly as Github-flavored Markdown.-->

**Python SDK 0.3.1 (Engine 0.8.0)**

# Mod9 ASR Python SDK

The Mod9 ASR Python SDK is a higher-level interface than the custom TCP protocol described in the [reference docs](/docs).
Designed as a compatible drop-in replacement for the
[Google Cloud STT Python Client Library](https://cloud.google.com/speech-to-text/docs/libraries#client-libraries-install-python),
Mod9's software enables privacy-protecting on-premise deployment,
while also extending functionality of the Google Cloud service.

There are some notable differences:
1. Google's
   [`RecognitionAudio.uri`](https://googleapis.dev/python/speech/latest/speech_v1p1beta1/types.html#google.cloud.speech_v1p1beta1.types.RecognitionAudio.uri)
   only allows files to be retrieved from Google Cloud Storage.
   <br>The Mod9 ASR Python SDK accepts audio from more diverse sources:

   | URI Scheme              | Access files stored ...        |
   | ----------------------- | ------------------------------ |
   | `gs://`                 | in Google Cloud Storage,       |
   | `s3://`                 | as AWS S3 objects,             |
   | `http://` or `https://` | via arbitrary HTTP services,   |
   | `file://`               | or on a local filesystem.      |

1. Google's
   [`RecognitionAudio.content`](https://googleapis.dev/python/speech/latest/speech_v1p1beta1/types.html#google.cloud.speech_v1p1beta1.types.RecognitionAudio.content)
   and
   [`SpeechClient.recognize()`](https://googleapis.dev/python/speech/latest/speech_v1p1beta1/speech.html#google.cloud.speech_v1p1beta1.services.speech.SpeechClient.recognize)
   restrict audio to be less than 60 seconds.
   <br>The Mod9 ASR Python SDK does not limit the duration of audio.
1. Google's
   [`SpeechClient.streaming_recognize()`](https://googleapis.dev/python/speech/latest/speech_v1p1beta1/speech.html#google.cloud.speech_v1p1beta1.services.speech.SpeechClient.streaming_recognize)
   restricts audio to be less than 5 minutes.
   <br>The Mod9 ASR Python SDK does not limit the duration of streaming audio.
1. Google's
   [`SpeechClient.long_running_recognize()`](https://googleapis.dev/python/speech/latest/speech_v1p1beta1/speech.html#google.cloud.speech_v1p1beta1.services.speech.SpeechClient.long_running_recognize)
   can asynchronously process longer audio files.
   <br> The Mod9 ASR Python SDK has not replicated this; it's better served with a Google-compatible [Mod9 ASR REST API](/rest-api).
1. Google Cloud STT supports a large number of languages for a variety of acoustic conditions.
   <br>The Mod9 ASR Python SDK only supports US English (8kHz telephone) and Global English (16kHz video).

## Quickstart
Install the Mod9 ASR Python SDK:
```bash
pip3 install mod9-asr
```

To transcribe a sample audio file accessible at [https://mod9.io/hey.wav](https://mod9.io/hey.wav):
```python
from mod9.asr.speech import SpeechClient

client = SpeechClient(host='mod9.io', port=9900)

response = client.recognize(config={'language_code': 'en-US'},
                            audio={'uri': 'https://mod9.io/hey.wav'})

print(response)
```

This Python code instantiates the `SpeechClient` class with arguments that specify
how to connect with a server running the Mod9 ASR Engine.
For convenience, such a server is deployed at `mod9.io`, listening on port `9900`.

**NOTE:** *Sensitive data should not be sent to this evaluation server, because the TCP connection is unencrypted.*

Mod9's implementation of `SpeechClient` replicates Google's
[`recognize()`](https://googleapis.dev/python/speech/latest/speech_v1p1beta1/speech.html#google.cloud.speech_v1p1beta1.services.speech.SpeechClient.recognize)
method, which is synchronous: it processes an entire request before returning a single response.
This is suitable for transcribing pre-recorded audio files.

The `config` argument can be either a Python `dict` or
[`RecognitionConfig`](https://googleapis.dev/python/speech/latest/speech_v1p1beta1/types.html#google.cloud.speech_v1p1beta1.types.RecognitionConfig)
object that contains metadata about the audio input,
as well as [supported configuration options](#supported-configuration-options) that affect the output.

The `audio` argument can be either a Python `dict` or
[`RecognitionAudio`](https://googleapis.dev/python/speech/latest/speech_v1p1beta1/types.html#google.cloud.speech_v1p1beta1.types.RecognitionAudio)
object that contains either `content` or `uri`.
While `content` would represent audio bytes directly, here the `uri` specifies a location where audio may be accessed.

The output from `recognize()` is a
[`RecognizeResponse`](https://googleapis.dev/python/speech/latest/speech_v1p1beta1/types.html#google.cloud.speech_v1p1beta1.types.RecognizeResponse)
that may contain
[`SpeechRecognitionResult`](https://googleapis.dev/python/speech/latest/speech_v1p1beta1/types.html#google.cloud.speech_v1p1beta1.types.SpeechRecognitionResult)
objects.

(Alternatively: the
[`streaming_recognize()`](https://googleapis.dev/python/speech/latest/speech_v1p1beta1/speech.html#google.cloud.speech_v1p1beta1.services.speech.SpeechClient.streaming_recognize)
method would return a generator that yields
[`StreamingRecognitionResult`](https://googleapis.dev/python/speech/latest/speech_v1p1beta1/types.html#google.cloud.speech_v1p1beta1.types.StreamingRecognitionResult)
objects while audio is being sent and processed.
This is more suitable for live audio streams.)


## Supported configuration options

The Mod9 ASR Python SDK provides two modules:
* `mod9.asr.speech` implements a strict subset of Google's functionality.
* `mod9.asr.speech_mod9` extends this with additional functionality that Google does not support.

<!-- Pro-tip: when editing, view this on a widescreen monitor -->
| Option in `config`                                                                                                                                                                                             | Accepted values in<br>`mod9.asr.speech` | Extended support in<br>`speech_mod9` |
| -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | --------------------------------------- | ------------------------------------ |
| [`enable_automatic_punctuation`](https://googleapis.dev/python/speech/latest/speech_v1p1beta1/types.html#google.cloud.speech_v1p1beta1.types.RecognitionConfig.enable_automatic_punctuation)<sup><b>1</b></sup> | `False`, `True`                         |                                      |
| [`enable_word_confidence`](https://googleapis.dev/python/speech/latest/speech_v1p1beta1/types.html#google.cloud.speech_v1p1beta1.types.RecognitionConfig.enable_word_confidence)                                | `False`, `True`                         |                                      |
| [`enable_word_time_offsets`](https://googleapis.dev/python/speech/latest/speech_v1p1beta1/types.html#google.cloud.speech_v1p1beta1.types.RecognitionConfig.enable_word_time_offsets)                            | `False`, `True`                         |                                      |
| [`encoding`](https://googleapis.dev/python/speech/latest/speech_v1p1beta1/types.html#google.cloud.speech_v1p1beta1.types.RecognitionConfig.encoding)                                                            | `"LINEAR16"` `"MULAW"`                  | `"ALAW"`                             |
| [`language_code`](https://googleapis.dev/python/speech/latest/speech_v1p1beta1/types.html#google.cloud.speech_v1p1beta1.types.RecognitionConfig.language_code)                                                  | `"en-US"`                               |                                      |
| [`sample_rate_hertz`](https://googleapis.dev/python/speech/latest/speech_v1p1beta1/types.html#google.cloud.speech_v1p1beta1.types.RecognitionConfig.sample_rate_hertz)                                          | `8000`, `16000`                         |                                      |
| [`max_alternatives`](https://googleapis.dev/python/speech/latest/speech_v1p1beta1/types.html#google.cloud.speech_v1p1beta1.types.RecognitionConfig.max_alternatives)<sup><b>2</b></sup>                         | `1`, ... , `10000`                      |                                      |
| [`max_phrase_alternatives`](https://mod9.io/docs#:~:text=phrase-alternatives)<sup><b>3</b></sup>                                                                                                               | N/A                                     | `1`, ... , `100`                     |
<!--
See https://stackoverflow.com/a/32119820/281536 for clickable footnotes (e.g. for long-range referencing and returning)
However, that looks pretty bad when it's "local" footnotes like this, so don't use the links.
-->
<sup><b>1</b></sup> <b>Mod9 ASR</b>: enabling punctuation also applies capitalization and number formatting.<br>
<sup><b>2</b></sup> <b>Google STT</b>: only recognizes up to 30 transcript-level alternatives (i.e. N-best), often returning just 1 or 2.<br>
<sup><b>3</b></sup> <b>Mod9 ASR</b>: more useful intra-transcript representation, derived with a patent-pending algorithm.<br>

## Setup

Install the Mod9 ASR Python SDK from PyPI:
```bash
pip3 install mod9-asr
```

A Mod9 ASR Engine server is expected to be run locally (i.e. at `localhost`),
listening for TCP connections on port `9900`.
These defaults may be reconfigured with the `MOD9_ASR_ENGINE_HOST` and `MOD9_ASR_ENGINE_PORT` environment variables.

There are several ways to proceed, and some command-line tools are recommended:
* `docker`: used to run the Mod9 ASR Engine locally.  See [docs.docker.com/get-docker](https://docs.docker.com/get-docker).
* `wget`: a command-line HTTP client used to conveniently download example files in a shell environment.


### Connect to the Mod9 ASR Engine
#### Quickstart: use the Mod9 ASR Engine evaluation server
It may be most expedient to use the evaluation server running at `mod9.io`:
```bash
export MOD9_ASR_ENGINE_HOST=mod9.io
```
However, because this TCP transport is unencrypted and traverses the public Internet,
customers are strongly advised that *sensitive data should not be sent to this evaluation server*.
No data privacy is implied, nor service level promised.


#### Recommended: run the Mod9 ASR Engine in a Docker container
The Engine can be run as a Docker container on a Linux system, or on macOS/Windows
using [Docker Desktop](https://www.docker.com/products/docker-desktop).

Pull the latest image:
```bash
docker pull mod9/asr
```

Run a container as a background daemon (`-d`),
named as `engine`, and map its default port `9900` from the host:
```bash
docker run -d --name=engine -p 9900:9900 mod9/asr
```

Its logging and resource usage can be monitored:
```bash
docker logs engine
docker stats engine
```

To forcefully stop (`-f`) and remove this container:
```bash
docker rm -f engine
```

The Engine loads ASR models to recognize audio sampled at 8kHz or 16kHz; these are named `8k` and `16k` respectively.
By default, the Docker image is configured to run with the `8k` model, suitable for "narrowband" telephony applications.
The [example usage](#example-usage) will need 16kHz audio (e.g. from "wideband" video)
which is best recognized with the `16k` model.

Overriding the image's default command as `./asr-engine 8k 16k` will load both models:
```bash
docker run -it --rm --name=engine -p 9900:9900 mod9/asr ./asr-engine 8k 16k
```

The command above also runs this container interactively in the terminal (`-it`)
so that it can be manually interrupted by pressing `Ctrl`+`C`,
causing it to exit and also clean up by removing itself (`--rm`).

Note that loading multiple models will significantly increase memory usage.
<!-- TODO: release this feature (#448)
Models can be loaded when the Engine starts; they can also be loaded and unloaded dynamically by client requests,
[if the operator has enabled this configuration](https://dev.mod9.io/operator-manual#shared-mode).
-->

The container may be accessed locally or as a remote service via TCP.
The Engine does not peform transport encryption,
so this server should be accessible only to a private network or the connection should be layered with SSL/TLS.


#### Advanced: run the Mod9 ASR Engine on bare-metal hardware
The Engine software can run as a statically compiled Linux application, outside of a Docker container.
It can also be specially built to run natively on macOS or Windows.
With suitably memory-optimized models, the Engine can also run well on embedded devices (ARM64).
Contact sales@mod9.com for further details.


### Compare with Google Cloud STT (optional)
This Mod9 ASR Python SDK is designed to emulate the Google Cloud STT Python Client Library,
and we encourage developers to compare our respective software and services side-by-side to ensure compatibility.

Google Cloud credentials are required for such comparisons, so we share
[gstt-demo-credentials.json](https://mod9.io/gstt-demo-credentials.json)
to facilitate testing.
Download and enable these demo credentials by setting an environment variable in your current shell:
```bash
wget mod9.io/gstt-demo-credentials.json
export GOOGLE_APPLICATION_CREDENTIALS=gstt-demo-credentials.json
```

*Sensitive data should not be used with these shared demo credentials*, as it could be seen by other users who are testing.
Rate throttling will prevent abuse of these limited-use credentials, so Google's service may at times be unavailable.


## Example usage

The Mod9 ASR Python SDK is a **drop-in replacement** for the Google Cloud STT Python Client Library.
<br>To demonstrate this compatibility, consider the sample scripts published by Google:
* [transcribe.py](https://github.com/googleapis/python-speech/blob/master/samples/snippets/transcribe.py)
  uses `recognize()` for basic processing of 16kHz audio files.
* [transcribe_auto_punctuation.py](https://github.com/googleapis/python-speech/blob/master/samples/snippets/transcribe_auto_punctuation.py)
  demonstrates an extra `config` option and uses 8kHz audio.
* [transcribe_streaming_mic.py](https://github.com/googleapis/python-speech/blob/master/samples/microphone/transcribe_streaming_mic.py)
  uses `recognize_streaming()` with live audio captured from your microphone.

To download Google's sample scripts with a command-line tool:
```bash
wget raw.githubusercontent.com/googleapis/python-speech/master/samples/snippets/transcribe.py
wget raw.githubusercontent.com/googleapis/python-speech/master/samples/snippets/transcribe_auto_punctuation.py
wget raw.githubusercontent.com/googleapis/python-speech/master/samples/microphone/transcribe_streaming_mic.py
```

Modify lines that call `from google.cloud import speech` to now use `mod9.asr`, for example with a stream editor:
```bash
sed s/google.cloud/mod9.asr/ transcribe.py > transcribe_mod9.py
sed s/google.cloud/mod9.asr/ transcribe_auto_punctuation.py > transcribe_auto_punctuation_mod9.py
sed s/google.cloud/mod9.asr/ transcribe_streaming_mic.py > transcribe_streaming_mic_mod9.py
```

The mod9ified sample scripts are named as `*_mod9.py` and differ only in the import lines. To verify this:
```bash
diff transcribe.py transcribe_mod9.py
```

**The modified scripts do not communicate with Google Cloud**;
the following example usage can even be demonstrated on a laptop with no Interent connection &mdash;
if configured to
[run the Mod9 ASR Engine in a Docker container](#recommended-run-the-mod9-asr-engine-in-a-docker-container)
on `localhost`.


### Transcribe audio files with `recognize()`
Download sample audio files,
[greetings.wav](https://mod9.io/greetings.wav) (2s @ 16kHz)
and
[switchboard-70s.wav](https://mod9.io/switchboard.wav) (70s @ 8kHz):
```bash
wget mod9.io/greetings.wav && wget mod9.io/switchboard-70s.wav
```

Run the modified sample script:
```bash
python3 transcribe_mod9.py greetings.wav
```

If it can [connect to the Mod9 ASR Engine](#connect-to-the-mod9-asr-engine), the script should print
`Transcript: greetings world`.

Google's `recognize()` method only allows audio duration up to 60 seconds.
To demonstrate that Mod9 ASR extends support for longer audio,
run another script (which is also configured for 8kHz and transcript formatting):
```bash
python3 transcribe_auto_punctuation_mod9.py switchboard-70s.wav
```

To [compare with Google Cloud STT (optional)](#compare-with-google-cloud-stt-optional), run the original unmodified scripts:
```bash
python3 transcribe.py greetings.wav
python3 transcribe_auto_punctuation.py switchboard-70s.wav
```
The first script produces the same result as Mod9 ASR; meanwhile, Google STT will fail to processs the longer audio file.


### Trancribe live audio with `streaming_recognize()`
The sample scripts will require
[PortAudio](https://github.com/PortAudio/portaudio)
and
[PyAudio](https://people.csail.mit.edu/hubert/pyaudio/)
for OS-dependent microphone access.
To install on a Mac:
```bash
brew install portaudio && pip3 install pyaudio
```

NOTE: as of February 2021,
[PortAudio is broken by macOS Big Sur updates](https://github.com/PortAudio/portaudio/issues/218#issuecomment-777273669).
Here's a temporary work-around:
```bash
brew uninstall portaudio && brew install portaudio --HEAD && pip3 install pyaudio
```

Running this sample script will record audio from your microphone and print results in real-time:
```bash
python3 transcribe_streaming_mic_mod9.py
```

To [compare with Google Cloud STT (optional)](#compare-with-google-cloud-stt-optional), run the unmodified script:
```bash
python3 transcribe_streaming_mic.py
```

It can be especially helpful to run both of these scripts at the same time, comparing side-by-side in different windows.
Note that the unmodified script using Google STT will eventually disconnect after reaching their 5-minute streaming limit.

## Next steps
See also the [Mod9 ASR REST API](/rest-api),
which can run a Google-compatible service that is accessible to HTTP clients.
<br>This is especially recommended for asynchronous batch-processing workloads,
with a POST followed by GET.

The [reference docs](/docs) describe details of the lower-level TCP protocol that is abstracted by the Python SDK and REST API.
Using this can enable more extensive functionality,
including [user-defined words](/custom-words) and [domain-specific grammar](/custom-grammar).

Advanced configuration of the Mod9 ASR Engine is described in the [operator manual](/operator-manual),
with guidance for deployment.
Contact support@mod9.com for additional assistance.
