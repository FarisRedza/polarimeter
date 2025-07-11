# Setup
`python3 -m venv .venv`
`pip install -r requirements.txt`

# Server
`python3 -m polarimeter.remote_server`

# GUI
## Linux
`python3 -m venv .venv --system-site-packages`\
`pip install -r requirements.txt`

## MacOS
`brew install pygobject3 libadwaita`\
`python3 -m venv .venv --system-site-packages`\
`pip install -r requirements.txt`

## Windows
The GUI is currently unsupported on Windows but using WSL might work

## Usage
`python3 -m polarimeter.gui` for local polarimeter\
`python3 -m polarimeter.remote_gui` for remote polarimeter