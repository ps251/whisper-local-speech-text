#! /usr/bin/env python3

import socket
import struct
import argparse
import sys
import subprocess


def send_command(command, server_address, duration=None, copy_to_clipboard=True):
    client_socket = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    client_socket.connect(server_address)
    try:
        message = struct.pack(">I", command)
        if command == 1 and duration is not None:
            message += struct.pack(">I", duration)
        if command == 2 and not copy_to_clipboard:
            message += struct.pack(">I", 1)
        client_socket.sendall(message)
        is_error = struct.unpack(">I", client_socket.recv(4))[0]
        response_length = struct.unpack(">I", client_socket.recv(4))[0]
        if response_length > 0:
            response = b""
            while len(response) < response_length:
                packet = client_socket.recv(4096)
                if not packet:
                    break
                response += packet
            return is_error, response.decode("utf-8")
    finally:
        client_socket.close()


def send_notification(message, is_error=False):
    try:
        if is_error:
            subprocess.run(
                [
                    "notify-send",
                    "-u",
                    "critical",
                    "Whisper Transcription Error",
                    message,
                ]
            )
        else:
            subprocess.run(["notify-send", "Whisper Transcription", message])
    except FileNotFoundError:
        print("notify-send command not found. Notification not sent.", file=sys.stderr)


def main():
    parser = argparse.ArgumentParser(description="Client for transcription server")
    parser.add_argument(
        "command", choices=["start", "stop"], help="Command to send to the server"
    )
    parser.add_argument(
        "--duration", type=int, help="Optional duration for the recording in seconds"
    )
    parser.add_argument(
        "--no-clipboard",
        action="store_false",
        help="Don't copy transcription to clipboard",
    )
    parser.add_argument(
        "--notify",
        action="store_true",
        help="Send desktop notifications",
    )
    args = parser.parse_args()

    server_address = "/tmp/1099430_whisper_server_socket"

    if args.command == "start":
        is_error, response = send_command(1, server_address, args.duration)
        if is_error:
            print(response, file=sys.stderr)
            if args.notify:
                send_notification(response, is_error=True)
            sys.exit(1)
        else:
            print(response)
            if args.notify:
                send_notification("Recording started")
    elif args.command == "stop":
        is_error, transcription = send_command(
            2, server_address, copy_to_clipboard=args.no_clipboard
        )
        if is_error:
            print(transcription, file=sys.stderr)
            if args.notify:
                send_notification(transcription, is_error=True)
            sys.exit(1)
        else:
            print(transcription)
            if args.notify:
                send_notification("Transcription completed" "\n" + transcription)


if __name__ == "__main__":
    main()
