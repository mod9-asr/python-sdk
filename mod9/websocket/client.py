#!/usr/bin/env python3

"""
Command-line WebSocket client for use with Mod9 ASR WebSocket server.

The first positional argument is the URI of the WebSocket server to connect to.
The second positional argument may specify JSON-formatted request options.

Audio data may be read from stdin and sent to the specified WebSocket server.
Meanwhile, messages received from the WebSocket server are printed on stdout.

Example usage with a pre-recorded file:
```
curl -sL mod9.io/hi.wav | client.py ws://localhost:9980 > results.jsonl
```

Example usage with live streaming audio:
```
sox -dqV1 -twav -r16000 -c1 -b16 - | client.py wss://mod9.io '{"partial":true}'
```


"""

import argparse
import asyncio
import sys

import websockets

# This is a fairly small default, set as a lowest common denominator for all use cases.  The ASR
# Engine receives data with a network buffer size of 128 bytes, but also utilizes an internal audio
# buffer size which is reflected by its "latency" request option. For example, at a default latency
# of 0.24s: 16kHZ 16-bit linear PCM audio would buffer as 0.24 * 16000 * 16/8 = 7680 bytes.
# At 0.10s:  8kHz  8-bit mu-law PCM audio would buffer as 0.10 * 8000 * 8/8 = 800 bytes.
# As general guidance: this parameter can be much larger for batch processing of pre-recorded audio,
# or if a real-time streaming application appears to be incurring significant networking overhead.
AUDIO_MESSAGE_SIZE = 128


async def from_stdin_to_engine(websocket, message_size=AUDIO_MESSAGE_SIZE):
    """
    Read chunked audio from stdin and send as messages to Engine WebSocket.
    Return when stdin is closed, after sending an empty message.

    Args:
        websocket (websockets.server.WebSocketServerProtocol):
            Engine WebSocket to send to (expects empty-message termination).
        message_size (int):
            Read audio chunks of this size; affects streaming latency.

    Returns:
        None
    """
    # Async read from stdin: https://stackoverflow.com/q/64303607/281536
    reader = asyncio.StreamReader()
    protocol = asyncio.StreamReaderProtocol(reader)
    await asyncio.get_event_loop().connect_read_pipe(lambda: protocol, sys.stdin.buffer)

    while True:
        # Read audio bytes from stdin, chunked at the message size.
        audio_chunk = await reader.read(message_size)

        if audio_chunk:
            # Send audio chunk as a WebSocket message of the same size.
            await websocket.send(audio_chunk)
        else:
            break

    # Send an empty message to terminate audio data.
    await websocket.send(b'')


async def from_engine_to_stdout(websocket):
    """
    Receive reply messages from Engine WebSocket, and print to stdout.
    Return when the WebSocket connection is closed by the Engine.

    Args:
        websocket (websockets.server.WebSocketServerProtocol):
            WebSocket to receive from (expecting single-line JSON replies).

    Returns:
        None
    """
    while True:
        try:
            reply_message = await websocket.recv()
        except websockets.ConnectionClosedOK:
            break

        reply_json = reply_message.decode()
        print(reply_json)


async def communicate_with_engine(uri, options_json, message_size):
    async with websockets.connect(uri) as websocket:
        # Send JSON-formatted options as initial message.
        options_message = options_json.encode('utf-8')
        await websocket.send(options_message)

        # Send audio to Engine in an async task.
        # NOTE: if the client sends audio for a command that does not expect it, or if the Engine
        #       closes the connection early (e.g. on error), then it may take 10 seconds for the
        #       WebSocket connection to be closed by the Engine.
        # TODO: add logic to this client to await/parse the first Engine reply before proceeding?
        send_audio = asyncio.get_event_loop().create_task(
            from_stdin_to_engine(websocket, message_size),
        )

        # Receive replies from Engine in an async task.
        recv_replies = asyncio.get_event_loop().create_task(
            from_engine_to_stdout(websocket),
        )

        # Wait for the Engine to send all its replies, and then close the connection.
        await recv_replies

        # Cancel any audio remaining to be sent, since the Engine can't accept it anymore.
        send_audio.cancel()


def main():
    parser = argparse.ArgumentParser(formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument(
        'uri',
        metavar='URI',
        help='URI of the WebSocket server.',
        default='ws://localhost:9980',
    )
    parser.add_argument(
        'options_json',
        metavar='OPTIONS_JSON',
        nargs='?',
        help='JSON-formatted request options to pass to ASR Engine.',
        default='{}'
    )
    parser.add_argument(
        '--message-size',
        help='Size of audio sent in each WebSocket message, affecting streaming latency.',
        default=AUDIO_MESSAGE_SIZE,
        type=int,
    )
    args = parser.parse_args()

    try:
        asyncio.get_event_loop().run_until_complete(
            communicate_with_engine(
                args.uri,
                args.options_json,
                args.message_size,
            )
        )
    except KeyboardInterrupt:
        sys.exit(130)  # Don't show Python traceback.
    except Exception:
        print(f"ERROR: Unable to communicate with {args.uri} ... check if server is accessible?")
        sys.exit(1)


if __name__ == '__main__':
    main()
