"""
Functions for converting Google-style and -type input and output to/from
Mod9-style and -type.
"""

import base64
from binascii import Error as BinasciiError
from collections import OrderedDict
import itertools
import json
import logging
from types import GeneratorType

from mod9.reformat import utils
from mod9.reformat.config import (
    WRAPPER_ENGINE_COMPATIBILITY_RANGE,
    WRAPPER_VERSION,
)

CHUNKSIZE = 8 * 1024


class ConflictingGoogleAudioSettingsError(Exception):
    pass


class Mod9EngineFailedStatusError(Exception):
    pass


# Used to allow arbitrary `model`s to be loaded into Engine and requested by user.
class ObjectContainingEverything:
    """Object that always returns True to `if x in ObjectContainingEverything()` queries."""
    def __contains__(self, x):
        return True


# Used to allow number ranges to be requested by user.
class RealNumericalRangeObject:
    """Object that returns True if ``x`` is in given numerical range."""
    def __init__(self, low, high):
        self.low = low
        self.high = high

    def __contains__(self, x):
        return x >= self.low and x <= self.high


class GoogleConfigurationSettingsAndMappings:
    """
    Hold dicts used to translate keys and values from Google to Mod9
    forms.

    Internally use camelCase for google_allowed_keys. We chose to use
    camelCase internally for compatibility with Google's
    ``protobuf.json_format`` funtions (which are called by ``to_json()``
    and ``from_json()``). We need to make sure we use the proper casing,
    both internally and for output, or can run into non-obvious bugs.
    These bugs can be non-obvious because many of the primary attributes
    are one-word attributes (like ``.transcript``) and so functionality
    will only break if it is dependent on multi-word attributes.

    Input from REST API come in camelCase. Input from Python SDK come in
    snake_case, are converted to camelCase using either ``from_json()``
    (in the case of Google protobuf object input), or
    ``mod9.reformat.utils.recursively_convert_dict_keys_case()`` and
    ``reformat.utils.snake_case_to_camel_case()`` (in the case of dict
    input). Output from REST API use camelCase. Output from Python SDK
    converted to snake_case in ``to_json()``.
    """
    def __init__(self):
        """
        Define dicts used to translate keys and values from Google to
        Mod9 forms.
        """

        # Mod9 and Google input key names for use in following dict's.
        self.mod9_allowed_keys = (
            'encoding',
            'rate',
            'word-confidence',
            'word-intervals',
            'transcript-formatted',
            'transcript-alternatives',
            'phrase-alternatives',       # only works in speech_mod9 or REST
            'phrase-alternatives-bias',  # only works in speech_mod9 or REST
            'latency',                   # only works in speech_mod9
            'speed',                     # only works in speech_mod9 or REST
            'options_json',              # only works in speech_mod9 or REST
            'asr-model',                 # Mod9 internal (always happens under the hood)
            'nlp-model',                 # Mod9 internal (always happens under the hood)
        )
        self.google_allowed_keys = (
            'encoding',
            'sampleRateHertz',
            'enableWordConfidence',
            'enableWordTimeOffsets',
            'enableAutomaticPunctuation',
            'maxAlternatives',
            'maxPhraseAlternatives',     # only works in speech_mod9 or REST
            'enablePhraseConfidence',    # only works in speech_mod9 or REST
            'latency',                   # only works in speech_mod9
            'speed',                     # only works in speech_mod9 or REST
            'optionsJson',               # only works in speech_mod9 or REST
            'asrModel',                  # Mod9 internal (always happens under the hood)
            'nlpModel',                  # Mod9 internal (always happens under the hood)
        )

        # Map from (Google key) to (Mod9 key).
        self.google_to_mod9_key_translations = dict(
            zip(
                self.google_allowed_keys,
                self.mod9_allowed_keys,
            )
        )

        # Allowed Google values.
        self.google_encoding_allowed_values = {
            'ENCODING_UNSPECIFIED',
            'LINEAR16',
            'MULAW',
            'ALAW',  # only in Mod9
        }
        self.google_rate_allowed_values = range(8000, 48001)
        self.google_confidence_allowed_values = {True, False}
        self.google_timestamp_allowed_values = {True, False}
        self.google_punctuation_allowed_values = {True, False}
        self.google_max_alternatives_allowed_values = range(10001)
        self.google_max_phrase_alternatives_allowed_values = range(10001)
        self.google_phrase_confidence_allowed_values = {True, False}
        self.latency_allowed_values = RealNumericalRangeObject(0.01, 3.0)
        self.speed_allowed_values = range(1, 10)
        self.options_json_allowed_values = ObjectContainingEverything()
        self.asr_model_allowed_values = ObjectContainingEverything()
        self.nlp_model_allowed_values = ObjectContainingEverything()

        # Group allowed Google values. To be used in following dict.
        self.google_allowed_values = (
            self.google_encoding_allowed_values,
            self.google_rate_allowed_values,
            self.google_confidence_allowed_values,
            self.google_timestamp_allowed_values,
            self.google_punctuation_allowed_values,
            self.google_max_alternatives_allowed_values,
            self.google_max_phrase_alternatives_allowed_values,
            self.google_phrase_confidence_allowed_values,
            self.latency_allowed_values,
            self.speed_allowed_values,
            self.options_json_allowed_values,
            self.asr_model_allowed_values,
            self.nlp_model_allowed_values,
        )

        # Map from (Mod9 key) to (allowed Google values) for given key.
        self.mod9_keys_to_allowed_values = dict(
            zip(
                self.mod9_allowed_keys,
                self.google_allowed_values,
            )
        )

        # Map from (allowed Google encodings) to (Mod9 encodings)
        self.google_encoding_to_mod9_encoding = {
            'LINEAR16': 'pcm_s16le',
            'MULAW': 'mu-law',
            'ALAW': 'a-law',
        }


