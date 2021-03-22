<!--NOTE: This is only expected to properly render correctly as Github-flavored Markdown.-->

**Version 0.3.0 (Engine 0.8.0)**

# Mod9 ASR REST API

By default, requests to the Mod9 ASR Engine TCPServer must be through a TCP socket.
The *Mod9 ASR REST API* is a wrapper for the Engine that provides another interface.
Designed to be a fully-compatible drop-in replacement for the
[Google Cloud STT REST API](https://cloud.google.com/speech-to-text/docs/reference/rest),
it also extends functionality beyond that offered by Google.
It is a lightweight wrapper built using open-source libraries such as
[Flask-RESTful](https://flask-restful.readthedocs.io).

A few important differences between the Mod9 ASR REST API wrapper and the
Google Cloud STT REST API are:
1. Google will only accept audio files of 60 seconds
   or less using the `audio.content` input field, while *the Mod9 ASR REST
   API does not limit the duration of audio inputs*.
1. Similarly, Google's synchronous `/speech:recognize` endpoint only
   accepts audio files of duration 60 seconds or less, while *the Mod9 ASR
   REST API does not limit the duration of audio accepted at the
   synchronous endpoint*.
1. The other audio input method, via `audio.uri`, only accepts
   files stored on Google Cloud Storage when using Google's service.
   In contrast, the *Mod9 ASR REST API accepts files stored using a
   variety of protocols*:

   | Protocol  | Access files stored on... |
   | --------  | ----------- |
   | `file://` | the filesystem of the host running the ASR REST server. |
   | `gs://`   | Google Cloud Storage. |
   | `http://` | the public internet. |
   | `s3://`   | AWS S3. |

1. Google currently supports a variety of audio encodings.
   The Mod9 ASR REST API supports 16-bit linear PCM,
   8-bit μ-law, and 8-bit A-law encodings.

## Supported configuration options

The Mod9 ASR REST API supports a subset of Google's functionality,
and additionally supports Mod9-exclusive functionality.
The configuration options supported are tabulated below:
| `config` option name           | Accepted values                   | Mod9 exclusive? | Google documentation |
| ------------------------------ | --------------------------------- | --------------- | -------------------- |
| `encoding`                     | `"LINEAR16"`, `"MULAW"`, `"ALAW"` | `"ALAW"`        | [link](https://cloud.google.com/speech-to-text/docs/reference/rest/v1p1beta1/RecognitionConfig#AudioEncoding) |
| `sampleRateHertz`              | `8000`, `16000`                   | No              | [link](https://cloud.google.com/speech-to-text/docs/reference/rest/v1p1beta1/RecognitionConfig#:~:text=Sample%20rate,AudioEncoding.) |
| `languageCode`                 | `en-US`                           | No              | [link](https://cloud.google.com/speech-to-text/docs/reference/rest/v1p1beta1/RecognitionConfig#:~:text=Required.,language%20codes.) |
| `maxAlternatives`              | `0` <= Integer <=` 30`            | No              | [link](https://cloud.google.com/speech-to-text/docs/reference/rest/v1p1beta1/RecognitionConfig#:~:text=Maximum,omitted%2C%20will%20return%20a%20maximum%20of%20one.) |
| `enableWordTimeOffsets`        | `False`, `True`                   | No              | [link](https://cloud.google.com/speech-to-text/docs/reference/rest/v1p1beta1/RecognitionConfig#:~:text=If%20true,The%20default%20is%20false.) |
| `enableWordConfidence`         | `False`, `True`                   | No              | [link](https://cloud.google.com/speech-to-text/docs/reference/rest/v1p1beta1/RecognitionConfig#:~:text=If%20true%2C%20the%20top%20result%20includes%20a%20list%20of%20words%20and%20the%20confidence,is%20false.) |
| `enableAutomaticPunctuation`   | `False`, `True`                   | No              | [link](https://cloud.google.com/speech-to-text/docs/reference/rest/v1p1beta1/RecognitionConfig#:~:text=If%20%27true,to%20result%20hypotheses.) |
| `maxPhraseAlternatives`        | `1` <= Integer <= `100`           | Yes             | N/A, see [Mod9 docs](http://mod9.io:8080/docs?#:~:text=phrase-alternatives) |

## Example usage
The examples below use several command-line tools:
* Required
    * `pip3`: Python's package manager.
    * `curl`: a command-line HTTP client,
       used for downloading example files and posting API input.
* For comparison with Google
    * `gcloud`: Google Cloud's command line interface.
       To install, follow instructions at
       [cloud.google.com/sdk/install](https://cloud.google.com/sdk/install).
    * `base64`: a tool to encode byte strings to Base64,
       required for audio input via `audio.content`.
* Optional
    * `docker`: used to run a local, containerized Mod9 ASR Engine TCPServer.
       Not needed for steps below that rely on the [mod9.io](http://mod9.io) Engine
       evaluation server.
       To install, follow instructions at
       [docs.docker.com/get-docker](https://docs.docker.com/get-docker).
    * `jq`: a command-line JSON parser, useful for filtering and formatting server responses.

### Install the Mod9 ASR REST API wrapper (required)
Install the Mod9 ASR Python wrappers, including the ASR REST API wrapper from PyPI:
```bash
pip3 install mod9-asr
```

### Run a container of the Mod9 ASR Engine TCPServer (optional)
For access to the Mod9 ASR Engine TCPServer Docker image, contact sales@mod9.com.
With access, pull the image:
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
Below, we include some example calls to an Engine running locally,
but also to the [mod9.io](http://mod9.io) Engine evaluation server.

The Engine has models for audio with two audio sample rates: 8kHz and 16kHz.
Models can be loaded when the Engine starts or during run time.
The Engine is exposed on port 9900 and loads the 8kHz model on start by default:
```bash
docker run -d --name=mod9-asr -p 9900:9900 mod9/asr
```
To launch an Engine for audio at a rate of 16kHz,
use the following instead:
```bash
docker run -d --name=mod9-asr -p 9900:9900 mod9/asr ./asr-engine 16k
```
Multiple models can be loaded at start time as follows:
```bash
docker run -d --name=mod9-asr -p 9900:9900 mod9/asr ./asr-engine 8k 16k
```

The Engine may take up to 30 seconds to start up.
The REST API wrapper will wait until the Engine is ready before
accepting connections.
The Engine outputs logs that can be followed using
```bash
docker logs -f mod9-asr
```
The Engine indicates readiness with a message similar to
"Ready to serve client connections...".

### Setup to test Google Cloud STT REST API (optional, for comparison purposes)
Google Cloud credentials are required for comparisons between
Google and the Mod9 ASR REST API wrapper.
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
gcloud auth activate-service-account gstt-demo@mod9-demo.iam.gserviceaccount.com --key-file=gstt-demo-credentials.json
```

### Starting the Mod9 ASR REST API wrapper in a new terminal
The REST server is launched using an executable script
installed into your `PATH` during the `pip3` installation.
The server connects to a host and port that are controlled either
by command-line options, as demonstrated below, or by the environment
variables `MOD9_ASR_ENGINE_HOST` and `MOD9_ASR_ENGINE_PORT`, respectively (with
defaults of `localhost` and `9900`).
For example, if the Engine is running an 8kHz model locally, exposed at port
9900, the wrapper can be launched using:
```bash
mod9-rest-server
```
Or, to connect to the [mod9.io](http://mod9.io) Engine evaluation server
(which serves 8kHz and 16kHz at port 9900):
```bash
mod9-rest-server --host mod9.io
```
The ASR REST API wrapper is exposed at the Flask
default of `localhost:5000`.
Sensitive data should not be posted to the [mod9.io](http://mod9.io)
Engine evaluation server as no attempt is made to provide data
privacy or transport encryption.
Additionally, as this is a service provided for convenience of
evaluation to Mod9 customers, there is no SLA.

### Sending synchronous requests to the `/speech:recognize` endpoint
Each request to the Mod9 ASR REST API wrapper or Google Cloud STT REST API
consists of a JSON object with two top-level fields: `config` and `audio`.

| Field    | Description |
| -------- | ----------- |
| `config` | Contains metadata about the audio, such as the sample rate, as well as options for the Engine (or Google), such as whether to output word-level confidence estimates or the time interval over which a word is spoken. |
| `audio`  | Consists of either a `audio.content` field, which must be Base64-encoded bytes, or an `audio.uri` field, which indicates an audio file's location (for Google: `gs://` only; for Mod9: local `file://`, on Google Cloud Storage `gs://`, on the public internet `http://`, or on AWS `s3://`). |

The synchronous endpoint provides the simplest means of accessing the Engine
through the wrapper.
Unfortunately, Google restricts the duration of audio
accepted at this endpoint to 60 seconds or less.
The Mod9 ASR REST API wrapper does not restrict the duration of
accepted audio at the synchronous endpoint, allowing for simpler access
to ASR transcription for use cases that have audio longer than 60
seconds and do not require an asynchronous response.

The following commands will create an example JSON request
from an audio file with ground truth transcript is "hey john".
```bash
curl -sL rmtg.co/hey.wav -o /tmp/hey.wav
echo '{"audio": {"content": "'$(base64 < /tmp/hey.wav | tr -d '\n')'"}, "config": {"sampleRateHertz": 8000, "languageCode": "en-us"}}' | jq . > sync-content-request.json
```

#### Mod9 ASR REST API wrapper
Send a request to the wrapper using the following `curl` command:
```bash
curl -H 'Content-Type: application/json' localhost:5000/speech:recognize -d @sync-content-request.json
```

To send a request that makes use of a local file and the
`audio.uri` field, the following lines can be used, to get an
example audio file, create a request JSON file, and send the request.
Note that an absolute path is passed in the `audio.uri` field
(denoted by a slash following the `file://` scheme), and
that the wrapper and the client must share the same filesystem.
```bash
curl -sL rmtg.co/hey.wav -o /tmp/hey.wav
echo '{"audio": {"uri": "file:///tmp/hey.wav"}, "config": {"sampleRateHertz": 8000, "languageCode": "en-us"}}' | jq . > sync-uri-request.json
curl -H 'Content-Type: application/json' localhost:5000/speech:recognize -d @sync-uri-request.json
```

Requests longer than 60 seconds can also be processed by the
wrapper. For example, try this 70-second audio file:
```bash
curl -sL rmtg.co/switchboard-70s.wav -o /tmp/switchboard-70s.wav
echo '{"audio": {"content": "'$(base64 < /tmp/switchboard-70s.wav | tr -d '\n')'"}, "config": {"sampleRateHertz": 8000, "languageCode": "en-us"}}' | jq . > longer-request.json
curl -H 'Content-Type: application/json' localhost:5000/speech:recognize -d @longer-request.json
```

#### Google Cloud STT REST API (optional, for comparison purposes)
With Google Cloud authentication loaded, compare the response
of Google to that of the Mod9 ASR REST API above:
```bash
curl -H 'Content-Type: application/json' \
     -H 'Authorization: Bearer '$(gcloud auth print-access-token) \
     https://speech.googleapis.com/v1p1beta1/speech:recognize \
     -d @sync-content-request.json
```

At the synchronous endpoint, and using the `audio.content` field,
Google limits audio to less than 60 seconds. Attempting to send
a request with the 70-second audio file will fail:
```bash
curl -H 'Content-Type: application/json' \
     -H 'Authorization: Bearer '$(gcloud auth print-access-token) \
     https://speech.googleapis.com/v1p1beta1/speech:recognize \
     -d @longer-request.json
```

### Sending asynchronous requests to the `/speech:longrunningrecognize` endpoint
The Mod9 ASR REST API wrapper also supports an asynchronous endpoint.
Note that requests longer than 60 seconds must be made using the `audio.uri`
format to Google Cloud STT REST API (and specifically must be
stored on Google Cloud Storage);
the Mod9 ASR REST API wrapper offers the flexibility to use
`audio.content` for audio longer than 60 seconds or to use
the `audio.uri` interface with local files (with plans to support cloud
storage in the future).

The `/speech:longrunningrecognize` endpoint has a different response, as well
as a different way to retrieve the transcription results.
The response to a properly formatted request is an
[Operation JSON object](https://cloud.google.com/speech-to-text/docs/reference/rest/v1p1beta1/operations)
that contains a `name` field.
The `name`s of asynchronous requests can be viewed at the
`/operations/` endpoint, and the status and completed results can be viewed by
appending the request `name` to the end of the `/operations/` endpoint
as demonstrated below.

The following commands create a longer JSON request
that asks for word-level time offsets and confidence scores
(which are also supported by the synchronous endpoint, above),
`long-request.json`, with audio of duration 30 seconds.
```bash
curl -sL rmtg.co/switchboard-30s.wav -o /tmp/switchboard-30s.wav
echo '{"audio": {"content": "'$(base64 < /tmp/switchboard-30s.wav | tr -d '\n')'"}, "config": {"sampleRateHertz": 8000, "languageCode": "en-us", "enableWordConfidence": true, "enableWordTimeOffsets": true}}' | jq . > long-request.json
```

#### Mod9 ASR REST API wrapper
Submit a request to the wrapper and capture the `name` response:
```bash
name=$(curl -s -H 'Content-Type: application/json' localhost:5000/speech:longrunningrecognize -d @long-request.json | jq -r .name)
```

The `name` can then be used with the `/operations/` endpoint to check on the
status of the request, and, when completed, to view the transcript.
```bash
curl localhost:5000/operations/$name
```

All the `name` values of requests submitted since
the server was started can be viewed at the `/operations/` endpoint.

**Note**: asynchronous results are stored in memory and
will not persist if the Mod9 ASR REST API wrapper server is halted.
```bash
curl localhost:5000/operations/
```

#### Google Cloud STT REST API (optional, for comparison purposes)
With Google Cloud authentication properly loaded, compare the response
of Google to that of the Mod9 ASR REST API above, capturing the
`name` response:
```bash
name=$( \
    curl -s -H 'Content-Type: application/json' \
            -H 'Authorization: Bearer '$(gcloud auth print-access-token) \
            https://speech.googleapis.com/v1p1beta1/speech:longrunningrecognize \
            -d @long-request.json \
                | jq -r .name)
```

The status and results (when finished) can be checked:
```bash
curl -H 'Authorization: Bearer '$(gcloud auth print-access-token) \
     https://speech.googleapis.com/v1p1beta1/operations/$name
```

The `name` values of recently submitted requests can be viewed at the
`/operations/` endpoint:
```bash
curl -H 'Authorization: Bearer '$(gcloud auth print-access-token) \
     https://speech.googleapis.com/v1p1beta1/operations/
```
