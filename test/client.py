#!/usr/bin/env python3

import argparse
import json
import sys

from mod9.asr import speech_mod9 as speech

READ_IN_CHUNK_SIZE = 1024


class Mod9StreamingRequest(object):
    def __init__(self, audio_content):
        # Streaming audio bytes expected at `.audio_content` attribute.
        self.audio_content = audio_content


def prepare_dict_inputs(options=dict()):
    encoding = 'LINEAR16'
    language_code = 'en-US'
    if options.get('sample_rate_hertz'):
        sample_rate_hertz = options['sample_rate_hertz']
    else:
        sample_rate_hertz = 16000  # Wrappers default.
    config = {
        'encoding': encoding,
        'sample_rate_hertz': sample_rate_hertz,
        'language_code': language_code,
    }
    config.update(options)
    # Comment following line to stop partial (non-final) result output.
    config = {'config': config, 'interim_results': True}
    return config


def read_bytes_from_stdin(read_in_chunk_size=READ_IN_CHUNK_SIZE):
    while True:
        bytes_in = sys.stdin.buffer.read(read_in_chunk_size)
        if not bytes_in:
            break
        yield bytes_in


def get_responses_from_mod9(options=dict(), host=None, port=None):
    client = speech.SpeechClient(host=host, port=port)
    config_dict = prepare_dict_inputs(options=options)
    requests = (
        Mod9StreamingRequest(chunk) for chunk in read_bytes_from_stdin()
    )
    return client.streaming_recognize(config_dict, requests)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument(
        '-o',
        '--options',
        help='Additional options to pass to Mod9 ASR Python SDK.',
        type=json.loads,
        default=dict(),
    )
    parser.add_argument(
        '--host',
        help='Mod9 ASR Engine TCP Server host name.'
             ' Overrides environmental variable `MOD9_ASR_ENGINE_HOST`.',
    )
    parser.add_argument(
        '--port',
        help='Mod9 ASR Engine TCP Server port.'
             ' Overrides environmental variable `MOD9_ASR_ENGINE_PORT`.',
        type=int,
    )
    args = parser.parse_args()

    for response in get_responses_from_mod9(
        options=args.options,
        host=args.host,
        port=args.port,
    ):
        print(response.results[0])
