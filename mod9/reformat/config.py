"""
Provides defaults used throughout mod9-asr.
"""

import os

MOD9_ASR_ENGINE_HOST = os.getenv('MOD9_ASR_ENGINE_HOST', 'localhost')
MOD9_ASR_ENGINE_PORT = int(os.getenv('MOD9_ASR_ENGINE_PORT', 9900))

SOCKET_CONNECTION_TIMEOUT_SECONDS = 10.0
SOCKET_INACTIVITY_TIMEOUT_SECONDS = 60.0
ENGINE_CONNECTION_RETRY_SECONDS = 10.0

CHUNK_SIZE = 8 * 1024 * 1024  # 8 MiB
GS_CHUNK_SIZE = 262144  # Google requires chunks be multiples of 262144

FLASK_ENV = os.getenv('FLASK_ENV', None)
