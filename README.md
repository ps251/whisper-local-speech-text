# whisper-local-speech-text

This project lends some code and ideas from [Whisper Clipboard](https://openai.com/research/whisper). Unlike the original, which uses a terminal UI, it consists of a separate background service and client script. The client script communicates with the background service, handling commands and outputting transcribed result. This setup allows for the use of global keybindings, enabling speech-to-text functionality from anywhere or within other scripts to do something interesting. 
Copy to clipboard of result text is optional and can be controlled via flag. If you have notify-send in your path (typically on Linux), you can also get desktop notifications. Check out "CLI Options" for all options.

## Prerequisites
* Python 3.10 or higher (probably works with lower versions, but not tested)
* ffmpeg


## Installation

```bash
# Step 1: Clone the repository.
git clone https://github.com/ps251/whisper-local-speech-text

# Step 2: cd into the cloned repository.
cd whisper-local-speech-text

# Step 3: (Optional) Create a virtual environment and activate it.
python -m venv venv
source venv/bin/activate
# On Windows, activate the virtual environment with 'venv\Scripts\activate'

# Step 4: Install the required packages.
pip install -r requirements.txt

# Step 5: Start the server.
python server.py

# Step 6: You can now use the client script to start and stop recording. With the stop command you will also get the result text to stdout 
python client.py start --duration 900
python client.py stop

```

## Usage


```bash
# Start the server
python server.py

Start 
# You can now use the client script to start and stop recording. With the stop command you will also get the result text to stdout
python client.py start --duration 900
python client.py stop
```

## CLI Options


| **Option**             | **Description**                                    | **Default** |
|------------------------|----------------------------------------------------|-------------|
| `command`              | The command to send to the server. Must be either `start` or `stop`. | N/A         |
| `--duration`           | Specifies the maximum duration of the recording in seconds. | N/A         |
| `--no-clipboard`       | Do not copy the transcription to the clipboard. This option negates the default behavior of copying the transcription. | `True`      |
| `--notify`             | Send desktop notifications when the transcription is complete. Must have notify-send command in path | `False`     |


### Example shell scripts (bash)

The following scripts assume that you've installed the python packages in a virtual environment. The server must already be running.

Start transcription.
```bash
cd /path/to/repo/whisper-local-speech-text/
source venv/bin/activate
python client.py start --notify --duration 900
```

Stop transcription. Unless a --no-insert flag is present, paste the result into the current app by simulating a Ctrl+v key press
```bash
# Check for the --no-insert flag
NO_INSERT=false
for arg in "$@"
do
    if [ "$arg" == "--no-insert" ]; then
        NO_INSERT=true
        break
    fi
done

cd /path/to/repo/whisper-local-speech-text/
source venv/bin/activate
python client.py stop --notify

# Only run xdotool command if --no-insert flag is not present
if [ "$NO_INSERT" = false ]; then
    xdotool key ctrl+v
fi

```
