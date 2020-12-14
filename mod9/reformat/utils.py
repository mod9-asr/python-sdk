"""
Utilities including functions to talk to the Mod9 ASR Engine TCP Server.
"""

import io
from itertools import _tee as TeeGeneratorType
import json
import os
import requests
import socket
import threading
from types import GeneratorType

import boto3
import google.auth
import google.auth.transport.requests
import google.resumable_media.requests

from mod9.reformat import config


class Mod9UnexpectedEngineResponseError(Exception):
    pass


class PropagatingThread(threading.Thread):
    """
    Thread class that propagates any exception that occurred during
    target function execution.

    See: https://stackoverflow.com/a/31614591
    """

    def run(self):
        self.exc = None
        try:
            self.ret = self._target(*self._args, **self._kwargs)
        except BaseException as e:
            self.exc = e

    def join(self):
        super().join()
        if self.exc:
            raise self.exc
        return self.ret


def get_local_path(local_path_with_prefix):
    """
    Get absolute path to file, assuming it begins with 'file://'.

    Args:
        local_path_with_prefix (str):
            Prefixed, possibly non-absolute path to file.

    Returns:
        str:
            Un-prefixed absolute path to file.
    """

    local_path = local_path_with_prefix.replace('file://', '', 1)
    return os.path.abspath(os.path.expanduser(local_path))


def parse_wav_encoding(audio_settings):
    """
    Determine if audio_settings has WAV file header.

    Args:
        audio_settings (Union[None, str, TeeGeneratorType[bytes]]):
            Audio content or location.

    Returns:
        Union[bool, str]:
            False or truthy value, which may be the encoding name.
    """

    if audio_settings is None:
        return False, 0
    elif isinstance(audio_settings, TeeGeneratorType):
        audio_settings_header = next(audio_settings)
        if audio_settings_header[:4] == b'RIFF' and audio_settings_header[8:12] == b'WAVE':
            # Get the encoding type, which is always truthy.
            encoding_bytes = audio_settings_header[20:22]
            if encoding_bytes == b'\x01\x00':
                wav_encoding = 'pcm_s16le'
            elif encoding_bytes == b'\x06\x00':
                wav_encoding = 'a-law'
            elif encoding_bytes == b'\x07\x00':
                wav_encoding = 'mu-law'
            else:
                wav_encoding = True
            # Get the sample rate.
            sample_rate = int.from_bytes(audio_settings_header[24:28], byteorder='little')
            return wav_encoding, sample_rate
        else:
            return False, 0
    elif isinstance(audio_settings, str):
        # Will fail in the pathological case of a non-WAV file stored with a ``.wav`` suffix.
        return audio_settings.endswith('.wav'), 0
    else:
        raise TypeError('Expected type None or TeeGeneratorType or str.')


def camel_case_to_snake_case(camel_case_string):
    """
    Convert a camelCase string to a snake_case string.

    Args:
        camel_case_string (str):
            A string using lowerCamelCaseConvention.

    Returns:
        str:
            A string using snake_case_convention.
    """

    # https://stackoverflow.com/a/44969381
    return ''.join(['_' + c.lower() if c.isupper() else c for c in camel_case_string]).lstrip('_')


def snake_case_to_camel_case(snake_case_string):
    """
    Convert a snake_case string to a camelCase string. Initial '_' will
    cause capitalization.

    Args:
        snake_case_string (str):
            A string using snake_case_convention.

    Returns:
        str:
            A string using lowerCamelCase or UpperCamelCase convention.
    """

    lower_case_words = snake_case_string.split(sep='_')
    camel_case_string = lower_case_words[0] \
        + ''.join(word.capitalize() for word in lower_case_words[1:])
    return camel_case_string


def recursively_convert_dict_keys_case(dict_in, convert_key):
    """
    Convert all the keys in a (potentially) recursive dict using
    function convert_key.

    Args:
        dict_in (dict[str, Union[dict, str]]):
            Dict of dicts and strs with str keys.
        convert_key (Callable[[str], str]):
            Function to convert str to str, to be applied to keys.

    Returns:
        dict[str, str]:
            Dict of dicts and strs with str keys; same structure as
            dict_in, with unchanged values, but with values transformed
            according to convert_key.
    """
    if not isinstance(dict_in, dict):
        return dict_in
    dict_out = {convert_key(key): value for key, value in dict_in.items()}
    for key, value in dict_out.items():
        if isinstance(value, dict):
            dict_out[key] = recursively_convert_dict_keys_case(dict_out[key], convert_key)
        if isinstance(value, list):
            dict_out[key] = [
                recursively_convert_dict_keys_case(item, convert_key) for item in dict_out[key]
            ]
    return dict_out


