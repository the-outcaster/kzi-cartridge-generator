# Kazeta Cartridge Generator
Swiss army knife utility for [Kazeta](https://kazeta.org)/[Kazeta+](https://github.com/the-outcaster/kazeta-plus) that allows you to do the following:
- create, edit, and test Kazeta information (`.kzi`) files
- Kazeta runtime (`.kzr`) creator -- create Windows runtime files, Linux runtime files, or emulator runtimes
- Kazeta package (`.kzp`) creator -- compress your games to save space and simplify the way your games are transferred (Kazeta+ only)
- mount and unmount `.kzr` and `.kzp` files with `erofsfuse`
- create ISOs for your cartridges, and burn them onto CDs/DVDs (Kazeta+ only)
- create and burn audio CDs (Kazeta+ only)
- create and edit themes for the BIOS (Kazeta+ only)

![Screenshot_20260326_110133](https://github.com/user-attachments/assets/8452b7aa-7d9e-4266-af35-5086209f6888)

Anti-AI users beware: **this is a vibe-coded tool.**

## Requirements
- `python3.x` (you may run into issues with certain features if you use Python 3.14 or later)
- for CD/DVD burning:
  - `genisoimage`
  - `wodim`
  - `pkexec`
- for KZR/KZP compression/mounting:
  - `erofs-utils`
  - `erofsfuse`
- for theme creation file conversion:
  - `ffmpeg`

## Usage
Simply head over to the [Releases](https://github.com/the-outcaster/kzi-cartridge-generator/releases) page, download the latest AppImage, and execute it. Note that you may have to mark it as executable in order to run it. Experimental support is also provided for Windows.

*NOTE: fetching icons from SteamGridDB requires you to log in to the website with your Steam account, and supplying your [API key](https://www.steamgriddb.com/profile/preferences/api) when the application asks you for it.*

## Development Requirements
Python libraries needed:
- `pyqt6`
- `pillow` 
- `certifi`
- `toml`
- `pydub`

Clone the repository:

```
git clone https://github.com/the-outcaster/kzi-cartridge-generator.git
cd kzi-cartridge-generator
```
  
You may need to use a Python virtual environment if you have Python 3.14 or later, due to certain dependencies being deprecated:

```
python3.12 -m venv venv
source venv/bin/activate
```

Install required Python packages:

`pip install pyqt6 pillow certifi toml pydub`

Run the application from your terminal:

`python main.py`

When you're ready to build the AppImage, run `./build.sh`. The AppImage will be placed in `~/Applications`.

## Credits
This project was created by [Linux Gaming Central](https://linuxgamingcentral.org).

Learn more about the Kazeta project at [kazeta.org](https://kazeta.org).
