#!/usr/bin/env python3
# TODO: describe this file.

import argparse
import json

# from google.protobuf import json_format

from mod9.asr import speech_mod9 as speech
# from mod9.asr import speech


def prepare_dict_test_inputs(content_file_name):
    encoding = speech.RecognitionConfig.AudioEncoding.LINEAR16
    sample_rate_hertz = 8000
    language_code = 'en-US'
    config = {
        'encoding': encoding,
        'sample_rate_hertz': sample_rate_hertz,
        'language_code': language_code,
        # 'enable_word_confidence': True,
        # 'enable_word_time_offsets': True,
        # 'max_alternatives': 2,
        'max_phrase_alternatives': 2,
    }
    with open(content_file_name, 'rb') as content_file:
        content = content_file.read()
    audio = {'content': content}
    return config, audio


# TODO: Remove or upgrade this old code.
# def dict_inputs_to_google_inputs(config, audio):
#     google_config = json_format.ParseDict(config, speech.RecognitionConfig())
#     google_audio = speech.RecognitionAudio(content=audio['content'])
#     return google_config, google_audio


def recognize_test(file_name, speech_client_input_type='dict'):
    client = speech.SpeechClient()
    config_dict, audio_dict = prepare_dict_test_inputs(content_file_name=file_name)
    if speech_client_input_type == 'dict':
        return client.recognize({'config': config_dict, 'audio': audio_dict})
    # elif speech_client_input_type == 'google_types':
    #     config_google, audio_google = dict_inputs_to_google_inputs(config_dict, audio_dict)
    #     return client.recognize({'config': config_google, 'audio': audio_google})
    else:
        raise TypeError(
            "SpeechClient() accepts 'dict' or 'google_types' input. "
            f"'{speech_client_input_type}' not allowed."
        )


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument(
        '-f', '--file',
        dest='file_name',
        required=True,
        type=str,
        help='Local WAV format audio file to be transcribed.',
    )
    parser.add_argument(
        '-t', '--type',
        dest='input_type',
        default='dict',
        choices=['dict', 'google_types'],
        type=str,
        help="Choose from SpeechClient's allowed input types.",
    )
    args = parser.parse_args()

    response = recognize_test(args.file_name, args.input_type)

    if isinstance(response, dict):
        print(json.dumps(response, indent=2), end='')
    else:
        print(response, end='')
