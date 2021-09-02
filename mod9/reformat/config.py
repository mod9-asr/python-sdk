"""
Provides defaults used throughout mod9-asr.
"""

import logging
import os

# Current wrappers version.  Note that this is not the same as the Engine version.
WRAPPER_VERSION = '1.2.0'

# CHANGELOG:
#   1.2.0 (30 Aug 2021):
#   - Improved logging.
#   - Allow "rate" option to be in the range [8000,48000], as with Google STT.
#   - Added "speed" option to speech_mod9.
#   - Added "options_json" to speech_mod9.
#   1.1.1 (11 Aug 2021):
#   - Rebuild correctly (after `rm -rf build/ dist/ *.egg-info`)
#   1.1.0 (11 Aug 2021):
#   - Released in coordination with Engine version 1.1.0 (coincidental version match, not causal).
#   - Added "latency" request option to speech_mod9.
#   - REST API now logs to a file, with UUIDs both for itself and the proxied Engine.
#   1.0.0 (31 Jul 2021):
#   - This version is not compatible with Engine version < 1.0.0 (due to "asr-model" option).
#   - Bugfixes to WebSocket interface; also add --skip-engine-check and --allow-*-uri (for REST).
#   0.5.0 (28 May 2021): Add Websocket Interface.
#   0.4.1 (20 May 2021): Additional minor documentation fixes; Flask-RESTful version pinning.
#   0.4.0 (30 Apr 2021): Rename mod9-rest-server to mod9-asr-rest-api; minor documentation fixes.

# Range of compatible Engine versions for current wrappers.
#  Lower bound is inclusive, upper bound is exclusive.
#  ``None`` indicates no bound.
WRAPPER_ENGINE_COMPATIBILITY_RANGE = ('1.0.0', None)  # tested at 1.2.0 as of 2021 Aug 29.

ASR_ENGINE_HOST = os.getenv('ASR_ENGINE_HOST', 'localhost')
ASR_ENGINE_PORT = int(os.getenv('ASR_ENGINE_PORT', 9900))

SOCKET_CONNECTION_TIMEOUT_SECONDS = 10.0
SOCKET_INACTIVITY_TIMEOUT_SECONDS = 60.0
ENGINE_CONNECTION_RETRY_SECONDS = 1.0

MAX_CHUNK_SIZE = 8 * 1024 * 1024  # Used as chunk size for URI producers; limits generators.
GS_CHUNK_SIZE = 262144  # Google requires chunks be multiples of 262144

FLASK_ENV = os.getenv('FLASK_ENV', None)

# Audio URI prefixes to accept, used by REST only (PySDK allows all).
#  Operator can set at server launch; default is allow none.
ASR_REST_API_ALLOWED_URI_SCHEMES = os.getenv('ASR_REST_API_ALLOWED_URI_SCHEMES', set())
if ASR_REST_API_ALLOWED_URI_SCHEMES:
    ASR_REST_API_ALLOWED_URI_SCHEMES = ASR_REST_API_ALLOWED_URI_SCHEMES.lower().split(sep=',')
    ASR_REST_API_ALLOWED_URI_SCHEMES = set(
        scheme.replace('://', '') for scheme in ASR_REST_API_ALLOWED_URI_SCHEMES
    )

if 'http' in ASR_REST_API_ALLOWED_URI_SCHEMES and 'https' not in ASR_REST_API_ALLOWED_URI_SCHEMES:
    logging.warning('REST API set to allow http:// but NOT https:// audio URIs.')