def input_to_mod9(google_input_settings, module):
    """
    Wrapper method to take Google inputs of various types and return
    Mod9-compatible inputs.

    Args:
        google_input_settings (dict):
            Contains dicts or Google-like-types ``.config`` and
            ``.audio``: options for transcription and audio to be
            transcribed, respectively.
        module (module):
            Module to read Google-like-types from, in case of
            subclassing.

    Returns:
        tuple:
            mod9_config_settings (dict):
                Mod9-style options to pass to Mod9 ASR Engine TCP Server.
            mod9_audio_settings (dict):
                Mod9-style audio to pass to Mod9 ASR Engine TCP Server.
    """

    engine_version = utils.get_version_mod9()
    if not utils.is_compatible_mod9(engine_version):
        raise utils.Mod9IncompatibleEngineVersionError(
            f"Python SDK version {WRAPPER_VERSION} compatible range"
            f" {WRAPPER_ENGINE_COMPATIBILITY_RANGE}"
            f" does not include given Engine of version {engine_version}."
            ' Please use a compatible SDK-Engine pairing. Exiting.'
        )

    # Convert keys from snake_case to camelCase (if necessary), which we use internally.
    #  See docstring for GoogleConfigurationSettingsAndMappings for more info.
    google_input_settings = utils.recursively_convert_dict_keys_case(
        google_input_settings,
        utils.snake_case_to_camel_case,
    )

    # Convert Google-type inputs to dict-type inputs, if necessary.
    if isinstance(google_input_settings['config'], dict):
        google_config_settings_dict = google_input_settings['config']
    elif isinstance(google_input_settings['config'], module.RecognitionConfig):
        google_config_settings_dict = json.loads(
            module.RecognitionConfig.to_json(
                google_input_settings['config'],
                use_integers_for_enums=False,
            )
        )
    elif isinstance(google_input_settings['config'], module.StreamingRecognitionConfig):
        google_config_settings_dict = json.loads(
            module.StreamingRecognitionConfig.to_json(
                google_input_settings['config'],
                use_integers_for_enums=False,
            )
        )

    if 'audio' not in google_input_settings or google_input_settings['audio'] is None:
        # Empty dict will lead to mod9_audio_settings returning None.
        google_audio_settings_dict = dict()
    elif isinstance(google_input_settings['audio'], dict):
        google_audio_settings_dict = google_input_settings['audio']
    elif isinstance(google_input_settings['audio'], module.RecognitionAudio):
        google_audio_settings_dict = json.loads(
            module.RecognitionAudio.to_json(google_input_settings['audio'])
        )

    # Convert Google-style inputs to Mod9-style inputs.
    mod9_config_settings = google_config_settings_to_mod9(google_config_settings_dict)
    mod9_audio_settings = google_audio_settings_to_mod9(google_audio_settings_dict)

    # None is a placeholder since we need to inspect the audio_settings to determine file format.
    if 'format' in mod9_config_settings and mod9_config_settings['format'] is None:
        # Set file type based on file header.
        if isinstance(mod9_audio_settings, GeneratorType):
            # Split generator so utils.parse_wav_encoding() can look at content header.
            mod9_audio_settings, mod9_audio_settings_clone = itertools.tee(mod9_audio_settings)
        wav_encoding, wav_sample_rate = utils.parse_wav_encoding(mod9_audio_settings)
        if wav_encoding:
            mod9_config_settings['format'] = 'wav'
            if 'encoding' in mod9_config_settings:
                if wav_encoding != mod9_config_settings['encoding']:
                    # The Google Cloud STT API complains if WAV and encoding are mismatched.
                    raise ConflictingGoogleAudioSettingsError(
                        "WAV file format encoded as %s should match config specified as %s."
                        % (wav_encoding, mod9_config_settings['encoding'])
                    )
                # The Mod9 ASR Engine complains if both WAV format and audio encoding are specified.
                del mod9_config_settings['encoding']
            if wav_sample_rate:
                if 'rate' in mod9_config_settings:
                    if mod9_config_settings['rate'] != wav_sample_rate:
                        raise ValueError(f"Specified rate, {mod9_config_settings['rate']},"
                                         f" differs from WAV header rate, {wav_sample_rate}.")
                else:
                    mod9_config_settings['rate'] = wav_sample_rate
        else:
            mod9_config_settings['format'] = 'raw'
            if 'encoding' not in mod9_config_settings:
                raise KeyError('Must specify an audio encoding for non-WAV file formats')
        # Reset audio using tee'd clone if it exists.
        try:
            mod9_audio_settings = mod9_audio_settings_clone
        except UnboundLocalError:
            pass

    # TODO: enable more languages, rather than only supporting English.
    # TODO: enable the model parameter, rather than auto-detecting it based on sample rate.
    if 'rate' in mod9_config_settings and 'asr-model' not in mod9_config_settings:
        # Set model associated with user-passed rate, but don't overwrite a user-passed model.
        models = utils.find_loaded_models_with_rate(mod9_config_settings['rate'])
        # Use first English model in list -> first loaded model.
        for model in models:
            if model['language'].lower() == 'en-us':
                mod9_config_settings['asr-model'] = model['name']
                break

    # Mod9 TCP does not accept 'rate' argument for 'wav' format.
    if 'format' not in mod9_config_settings or mod9_config_settings['format'] == 'wav':
        if 'rate' in mod9_config_settings:
            del mod9_config_settings['rate']

    # Need transcript intervals to mirror Google response format.
    mod9_config_settings['transcript-intervals'] = True

    return mod9_config_settings, mod9_audio_settings


