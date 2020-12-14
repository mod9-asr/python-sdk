#!/usr/bin/env python3

"""
REST API wrapper over the Mod9 ASR Engine TCP Server.
"""

import argparse
from collections import OrderedDict
from datetime import datetime
import json
import logging
import socket
import threading
import time
import uuid

from flask import Flask
from flask_restful import reqparse, abort, Api, Resource

from mod9.asr import speech_mod9
import mod9.reformat.config as config
from mod9.reformat.utils import get_transcripts_mod9
from mod9.reformat import google as reformat

app = Flask(__name__)
# Make JSON output readable.
#  ``RESTFUL_JSON`` is a config var from ``flask_restful`` that
#  allows JSON formatting similar to ``json.dumps()``, see docs:
#  https://flask-restful.readthedocs.io/en/latest/extending.html#:~:text=RESTFUL_JSON
app.config['RESTFUL_JSON'] = {'indent': 2, 'sort_keys': False}
if config.FLASK_ENV is not None:
    app.config['ENV'] = config.FLASK_ENV
else:
    # Stop output of warning message on server start.
    #  Note this is not recommended by Flask devs, but should be fine for our purposes:
    #  https://flask.palletsprojects.com/en/1.1.x/config/#environment-and-debug-features
    app.config['ENV'] = 'development'
api = Api(app)

# Input parser for Recognize and LongRunningRecognize resources.
parser = reqparse.RequestParser()
parser.add_argument(
    'config',
    required=True,
    help="Required 'config' contains ASR settings in JSON format.",
    location='json',
    type=dict,
)
parser.add_argument(
    'audio',
    required=True,
    help="Required 'audio' contains audio file path or encoded bytes.",
    location='json',
    type=dict,
)

# Storage for operation names and results used by LongRunningRecognize.
operation_names = []
operation_results = {}


def test_host_port():
    """
    Check if Mod9 ASR Engine is online. Loop until get ``server_ready``
    response. Log stats.

    Args:
        None

    Returns:
        None
    """

    logging.info(
        "Checking for Mod9 ASR Engine running at %s:%s...",
        config.MOD9_ASR_ENGINE_HOST, config.MOD9_ASR_ENGINE_PORT
    )

    # Loop sending get-stats until receive ``server_ready is True`` response.
    response = dict()
    while response.get('server_ready') is not True:
        with socket.create_connection(
            (config.MOD9_ASR_ENGINE_HOST, config.MOD9_ASR_ENGINE_PORT),
            timeout=config.SOCKET_CONNECTION_TIMEOUT_SECONDS,
        ) as sock:
            sock.settimeout(config.SOCKET_INACTIVITY_TIMEOUT_SECONDS)

            sock.sendall('{"command": "get-stats"}\n'.encode())
            with sock.makefile(mode='r') as sockfile:
                response = json.loads(sockfile.readline())

        # Output and sleep except when receive ``server_ready is True`` response.
        if response['server_ready'] is not True:
            logging.error(
                "The Engine is not ready yet. Will attempt to connect again in %s seconds...",
                config.ENGINE_CONNECTION_RETRY_SECONDS,
            )
            time.sleep(config.ENGINE_CONNECTION_RETRY_SECONDS)

    logging.info(
        "The Engine is ready and responded:\n%s",
        json.dumps(response, indent=2, sort_keys=True),
    )


def place_reformatted_mod9_response_in_operation_results(
    mod9_config_settings,
    mod9_audio_settings,
    operation_name,
):
    """
    Get and format response from Mod9 ASR Engine. Place response in
    proper ``operation_result``.

    Args:
        mod9_config_settings (dict[str, Union[dict, float, int, str]]):
            Mod9-style transcription options.
        mod9_audio_settings (Union[
                GeneratorType,
                TeeGeneratorType,
                str,
        ]):
            Audio content to be transcribed.
        operation_name (str):
            Transcription operation UUID.

    Returns:
        None
    """

    # Response type metadata constant string.
    response_type = 'type.googleapis.com/google.cloud.speech.v1p1beta1.LongRunningRecognizeResponse'

    # Talk to Mod9 ASR Engine.
    try:
        engine_response = get_transcripts_mod9(mod9_config_settings, mod9_audio_settings)
    except (KeyError, ConnectionError):
        logging.exception('Error communicating with Mod9 ASR Engine.')
        abort(500)

    # Place response in operation_results.
    operation_results[operation_name]['response'] = OrderedDict(
        [
            ('@type', response_type),
            ('results', list(reformat.result_from_mod9(engine_response))),
        ]
    )
    operation_results[operation_name]['done'] = True
    operation_results[operation_name].move_to_end('response')

    # Hack to remove .isFinal field from response.
    [result.pop('isFinal') for result in operation_results[operation_name]['response']['results']]

    # Update metadata.
    current_time = datetime.utcnow().isoformat() + 'Z'
    operation_results[operation_name]['metadata']['lastUpdateTime'] = current_time
    operation_results[operation_name]['metadata']['progressPercent'] = 100
    operation_results[operation_name]['metadata'].move_to_end('startTime')
    operation_results[operation_name]['metadata'].move_to_end('lastUpdateTime')


