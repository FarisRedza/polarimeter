# Setup
`python3 -m venv .venv`\
`source .venv/bin/activate`\
`pip install -r requirements.txt`

# Server
`python3 -m polarimeter.remote_server`

# GUI
Use `--system-site-packages` if you want to allow the python environment to access the system's `pygobject` for GTK and Adwaita libraries to avoid having to compile `pygobject` as PyPI only hosts the source for this module. Otherwise, run `pip install pygobject` after installing the rest of the packages in requirements.txt

## Linux
`python3 -m venv .venv --system-site-packages`\
`source .venv/bin/activate`\
`pip install -r requirements.txt`\
or\
`sudo apt install build-essential libcairo2-dev libgirepository-2.0-dev python3-dev`\
`python3 -m venv .venv`\
`source .venv/bin/activate`\
`pip install -r requirements.txt`\
`pip install pygobject`

## MacOS
`brew install pygobject3 libadwaita`\
`python3 -m venv .venv --system-site-packages`\
`source .venv/bin/activate`\
`pip install -r requirements.txt`
or\
`brew install pygobject3 libadwaita`\
`python3 -m venv .venv`\
`source .venv/bin/activate`\
`pip install -r requirements.txt`
`pip install pygobject`

## Windows
The GUI is currently unsupported on Windows but using WSL might work

## Usage
`python3 -m polarimeter.gui` for local polarimeter\
`python3 -m polarimeter.remote_gui` for remote polarimeter