def google_config_settings_to_mod9(google_config_settings):
    """
    Map from Google-style key:value inputs to Mod9 ASR TCP server-style
    key:value inputs.

    Args:
        google_config_settings (dict):
            Google-style options.

    Returns:
        dict:
            Mod9-style options to pass to Mod9 ASR Engine TCP Server.
    """

    settings = GoogleConfigurationSettingsAndMappings()
    mod9_config_settings = dict()

    # StreamingRecognitionConfig has config attribute of type RecognitionConfig.
    if 'config' in google_config_settings:
        # Grab streaming options and assign google_config_settings to RecognitionConfig attribute.
        if google_config_settings.get('singleUtterance') is True:
            raise NotImplementedError(
                'Streaming recognize not yet implemented for Google option single_utterance: True.'
            )
        mod9_config_settings['partial'] = google_config_settings.get('interimResults', False)
        google_config_settings = google_config_settings['config']

        # Turn off batch mode for streaming, otherwise partial will not work.
        mod9_config_settings['batch-threads'] = 0
    else:
        # Use max number of threads available for best speed.
        mod9_config_settings['batch-threads'] = -1

        # This option only applies with speech_mod9.
        if 'latency' in google_config_settings:
            raise KeyError("Option key 'latency' only supported for streaming requests.")

    if 'languageCode' not in google_config_settings:
        raise KeyError("Config missing required key 'languageCode'/'language_code'.")

    # Ensure 'languageCode' is English, Mod9 Engine's default. Mod9 assumes this input.
    if 'en-' in google_config_settings['languageCode']:
        # Mod9 Engine does not accept an input for language code.
        del google_config_settings['languageCode']
    else:
        raise ValueError(
            f"Language {google_config_settings['languageCode']} not supported. "
            'Mod9 ASR Engine supports English at this time.'
        )

    # ``to_json()`` populates absent attributes of config with falsy values -> exceptions later.
    google_config_settings = {
        key: value for key, value in google_config_settings.items() if value
    }

    # A subset of possible Google keys are supported by this wrapper and the Mod9 Engine.
    for google_key in google_config_settings:
        if google_key not in settings.google_allowed_keys:
            raise KeyError(f"Option key '{google_key}' not supported.")

    # Translate google_config_settings keys to corresponding Mod9 keys and values.
    for google_key, google_value in google_config_settings.items():
        mod9_key = settings.google_to_mod9_key_translations[google_key]
        # A subset of possible Google values are supported by this wrapper and the Mod9 Engine.
        if google_value in settings.mod9_keys_to_allowed_values[mod9_key]:
            # Some Mod9 values are equivalent to Google values. Others to be translated later.
            mod9_config_settings[mod9_key] = google_value
        else:
            raise KeyError(f"Option value '{google_value}' not supported for key '{google_key}'.")

    # Do first step of translating Mod9 'encoding' value from Google to Mod9 format + encoding.
    # Format will map to 'wav' or 'raw'. Set placeholder until determined by file header.
    mod9_config_settings['format'] = None
    if 'encoding' in mod9_config_settings:
        if mod9_config_settings['encoding'] == 'ENCODING_UNSPECIFIED':
            mod9_config_settings['format'] = 'wav'
            del mod9_config_settings['encoding']
        else:
            mod9_config_settings['encoding'] = \
                settings.google_encoding_to_mod9_encoding[mod9_config_settings['encoding']]

    # Set N-best settings.
    #  ``result_from_mod9()`` iterates through alternatives.
    n_best_N = mod9_config_settings.get('transcript-alternatives')
    if n_best_N is not None:
        if n_best_N == 0:
            # Google sets n_best_N: 0 -> 1.
            n_best_N = 1
        mod9_config_settings['transcript-alternatives'] = n_best_N

    # This option only applies with speech_mod9.
    if mod9_config_settings.get('phrase-alternatives'):
        mod9_config_settings['phrase-intervals'] = True

    # These speech_mod9 options override all prior options that might have been set.
    if 'options_json' in mod9_config_settings:
        try:
            extra_options = json.loads(mod9_config_settings['options_json'])
        except Exception:
            raise ValueError('Could not parse additional options JSON.')
        mod9_config_settings.update(extra_options)
        del mod9_config_settings['options_json']

    return mod9_config_settings


