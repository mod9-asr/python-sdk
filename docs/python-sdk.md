<!--NOTE: This is only expected to properly render correctly as Github-flavored Markdown.-->

[Reference Docs](http://mod9.io/docs) | [Operator Manual](http://mod9.io/operator-manual) | [Python SDK](http://mod9.io/python-sdk) | [REST API](http://mod9.io/rest-api) | [Custom Grammar](http://mod9.io/custom-grammar)

**Version 0.6.0**, last updated November 13, 2020.

# Mod9 ASR Python SDK

By default, requests to the Mod9 ASR Engine TCPServer must be through a TCP socket.
The *Mod9 ASR Python SDK* is a wrapper for the Engine that provides another interface.
Designed to be a fully-compatible drop-in replacement for the
[Google Cloud STT Python Client Library](https://cloud.google.com/speech-to-text/docs/libraries#client-libraries-install-python),
it also extends functionality beyond that offered by Google
(see also Google's
[API](https://googleapis.dev/python/speech/latest/gapic/v1p1beta1/api.html) and
[type](https://googleapis.dev/python/speech/latest/gapic/v1p1beta1/types.html) references).
It is a lightweight wrapper built using Python standard libraries.

A few important differences between the Mod9 ASR Python SDK and the
Google Cloud STT Python Client Library are as follows:
1. Google will only accept audio files of 60 seconds
   or less using the `RecognitionAudio.content` input field, while
   *the Mod9 Python SDK does not limit the duration of audio inputs*.
1. Similarly, Google's synchronous `recognize()` SpeechClient method only
   accepts audio files of duration 60 seconds or less, while *the Mod9
   Python SDK does not limit the duration of audio accepted by the
   synchronous `recognize()` method*.
1. The other audio input method, via `RecognitionAudio.uri`,
   only accepts files stored on Google Cloud Storage when
   using Google's service.
   In contrast, the *Mod9 ASR Python SDK accepts files from a variety
   of storage backends*:

   | Prefix    | Access files stored on... |
   | --------- | ------------------------- |
   | `file://` | the local filesystem. |
   | `gs://`   | Google Cloud storage. |
   | `http://` | the public internet. |
   | `s3://`   | AWS S3. |

1. Google currently supports a variety of audio encodings.
   The Mod9 ASR Python SDK supports 16-bit linear PCM,
   8-bit μ-law, and 8-bit A-law encodings.
1. The Mod9 ASR Python SDK wrapper does not currently support the
   asynchronous `long_running_recognize()` method. It is planned
   to be supported in the future. Until then, please consider
   using the
   [Mod9 ASR REST API wrapper](http://mod9.io/rest).

## Quickstart
First, install the Mod9 ASR Python SDK wrapper:
```bash
pip3 install mod9-asr
```

Transcription using the Mod9 ASR Python SDK requires a
connection to an instance of the Mod9 ASR Engine TCPServer.
The following example uses the [mod9.io](http://mod9.io)
evaluation server, provided for convenience of development
and testing.
Sensitive data should not be sent the the evaluation server,
as the connection is unencrypted.

To transcribe an audio file that is
accessible via HTTP, run the following Python code:
```python
from mod9.asr.speech import SpeechClient

client = SpeechClient(host='mod9.io', port=9900)

transcripts = client.recognize(
    config={
        'language_code': 'en-US',
        'sample_rate_hertz': 8000,
    },
    audio={'uri': 'https://rmtg.co/hey.wav'},
)

print(transcripts)
```

The Python code above first instantiates a `SpeechClient` object
with arguments `host` and `port` that tell the
client where to look for the Mod9 ASR Engine TCPServer.
`SpeechClient` has methods that mimic Google's
[`recognize()`](https://googleapis.dev/python/speech/latest/gapic/v1p1beta1/api.html#google.cloud.speech_v1p1beta1.SpeechClient.recognize)
 and
[`streaming_recognize()`](https://googleapis.dev/python/speech/latest/gapic/v1p1beta1/api.html#google.cloud.speech_v1p1beta1.SpeechClient.streaming_recognize)
methods.
The synchronous `recognize()` method, used above,
transcribes the entire audio file before returning.
The `streaming_recognize()` method instead returns a generator,
so results from early in the audio file are yielded as they
are transcribed.

As seen in the Python code above, the `recognize()` method takes
a `config` and an `audio` argument.

The `config` argument is a `dict` or Google
[`RecognitionConfig`](https://googleapis.dev/python/speech/latest/gapic/v1p1beta1/types.html#google.cloud.speech_v1p1beta1.types.RecognitionConfig)
object that contains metadata about the audio input as well as
options for the Engine that control its output
(see [list of supported options below](/#supported-configuration-options)).
In the simple example above, no options to control the output
are requested, and the `config` argument merely specifies
metadata about the audio.

The `recognize()` method also requires an `audio` argument,
which is a `dict` or Google
[`RecognitionAudio`](https://googleapis.dev/python/speech/latest/gapic/v1p1beta1/types.html#google.cloud.speech_v1p1beta1.types.RecognitionAudio)
object that contains either `.content` or `.uri`.
`.content` holds the byte-encoded audio directly.
`.uri` holds a reference to the location the audio is stored.
In the example code above, the file is retrieved from the public
internet, but a variety of backends are supported
(see [table above](#mod9-asr-python-sdk)).
For example, audio files stored locally can be transcribed using
the `file://` prefix as `file:///path/to/audio.wav`.
The output from `recognize()` is a Google
[`RecognizeResponse`](https://googleapis.dev/python/speech/latest/gapic/v1p1beta1/types.html#google.cloud.speech_v1p1beta1.types.RecognizeResponse)
object that contains zero or more sequential
[`SpeechRecognitionResult`](https://googleapis.dev/python/speech/latest/gapic/v1p1beta1/types.html#google.cloud.speech_v1p1beta1.types.SpeechRecognitionResult)s.

## Supported configuration options

The Mod9 ASR Python SDK comes in two parts: one that supports a
strict subset of Google's functionality, `mod9.asr.speech`, and
a second that additionally supports Mod9-exclusive functionality,
`mod9.asr.speech_mod9`.
The configuration options supported are tabulated below:
| `config` option name            | Accepted values                   | Mod9 exclusive? | Google documentation |
| ------------------------------- | --------------------------------- | --------------- | -------------------- |
| `encoding`                      | `"LINEAR16"`, `"MULAW"`, `"ALAW"` | `"ALAW"`        | [link](https://googleapis.dev/python/speech/latest/gapic/v1p1beta1/types.html#google.cloud.speech_v1p1beta1.types.RecognitionConfig.encoding) |
| `sample_rate_hertz`             | `8000`, `16000`                   | No              | [link](https://googleapis.dev/python/speech/latest/gapic/v1p1beta1/types.html#google.cloud.speech_v1p1beta1.types.RecognitionConfig.sample_rate_hertz) |
| `language_code`                 | `en-US`                           | No              | [link](https://googleapis.dev/python/speech/latest/gapic/v1p1beta1/types.html#google.cloud.speech_v1p1beta1.types.RecognitionConfig.language_code) |
| `max_alternatives`              | `0` <= Integer <=` 30`            | No              | [link](https://googleapis.dev/python/speech/latest/gapic/v1p1beta1/types.html#google.cloud.speech_v1p1beta1.types.RecognitionConfig.max_alternatives) |
| `enable_word_time_offsets`      | `False`, `True`                   | No              | [link](https://googleapis.dev/python/speech/latest/gapic/v1p1beta1/types.html#google.cloud.speech_v1p1beta1.types.RecognitionConfig.enable_word_time_offsets) |
| `enable_word_confidence`        | `False`, `True`                   | No              | [link](https://googleapis.dev/python/speech/latest/gapic/v1p1beta1/types.html#google.cloud.speech_v1p1beta1.types.RecognitionConfig.enable_word_confidence) |
| `enable_automatic_punctuation`  | `False`, `True`                   | No              | [link](https://googleapis.dev/python/speech/latest/gapic/v1p1beta1/types.html#google.cloud.speech_v1p1beta1.types.RecognitionConfig.enable_automatic_punctuation) |
| `max_phrase_alternatives`       | `1` <= Integer <= `100`           | Yes             | N/A, see [Mod9 docs](http://mod9.io:8080/docs?#:~:text=phrase-alternatives) |

## Example usage

The examples below use several command-line tools:
* Required
    * `pip3`: Python's package manager.
* Optional
    * `docker`: used to run a local, containerized Mod9 ASR Engine TCPServer.
       Not needed for steps below that rely on the [mod9.io](http://mod9.io) Engine
       evaluation server.
       To install, follow instructions at
       [docs.docker.com/get-docker](https://docs.docker.com/get-docker).
    * `wget`: a command-line HTTP client,
       used for downloading example files.

### Install the Mod9 ASR Python SDK wrapper (required)
Install the Mod9 ASR Python wrappers, including the ASR Python SDK wrapper from PyPI:
```bash
pip3 install mod9-asr
```

#### Run a container of the Mod9 ASR Engine TCPServer (optional)
To get access to the Mod9 ASR Engine TCPServer Docker image contact sales@mod9.com.
If you have access, pull the latest image:
```bash
docker pull mod9/asr
```
This image can be run as a Docker container locally on your personal Windows/Mac computer
(via [docker.com/products/docker-desktop](https://www.docker.com/products/docker-desktop))
or on a remote Linux server that is accessible via TCP.
Note that transport encryption is not provided by the Engine, so
a remote server should be accessible only to an internal network,
or otherwise wrapped to provide security (e.g. see
[aws.amazon.com/elasticloadbalancing](https://aws.amazon.com/elasticloadbalancing)).
Below, there are example calls to an Engine running locally,
but also to the [mod9.io](http://mod9.io) Engine evaluation server.
Sensitive data should not be posted to the [mod9.io](http://mod9.io)
Engine evaluation server as no attempt is made to provide data
privacy or transport encryption.
Additionally, as this is a service provided for convenience
of evaluation to Mod9 customers, there is no SLA.

The Engine has models for audio with two audio sample rates: 8kHz and 16kHz.
Models can be loaded when the Engine starts or during run time.
The Engine is exposed on port 9900 and loads the 8kHz model on start by default:
```bash
docker run -d --name=mod9-asr -p 9900:9900 mod9/asr
```
Most of the examples below use example audio files with a rate of 16kHz,
so that model is loaded in the example below:
```bash
docker run -d --name=mod9-asr -p 9900:9900 mod9/asr ./asr-engine 16k
```
Multiple models can be loaded at start time as follows:
```bash
docker run -d --name=mod9-asr -p 9900:9900 mod9/asr ./asr-engine 8k 16k
```

The Engine may take up to 30 seconds to start up.
Clients should wait until the Engine has completed start up.
The Engine outputs logs that can be followed using:
```bash
docker logs -f mod9-asr
```
The Engine indicates readiness with a message similar to
"Ready to serve client connections...".

### Setup to test Google Cloud STT Python Client Library (optional, for comparison purposes)

Google Cloud credentials are required for comparisons between
Google and the Mod9 ASR Python SDK wrapper.
Load your own (with STT permissions), or load the demo credentials.
Note that these demo credentials are provided by Mod9 for convenience
of testing and are shared with multiple customers.
Sensitive data should not be posted using the demo credentials.
In addition, the demo credentials have usage rate limits, and so
may not always work.
Download the demo credentials
[here](http://mrp-dev.s3.amazonaws.com/share/wrappers/gstt-demo-credentials.json).
The line below will load and enable the demo credentials.
```bash
export GOOGLE_APPLICATION_CREDENTIALS=gstt-demo-credentials.json
```

### Synchronous transcription using the `recognize()` method
Each request to the Mod9 ASR Python SDK wrapper or Google Cloud Python
Client Library consists of two Python objects:

| Object type                     | Description |
| ------------------------------- | ----------- |
| `RecognitionConfig` (or `dict`) | Contains metadata about the audio, such as the sample rate, as well as options for the Engine (or Google), such as whether to output word-level confidence estimates or the time interval over which a word is spoken. |
| `RecognitionAudio` (or `dict`)  | Consists of either a `.content` field, containing a byte-string of the audio data, or a `.uri` field, which indicates an audio file's location (for Google: `gs://` only; for Mod9: `file://`, `gs://`, `http://`, or `s3://`, see [table above](#mod9-asr-python-sdk)). |

The synchronous `recognize()` method provides the simplest means
of accessing the Engine through the wrapper.
Unfortunately, Google restricts the duration of audio
accepted at this endpoint to 60 seconds or less.
The Mod9 ASR Python SDK wrapper does not restrict the duration of
accepted audio at the synchronous endpoint, allowing for simpler access
to ASR transcription for use cases that have audio longer than 60
seconds and do not require an asynchronous response.

The following lines download a Google sample script to interact
with the synchronous `recognize()` method and a short example audio clip,
`greetings.wav`, whose ground truth transcript is
"greetings world", to be used in the following examples.
```bash
wget https://raw.githubusercontent.com/googleapis/python-speech/master/samples/snippets/transcribe.py
wget rmtg.co/greetings.wav
```

Google's `transcribe.py` script will import a `speech` submodule from `google.cloud`.
By changing that import line alone, the Mod9 ASR Python SDK can be
used as a drop-in replacement in code written for the Google Cloud STT
Python Client library:
```bash
sed 's/from google.cloud import speech/from mod9.asr import speech/' transcribe.py > transcribe_mod9.py
diff -u transcribe{,_mod9}.py
```

To further demonstrate flexibility and simplicity,
the synchronous `recognize()` method may also be tested with a longer file.
This 8kHz telephone recording can be downloaded along with another Google example script that performs automatic punctuation.
As before, we modify the import lines to use the Mod9 ASR Python SDK:
```bash
wget rmtg.co/switchboard-70s.wav
wget https://raw.githubusercontent.com/googleapis/python-speech/master/samples/snippets/transcribe_auto_punctuation.py
sed 's/from google.cloud import speech/from mod9.asr import speech/' transcribe_auto_punctuation.py > transcribe_auto_punctuation_mod9.py
diff -u transcribe_auto_punctuation{,_mod9}.py
```
(Alternatively, the `sample_rate_hertz` parameter in the previous `transcribe.py`
script could be changed to `8000` to match this example file's sample rate.)


#### Mod9 ASR Python SDK wrapper
The Python SDK wrapper connects to the Engine backend using two
environmental variables, `MOD9_ASR_ENGINE_HOST` and
`MOD9_ASR_ENGINE_PORT`, which have defaults of `localhost` and
`9900`, respectively.
With the import-modified Google `transcribe_mod9.py` created
in the
[section above](/#synchronous-transcription-using-the-recognize-method),
transcribe the `greetings.wav` example audio file, using the
[mod9.io](http://mod9.io) Engine evaluation server
(note again that sensitive data should not be posted to the
[mod9.io](http://mod9.io) Engine evaluation server):
```bash
MOD9_ASR_ENGINE_HOST=mod9.io python3 transcribe_mod9.py greetings.wav
```

Or instead using a locally-run Docker image of the Engine:
```bash
python3 transcribe_mod9.py greetings.wav
```

While Google requires audio submitted to the synchronous `recognize()`
method to be 60 seconds or less in duration, audio duration is not
limited by the Mod9 ASR Python SDK wrapper. The following optional test
submits audio that is 70 seconds in duration:
```bash
MOD9_ASR_ENGINE_HOST=mod9.io python3 transcribe_auto_punctuation_mod9.py switchboard-70s.wav
```

#### Google Cloud STT Python Client Library (optional, for comparison purposes)
With Google Cloud credentials exported, compare the response
of Google to that of the Mod9 ASR Python SDK above:
```bash
python3 transcribe.py greetings.wav
```

However, Google limits audio submitted to the synchronous `recognize()`
method to be 60 seconds or less in duration, and so the following optional
test, submitting a 5-minute duration audio file to Google, will fail:
```bash
python3 transcribe_auto_punctuation.py switchboard-70s.wav
```

### Streaming transcription using the `streaming_recognize()` method
The Mod9 ASR Python SDK wrapper also supports a streaming method,
in which partial results are returned in real time.

As above for synchronous recognition, a streaming recognition code
can be easily ported from Google to use the Mod9 ASR Python
SDK with a one-line `import` replacement.
Get a Google streaming test file:
```bash
wget https://raw.githubusercontent.com/googleapis/python-speech/master/samples/microphone/transcribe_streaming_mic.py
```

Altering the import line is sufficient to change the backend to the Mod9 ASR Engine TCPServer:
```bash
sed 's/from google.cloud import speech/from mod9.asr import speech/' transcribe_streaming_mic.py > transcribe_streaming_mic_mod9.py
diff -u transcribe_streaming_mic{,_mod9}.py
```

The `transcribe_streaming_mic.py` script depends on PyAudio, which itself depends on PortAudio.
These are easy to install, but installation is platform dependent.
See the [PyAudio webpage](http://people.csail.mit.edu/hubert/pyaudio/) for installation instructions.

#### Mod9 ASR Python SDK wrapper
As mentioned previously,
the Python SDK wrapper connects to the Engine backend using two
environmental variables, `MOD9_ASR_ENGINE_HOST` and
`MOD9_ASR_ENGINE_PORT`, which have defaults of `localhost` and
`9900`, respectively.
Using the import-modified Google
`transcribe_streaming_mic_mod9.py` created in the
[section above](/#streaming-transcription-using-the-streaming_recognize-method),
transcribe the input in real-time, from the client's microphone input,
using the [mod9.io](http://mod9.io) Engine evaluation server
(note again that sensitive data should not be posted to the
[mod9.io](http://mod9.io) Engine evaluation server):
```bash
MOD9_ASR_ENGINE_HOST=mod9.io python3 transcribe_streaming_mic_mod9.py
```

Or instead using a locally-run Docker image of the Engine:
```bash
python3 transcribe_streaming_mic_mod9.py
```

#### Google Cloud STT Python Client Library (optional, for comparison purposes)
With Google Cloud credentials exported, compare the response
of Google to that of the Mod9 ASR Python SDK above:
```bash
python3 transcribe_streaming_mic.py
```
