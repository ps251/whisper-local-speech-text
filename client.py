#! /usr/bin/env python3

import socket
import struct
import argparse


def send_command(command, server_address, duration=None):
    client_socket = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    client_socket.connect(server_address)
    try:
        if command == 1 and duration is not None:
            message = struct.pack(">I", command) + struct.pack(">I", duration)
        else:
            message = struct.pack(">I", command)
        client_socket.sendall(message)
        response_length = struct.unpack(">I", client_socket.recv(4))[0]
        if response_length > 0:
            response = b""
            while len(response) < response_length:
                packet = client_socket.recv(4096)
                if not packet:
                    break
                response += packet
            return response.decode("utf-8")
    finally:
        client_socket.close()


def main():
    parser = argparse.ArgumentParser(description="Client for transcription server")
    parser.add_argument(
        "command", choices=["start", "stop"], help="Command to send to the server"
    )
    parser.add_argument(
        "--duration", type=int, help="Optional duration for the recording in seconds"
    )
    args = parser.parse_args()

    server_address = "/tmp/1099430_whisper_server_socket"

    if args.command == "start":
        send_command(1, server_address, args.duration)
    elif args.command == "stop":
        transcription = send_command(2, server_address)
        print(transcription)


if __name__ == "__main__":
    main()