def google_audio_settings_to_mod9(google_audio_settings):
    """
    Map from Google-style audio input to Mod9 TCP server-style audio
    input.

    Args:
        google_audio_settings (dict):
            Google-style audio.

    Returns:
        Union[str, Iterable[bytes]]:
            Mod9-style audio to pass to Mod9 ASR Engine TCP Server.
    """

    if not google_audio_settings:
        return None

    # Require one, and only one, of 'uri' or 'content'.
    if 'uri' in google_audio_settings and 'content' in google_audio_settings:
        raise ConflictingGoogleAudioSettingsError("Got both 'uri' and 'content' keys.")
    if 'uri' not in google_audio_settings and 'content' not in google_audio_settings:
        raise KeyError("Got neither 'uri' nor 'content' key.")

    if 'uri' in google_audio_settings:
        mod9_audio_settings = google_audio_settings['uri']
    else:
        # Decode google_audio_settings byte string if Base64 encoded; send chunks in generator.
        try:
            byte_string = base64.b64decode(google_audio_settings['content'], validate=True)
        except BinasciiError:
            byte_string = google_audio_settings['content']
        mod9_audio_settings = (
            byte_string[i:i+CHUNKSIZE] for i in range(0, len(byte_string), CHUNKSIZE)
        )

    return mod9_audio_settings