class Recognize(Resource):
    """Implement synchronous ASR for ``/recognize`` endpoint."""

    def post(self):
        """Perform synchronous ASR on POSTed config and audio."""
        # Translate request -> Mod9 format.
        args = parser.parse_args()
        try:
            mod9_config_settings, mod9_audio_settings = reformat.input_to_mod9(
                args,
                module=speech_mod9,
            )
        except Exception:
            logging.exception('Invalid arguments.')
            abort(400)

        # Talk to Mod9 ASR Engine.
        try:
            engine_response = get_transcripts_mod9(mod9_config_settings, mod9_audio_settings)
        except (KeyError, ConnectionError):
            logging.exception('Error communicating with Mod9 ASR Engine.')
            abort(500)

        # Translate response -> external API format.
        response = {'results': list(reformat.result_from_mod9(engine_response))}

        # Hack to remove .isFinal field from response.
        [result.pop('isFinal') for result in response['results']]

        return response


class Operations(Resource):
    """
    Implement operations name fetching for ``/operations`` endpoint.
    """

    def get(self):
        """Output finished and presently running operation names."""
        return {'operations': list(reversed(operation_names))}


class GetOperationByName(Resource):
    """
    Implement operation result fetching for
    ``/operations/<operation_name>`` endpoint.
    """

    def get(self, operation_name):
        """Output operation with given operation name."""
        return operation_results[str(operation_name)]


class LongRunningRecognize(Resource):
    """
    Implement asynchronous ASR for ``/longrunningrecognize`` endpoint.
    """

    def post(self):
        """Perform asynchronous ASR on POSTed config and audio."""
        # Translate request -> Mod9 format.
        args = parser.parse_args()
        try:
            mod9_config_settings, mod9_audio_settings = reformat.input_to_mod9(
                args,
                module=speech_mod9,
            )
        except Exception:
            logging.exception('Invalid arguments.')
            abort(400)

        # Generate a name for operation and append to list of operations.
        operation_name = str(uuid.uuid4().int)
        operation_names.append({'name': operation_name})

        # Set up initial operation_result.
        # Reponse type metadata constant string.
        meta_type = 'type.googleapis.com/google.cloud.speech.v1p1beta1.LongRunningRecognizeMetadata'
        start_time = datetime.utcnow().isoformat() + 'Z'
        operation_metadata = OrderedDict(
            [
                ('@type', meta_type),
                ('startTime', start_time),
                ('lastUpdateTime', start_time),
            ]
        )

        operation_results[operation_name] = OrderedDict([('name', operation_name)])
        operation_results[operation_name]['metadata'] = operation_metadata

        # Send request to Mod9 ASR Engine. Result will appear in operation_results when done.
        request_thread = threading.Thread(
            target=place_reformatted_mod9_response_in_operation_results,
            args=(
                mod9_config_settings,
                mod9_audio_settings,
                operation_name,
            ),
        )
        request_thread.start()

        return {'name': operation_name}


api.add_resource(
    Recognize,
    '/speech:recognize',
    '/speech:recognize/',
)
api.add_resource(
    LongRunningRecognize,
    '/speech:longrunningrecognize',
    '/speech:longrunningrecognize/',
)
api.add_resource(
    Operations,
    '/operations',
    '/operations/',
)
api.add_resource(
    GetOperationByName,
    '/operations/<int:operation_name>',
    '/operations/<int:operation_name>/',
)


def main():
    parser = argparse.ArgumentParser()
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

    logging.basicConfig(format="%(levelname)s: %(message)s", level=logging.INFO)

    if args.host is not None:
        logging.info("Setting host to '%s' from command line argument.", args.host)
        config.MOD9_ASR_ENGINE_HOST = args.host
    if args.port is not None:
        logging.info("Setting port to '%s' from command line argument.", args.port)
        config.MOD9_ASR_ENGINE_PORT = args.port

    test_host_port()
    app.run(debug=False)


if __name__ == '__main__':
    main()
