#!/bin/bash
: << 'COMMENT'
Note: in order to build the Windows version on Linux, you'll need to have Python 3.12 installed. After that you'll need to install the dependencies via Wine:
wine python -m pip install pyinstaller pyqt6 pillow pydub toml
COMMENT

clear

APPLICATION_DIR="$HOME/Applications"
VERSION="2.1"
OUTPUT_NAME="KZI-Cartridge-Generator-${VERSION}"

mkdir -p $APPLICATION_DIR

echo -e "\nCreating standalone executable..."

# Make sure icon.ico and icon.png are both in /tmp
wine python -m PyInstaller --onefile --windowed --icon=icon.ico --add-data "icon.png;." main.py --distpath $APPLICATION_DIR --workpath /tmp/ --specpath /tmp/ --name $OUTPUT_NAME

echo -e "\nDone! Windows build has been stored in $APPLICATION_DIR/$OUTPUT_NAME"

