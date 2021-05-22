"""
Provides defaults used throughout mod9-asr.
"""

import os

# Current wrappers version.
# CHANGELOG:
#   0.4.0 (30 Apr 2021): Rename mod9-rest-server to mod9-asr-rest-api; minor documentation fixes.
#   0.4.1 (20 May 2021): Additional minor documentation fixes; Flask-RESTful version pinning.
WRAPPER_VERSION = '0.4.1'

# Range of compatible Engine versions for current wrappers.
#  Lower bound is inclusive, upper bound is exclusive.
#  ``None`` indicates no bound.
WRAPPER_ENGINE_COMPATIBILITY_RANGE = ('0.8.0', None)  # tested at 0.8.1 as of 30 Apr 2021

MOD9_ASR_ENGINE_HOST = os.getenv('MOD9_ASR_ENGINE_HOST', 'localhost')
MOD9_ASR_ENGINE_PORT = int(os.getenv('MOD9_ASR_ENGINE_PORT', 9900))

SOCKET_CONNECTION_TIMEOUT_SECONDS = 10.0
SOCKET_INACTIVITY_TIMEOUT_SECONDS = 60.0
ENGINE_CONNECTION_RETRY_SECONDS = 10.0

CHUNK_SIZE = 8 * 1024 * 1024  # 8 MiB
GS_CHUNK_SIZE = 262144  # Google requires chunks be multiples of 262144

FLASK_ENV = os.getenv('FLASK_ENV', None)