def result_from_mod9(mod9_results, logger=None):
    """
    Map from Mod9 TCP server-style output to Google-style output.

    Args:
        mod9_results (Iterable[dict]):
            Mod9-style results from the Mod9 ASR Engine TCP Server.

    Yields:
        dict:
            Google-style result.
    """

    # Longer audio comes chopped into segments.
    for mod9_result in mod9_results:
        if mod9_result['status'] != 'processing':
            # Non-'processing' status -> failure or transcription is complete.
            if mod9_result['status'] == 'failed':
                raise Mod9EngineFailedStatusError(f"Mod9 server issues 'failed': {mod9_result}.")
            elif mod9_result['status'] != 'completed':
                if logger:
                    logger.error("Unexpected Mod9 server response: %s.", mod9_result)
                else:
                    logging.error("Unexpected Mod9 server response: %s.", mod9_result)
            else:
                # Status 'completed' is final response (with no transcript).
                break

        if 'result_index' not in mod9_result:
            # This is likely benign ... let's ignore it.
            # TODO: should our module have logging?
            continue

        alternatives = []
        if 'alternatives' in mod9_result:
            for alternative_number, mod9_alternative in enumerate(mod9_result['alternatives']):
                alternative = build_google_alternative(mod9_result['result_index'])
                if alternative_number == 0 and 'transcript_formatted' in mod9_result:
                    alternative['transcript'] += mod9_result['transcript_formatted']
                else:
                    alternative['transcript'] += mod9_alternative['transcript']
                alternatives.append(alternative)
        else:
            # Partial results (``.final`` == ``False``) from Mod9 do not have alternatives
            #  or ``.transcript_formatted``.
            #  Requests without transcript alternatives do not have alternatives,
            #  but may have ``.transcript_formatted``.
            alternative = build_google_alternative(mod9_result['result_index'])
            if 'transcript_formatted' in mod9_result:
                alternative['transcript'] += mod9_result['transcript_formatted']
            else:
                alternative['transcript'] += mod9_result['transcript']
            alternatives.append(alternative)

        # Build the WordInfo if Mod9 has returned word-level results.
        #  If returning N-best, only 1-best gets word alternatives.
        if 'words' in mod9_result:
            words = []
            for mod9word in mod9_result['words']:
                new_word = OrderedDict()
                if 'interval' in mod9word:
                    start_time, end_time = mod9word['interval']
                    new_word['startTime'] = "{:.3f}s".format(start_time)
                    new_word['endTime'] = "{:.3f}s".format(end_time)

                new_word['word'] = mod9word['word']

                if 'confidence' in mod9word:
                    new_word['confidence'] = mod9word['confidence']

                words.append(new_word)
            alternatives[0]['words'] = words

        google_result = OrderedDict(
            [
                ('alternatives', alternatives),
                ('isFinal', mod9_result['final']),
                # NOTE: this is only returned in v1p1beta1, and it's lowercase for some reason.
                ('languageCode', 'en-us'),
                ('resultEndTime', "{:.3f}s".format(mod9_result['interval'][1]))
            ]
        )
        if not mod9_result['final']:
            google_result['stability'] = 0.0  # Google's default.

        if 'phrases' in mod9_result:
            google_result['phrases'] = mod9_result['phrases']
            for phrase in google_result['phrases']:
                interval = phrase.pop('interval')
                phrase['startTime'] = "{:.3f}s".format(interval[0])
                phrase['endTime'] = "{:.3f}s".format(interval[1])

        yield google_result


def build_google_alternative(transcript_number, confidence_value=1.0):
    """
    Build template for Google alternative.

    Args:
        transcript_number (int):
            Indicate the segment/endpoint the alternative is a part of.
        confidence_value (float):
            Rating in [0.0, 1.0] indicating confidence this alternative
            is the true transcript/one-best (default is 1.0).

    Returns:
        dict:
            Google-style transcript alternative (i.e. one of N-best list).
    """

    alternative = OrderedDict([('transcript', '')])
    # Google transcripts after the first start with a space.
    if transcript_number > 0:
        alternative['transcript'] += ' '

    # Add placeholder value for transcript-level confidence.
    alternative['confidence'] = confidence_value

    return alternative


def google_type_result_from_dict(
        google_result_dicts,
        google_result_type,
        module,
):
    """
    Convert dict-type result iterable to Google-type result generator.

    Args:
        google_result_dicts (Iterable[dict]):
            Google-style results.
        google_result_type (Union[module.RecognizeResponse, module.StreamingRecognizeResponse]):
            Google-like-type to return.
        module (module):
            Module to read Google-like-types from, in case of
            subclassing.

    Yields:
        Union[module.RecognizeResponse, module.StreamingRecognizeResponse]:
            Google-like-type result.
    """

    for google_result_dict in google_result_dicts:
        if google_result_type == module.SpeechRecognitionResult:
            # ``from_json()`` complains if attributes that do not exist in a protobuf are passed.
            if 'isFinal' in google_result_dict:
                google_result_dict.pop('isFinal')
            if 'resultEndTime' in google_result_dict:
                google_result_dict.pop('resultEndTime')
        # Internal camelCase keys are converted to snake_case by from_json().
        #  See docstring in GoogleConfigurationSettingsAndMappings for more info.
        yield google_result_type.from_json(json.dumps(google_result_dict))