def get_bucket_key_from_path(bucketed_path_with_prefix, prefix):
    """
    Get bucket and key from path, assuming it begins with given prefix.

    Args:
        bucketed_path_with_prefix (str):
            Prefixed path including bucket and key.
        prefix (str):
            Prefix to look for in bucketed_path_with_prefix.

    Returns:
        tuple:
            bucket_name (str):
                Parsed name of bucket.
            key_name (str):
                Parsed name of key.
    """

    bucket_key = bucketed_path_with_prefix.replace(prefix, '', 1)
    bucket_name, key_name = bucket_key.split(sep='/', maxsplit=1)
    return bucket_name, key_name


def convert_gs_uri_to_http_url(uri):
    """
    Convert URI, assumed to begin with 'gs://', to URL for use with
    Google Resumable Media.

    Args:
        uri (str):
            URI to Google Cloud Storage beginning with ``gs://``.

    Returns:
        str:
            URL to Google Cloud Storage usable with Google Resumable
            Media.
    """

    bucket, key = get_bucket_key_from_path(uri, 'gs://')
    url = f"https://storage.googleapis.com/download/storage/v1/b/{bucket}" \
          f"/o/{key}?alt=media"
    return url


def generator_producer(generator, sock):
    """
    Send contents of generator to given socket.

    Args:
        generator (Iterable[bytes]):
            Data to send to socket.
        sock (socket.socket):
            Socket to send to.

    Returns:
        None
    """

    for item in generator:
        # Chunk-ify items that are larger than specified size.
        for i in range(0, len(item), config.CHUNK_SIZE):
            sock.sendall(item[i:i+config.CHUNK_SIZE])


def file_producer(uri, sock):
    """
    Send contents of file in chunks to given socket.

    Args:
        uri (str):
            Prefixed path to local file to be sent to socket.
        sock (socket.socket):
            Socket to send to.

    Returns:
        None
    """

    with open(get_local_path(uri), 'rb') as fin:
        for chunk in iter(lambda: fin.read(config.CHUNK_SIZE), b''):
            sock.sendall(chunk)


def http_producer(uri, sock):
    """
    Send contents of file hosted at URL in chunks to given socket.

    Args:
        uri (str):
            Prefixed public URL file to be sent to socket.
        sock (socket.socket):
            Socket to send to.

    Returns:
        None
    """

    with requests.get(uri, stream=True) as r:
        r.raise_for_status()
        for chunk in r.iter_content(chunk_size=config.CHUNK_SIZE):
            sock.sendall(chunk)


def google_cloud_producer(uri, sock):
    """
    Send contents of file hosted on GCS in chunks to given socket.

    Args:
        uri (str):
            Prefixed Google Cloud Storage file to to be sent to socket.
            Note you must have access to the file with currently loaded
            Google credentials.
        sock (socket.socket):
            Socket to send to.

    Returns:
        None
    """

    url = convert_gs_uri_to_http_url(uri)

    # https://googleapis.dev/python/google-resumable-media/latest/resumable_media/requests.html#google.resumable_media.requests.ChunkedDownload
    ro_scope = 'https://www.googleapis.com/auth/devstorage.read_only'
    credentials, _ = google.auth.default(scopes=(ro_scope,))
    transport = google.auth.transport.requests.AuthorizedSession(credentials)

    chunk_start = 0
    total_bytes = float('inf')
    while chunk_start < total_bytes:
        # ChunkedDownload appends bytes to stream.
        #  Use new stream each chunk to avoid holding entire file in memory.
        with io.BytesIO() as f:
            download = google.resumable_media.requests.ChunkedDownload(
                url,
                config.GS_CHUNK_SIZE,
                f,
                start=chunk_start,
            )
            download.consume_next_chunk(transport)
            chunk = f.getvalue()
            sock.sendall(chunk)

            chunk_start += config.GS_CHUNK_SIZE
            total_bytes = download.total_bytes


def aws_s3_producer(uri, sock):
    """
    Send contents of file hosted on AWS S3 in chunks to given socket.

    Args:
        uri (str):
            Prefixed AWS S3 file to to be sent to socket. Note you must
            have access to the file with currently loaded AWS
            credentials.
        sock (socket.socket):
            Socket to send to.

    Returns:
        None
    """

    bucket, key = get_bucket_key_from_path(uri, 's3://')
    # https://stackoverflow.com/a/40854612
    # https://botocore.amazonaws.com/v1/documentation/api/latest/reference/response.html#botocore.response.StreamingBody.iter_chunks
    s3c = boto3.client('s3')
    for chunk in s3c.get_object(Bucket=bucket, Key=key)['Body'].iter_chunks(
        chunk_size=config.CHUNK_SIZE
    ):
        sock.sendall(chunk)


