# Manual Installation

If you want to install on Linux or macOS follow the following manual installation steps.

For developers, see [below](#contributing) for instructions.

## Install

1) Download and install [Python](https://www.python.org/downloads/), if you do not have it installed already. (If you are already using Python and know what you're doing, you may want to create a virtual environment.)
2) Download the contents of this repository with the "Download ZIP" option and unzip it to where you want to save the application.
3) Install Python dependencies: Open a terminal window in the directory where you unzipped the application files and run the following command:
```
pip install -r requirements.txt
```
4) Run the application by starting `app.py`.
5) Optionally: create a shortcut to `app.py` to quickly start it. There's an app icon you can use in `./manr/resources/img/icon.ico`.

## Uninstall

On Windows: Simply delete the application folder. Additionally, delete settings and caches in `%APPDATA%/manr` and `%LOCALAPPDATA%/manr`.

# Contributing

## Reporting Issues & Contributing Code

Bug reports and feature requests are welcome. Please open an issue.

If you would like to contribute code, please open an issue first to discuss
the change before submitting a pull request.

## Development Environment

1. Install the latest Python release from your package manager or from [python.org](https://www.python.org/downloads/)
2. Clone the repository with git.
```
git clone https://codeberg.org/manr/manr_chat.git
```
3. Create and activate a new virtual environment:
```
python -m venv manr_venv
source manr_venv/bin/activate
```
4. Install dependencies:
```
pip install -r requirements.txt
```
5. Run the application:
python app.py

## Building the Windows Setup executable

To build the Windows Setup, you need PyInstaller and [Inno Setup](https://jrsoftware.org/isinfo.php).

1. Set up a clean build environment, and install the requirements
```
pip install -r requirements.txt
pip install pyinstaller
```
2. Bundle with PyInstaller
```
pyinstaller manr_pyinstaller.spec
```
3. Building the Setup executable
```
iscc.exe manr_inno_setup.iss
```

# Contact

Email the authors at: manr&zwj;-chat&nbsp;(at)&nbsp;proton.me