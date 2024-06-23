#! /usr/bin/env python3

import socket
import select
import os
import threading
import struct
import warnings
from time import monotonic as time
from my_logger import my_log

warnings.filterwarnings("ignore")

DEFAULT_DURATION = 120

try:
    import pyperclip
except ImportError:
    raise ImportError(
        "pyperclip package not found. Please reinstall pyperclip to use this script."
    )

try:
    import sounddevice as sd
except ImportError:
    raise ImportError(
        "sounddevice package not found. Please reinstall sounddevice to use this script."
    )

try:
    import whisper
except ImportError:
    raise ImportError(
        "whisper package not found. Please reinstall whisper to use this script."
    )


class Recorder:
    """Recorder class for audio recording."""

    def __init__(
        self,
        fs: int = 16_000,
        duration: int = DEFAULT_DURATION,
        model_name: str = "base",
        ewm_alpha: float = 1 / 20,
    ):
        """Initialize the Recorder object.

        Args:
            fs (int): The sample rate in kHz. Default is 16 kHz.
            duration (int): The maximum duration of the recording in seconds. Default is 120 seconds.
            model_name (str): The name of the model to load. Default is "base".
            ewm_alpha (float): The alpha value for the EWMA of the WPM. Default is 1/20.

        """

        self.fs = fs
        self.duration = duration
        self.recording = None
        self.start_time = None
        self.copy_to_clipboard = True

        self.ewma_wpm: float = None
        self.ewm_alpha: float = ewm_alpha
        self.wpm_languages: set = {
            "en",
            "de",
            "es",
            "fr",
            "it",
            "nl",
            "pl",
            "pt",
            "ru",
            "tr",
        }

        try:
            self.model = whisper.load_model(model_name, in_memory=True)
        except Exception as e:
            error_message = (
                f"Failed to load whisper model '{model_name}'. Make sure the model is available and correctly configured. "
                f"Available models are 'tiny', 'base', 'small', 'medium' and 'large'. "
            )
            print(error_message)
            raise type(e)(error_message).with_traceback(e.__traceback__)

    def start_recording(self):
        print("Recording ", end="")
        self.start_time = time()
        self.recording = sd.rec(
            int(self.fs * self.duration), samplerate=self.fs, channels=1
        )

    def stop_recording(self):
        print("stopped. ", end="")
        sd.stop()
        elapsed_time = time() - self.start_time
        self.recording = self.recording[: int(elapsed_time * self.fs)]

        print(f"Recorded {elapsed_time:.2f} seconds. ", end="", flush=True)

        return self.transcribe_audio()

    def transcribe_audio(self):
        try:
            transcription_start_time = time()
            r = self.model.transcribe(self.recording[:, 0], temperature=0.0)

            # And process the output
            language = r["language"]

            text: str = "\n".join((f["text"].lstrip() for f in r["segments"]))

            time_to_transcribe: float = time() - transcription_start_time
            total_time_elapsed: float = time() - self.start_time

            transcribed_text: str = str(text).rstrip().lstrip()

            # Print the elapsed time and calculate the WPM (words per minute)
            if language in self.wpm_languages:
                wpm: float = float(
                    len(transcribed_text.split()) / (total_time_elapsed / 60)
                )

                # And recalc the EWMA
                if self.ewma_wpm is None:
                    self.ewma_wpm = wpm

                else:
                    self.ewma_wpm = (
                        self.ewm_alpha * wpm + (1 - self.ewm_alpha) * self.ewma_wpm
                    )

                additional_info: str = f"WPM {wpm:.2f} EWMA WPM {self.ewma_wpm:.2f}"

            else:
                additional_info: str = ""

            summary = f"Transcribed in {time_to_transcribe:.2f}s, total {total_time_elapsed:.2f}s {additional_info}"
            print(summary)

            print(80 * "=")
            print(transcribed_text)
            print(80 * "=", end="\n")
            if self.copy_to_clipboard:
                pyperclip.copy(transcribed_text)
            return transcribed_text
        except Exception as e:
            print(f"Error during transcription:\n{str(e)}")
            return f"Error during transcription:\n{str(e)}"


class TranscriptionServer:
    def __init__(self):
        self.recorder = Recorder()
        self.recording_lock = threading.Lock()
        self.transcribing_lock = threading.Lock()
        self.is_recording = False
        self.transcription_queue = []

    def start_recording(self, duration=None):
        with self.recording_lock:
            if self.is_recording:
                return False, "Error: Already recording"
            self.is_recording = True
            if duration:
                self.recorder.duration = duration
            else:
                self.recorder.duration = DEFAULT_DURATION
            self.recorder.start_recording()
            return True, "Recording started"

    def stop_recording_and_transcribe(self, copy_to_clipboard=True):
        with self.recording_lock:
            if not self.is_recording:
                return False, "Error: Not currently recording"
            self.is_recording = False

        with self.transcribing_lock:
            self.recorder.copy_to_clipboard = copy_to_clipboard
            try:
                transcription = self.recorder.stop_recording()
                return True, transcription
            except Exception as e:
                return False, f"Error during transcription: {str(e)}"


def handle_client_connection(client_socket, server):
    try:
        command = struct.unpack(">I", client_socket.recv(4))[0]
        if command == 1:  # Start recording
            ready_to_read, _, _ = select.select([client_socket], [], [], 0)
            duration = None
            if ready_to_read:
                duration = struct.unpack(">I", client_socket.recv(4))[0]
            success, response = server.start_recording(duration)
            client_socket.sendall(
                struct.pack(">I", int(not success))
                + struct.pack(">I", len(response))
                + response.encode("utf-8")
            )
        elif command == 2:  # Stop recording and transcribe
            ready_to_read, _, _ = select.select([client_socket], [], [], 0)
            copy_to_clipboard = True
            if ready_to_read:
                struct.unpack(">I", client_socket.recv(4))
                copy_to_clipboard = False
            success, transcription = server.stop_recording_and_transcribe(
                copy_to_clipboard
            )
            response = transcription.encode("utf-8")
            client_socket.sendall(
                struct.pack(">I", int(not success))
                + struct.pack(">I", len(response))
                + response
            )
    finally:
        client_socket.close()


def main():
    server = TranscriptionServer()

    server_address = "/tmp/1099430_whisper_server_socket"

    server_socket = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)

    try:
        os.unlink(server_address)
    except OSError:
        if os.path.exists(server_address):
            raise

    server_socket.bind(server_address)
    server_socket.listen(5)
    print(f"Server listening on {server_address}")

    try:
        while True:
            client_socket, _ = server_socket.accept()
            client_handler = threading.Thread(
                target=handle_client_connection,
                args=(client_socket, server),
            )
            client_handler.start()
    except KeyboardInterrupt:
        server_socket.close()
        print("\nServer shut down.")


if __name__ == "__main__":
    main()