def _make_eof_producer(producer):
    """
    Send a special EOF byte sequence to terminate the request.

    Args:
        producer (Callable[[str, socket.socket], None]):
            Request producer.

    Returns:
        Callable[[str, socket.socket], None]:
            Request producer that sends 'END-OF-FILE' at end of request.
    """

    def new_producer(audio_input, sock):
        producer(audio_input, sock)
        sock.sendall(b'END-OF-FILE')
    return new_producer


prefix_producer_map = {
    'file':  file_producer,
    'gs':    google_cloud_producer,
    'http':  http_producer,
    'https': http_producer,
    's3':    aws_s3_producer,
}


def get_transcripts_mod9(options, audio_input):
    """
    Open TCP connection to Mod9 server, send input, and yield output
    generator.

    Args:
        options (dict[str, Union[dict, float, int, str]]):
            Transcription options for Engine.
        audio_input (Union[GeneratorType, TeeGeneratorType, str]):
            Audio content to be transcribed.

    Yields:
        dict[str, Union[dict, float, int, str]]:
            Result from Mod9 ASR Engine TCP Server.
    """

    with socket.create_connection(
        (config.MOD9_ASR_ENGINE_HOST, config.MOD9_ASR_ENGINE_PORT),
        timeout=config.SOCKET_CONNECTION_TIMEOUT_SECONDS,
    ) as sock:
        sock.settimeout(config.SOCKET_INACTIVITY_TIMEOUT_SECONDS)

        # Start by sending the options as JSON on the first line (terminated w/ newline character).
        first_request_line = json.dumps(options, separators=(',', ':')) + '\n'
        sock.sendall(first_request_line.encode())

        # The Engine should respond with an initial 'processing' status message.
        sockfile = sock.makefile(mode='r')
        first_response_line = json.loads(sockfile.readline())
        if first_response_line.get('status') != 'processing':
            raise KeyError(
                f"Did not receive 'processing' from Mod9 ASR Engine. Got '{first_response_line}'."
            )

        # Select proper producer given audio input type.
        if isinstance(audio_input, GeneratorType) or isinstance(audio_input, TeeGeneratorType):
            producer = generator_producer
        elif isinstance(audio_input, str):
            producer = prefix_producer_map.get(audio_input.split(sep='://')[0])
            if producer is None:
                allowed_prefixes = '://, '.join(prefix_producer_map) + '://'
                raise NotImplementedError(
                    f"URI '{audio_input}' has unrecognized prefix."
                    f" Allowed prefixes: {allowed_prefixes}."
                )
        else:
            raise TypeError(f"Audio input should be generator or str; got '{type(audio_input)}'.")

        if options.get('format') == 'raw':
            producer = _make_eof_producer(producer)

        # Launch producer thread to stream from audio input source to Engine.
        producer_thread = PropagatingThread(target=producer, args=(audio_input, sock))
        producer_thread.start()

        for line in sockfile:
            yield json.loads(line)

        producer_thread.join()


def get_loaded_models_mod9():
    """
    Query Engine for a list of models and return loaded models.

    Args:
        None

    Returns:
        dict[str, dict[str, Union[bool, dict, int, str]]]:
            Metadata about models currently loaded in Engine.
    """

    with socket.create_connection(
        (config.MOD9_ASR_ENGINE_HOST, config.MOD9_ASR_ENGINE_PORT),
        timeout=config.SOCKET_CONNECTION_TIMEOUT_SECONDS,
    ) as sock:
        sock.settimeout(config.SOCKET_INACTIVITY_TIMEOUT_SECONDS)

        # Start by sending request to list models (terminated w/ newline character).
        get_model_request = '{"command": "get-models-info"}\n'
        sock.sendall(get_model_request.encode())

        sockfile = sock.makefile(mode='r')

        get_models_response = json.loads(sockfile.readline())
        if get_models_response.get('status') != 'completed':
            raise KeyError(
                f"Got response '{get_models_response}'; must have `.status` field `completed`."
            )
        if 'models' not in get_models_response:
            raise Mod9UnexpectedEngineResponseError(
                f"Got response '{get_models_response}'; must have `.models` field."
            )

        sockfile.close()

        return get_models_response['models']


def find_loaded_models_with_rate(rate):
    """
    Get all models loaded in Engine that have the specified rate.

    Args:
        rate (int):
            Check for loaded Engine models with this rate.

    Returns:
        list[dict[str, Union[bool, dict, int, str]]]:
            Metadata about models currently loaded in Engine with specified rate (or empty list).
    """
    try:
        models = get_loaded_models_mod9()
    except Mod9UnexpectedEngineResponseError:
        return []
    return [model for model in models if model['rate'] == rate]
