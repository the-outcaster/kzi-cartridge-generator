# Kazeta Cartridge Generator
Simple Python GUI application for creating and editing `.kzi` (Kazeta information) files for [Kazeta](https://kazeta.org)/[Kazeta+](https://github.com/the-outcaster/kazeta-plus).

![Kazeta Cartridge Generator screenshot](https://i.imgur.com/mNnOkjf.png)

## Features

- graphical interface: Easily create and edit `.kzi` files without manual text editing.
- load existing files: Open and parse existing `.kzi` files to quickly modify them.
- auto-generating ID: The Game ID is automatically generated from the Game Name as you type.
- parameter support: Add optional launch parameters for executables and GameScope options.
- icon fetching: Automatically search for and download 64x64 game icons from [SteamGridDB](https://www.steamgriddb.com/).
- runtime downloader: Download official Kazeta runtimes for various platforms directly within the app.
- smart path handling: Automatically creates relative paths and adds quotes to executable paths containing spaces.
- `.kzi` file preview
- test Linux/Windows-based cartridges before export
- D-pad reversal fix for native Linux games: note **this is a Kazeta+-only feature for now.**
- game and audio CD/DVD burning

*NOTE: fetching icons from SteamGridDB requires you to log in to the website with your Steam account, and supplying your [API key](https://www.steamgriddb.com/profile/preferences/api) when the application asks you for it.*

## Requirements
- `python3.13` (you may run into issues with certain features if you use Python 3.14 or later)
- `genisoimage`
- `wodim`

## Usage
Simply head over to the [Releases](https://github.com/the-outcaster/kzi-cartridge-generator/releases) page, download the latest AppImage, and execute it. Note that you may have to mark it as executable in order to run it.

If you want to fetch icons from SteamGridDB: the first time you use this feature, you will be prompted to enter your API key. This key will be saved to `~/.config/kzi-cartridge-generator/config.json` for future use.

Fill out the fields:
- game name: The display name of your game.
- game ID: Automatically generated from the game name.
- executable path: The path to the game's main executable or ROM file.
- additional parameters (optional): Any command-line arguments to pass to the executable.
- icon path: The path to the game's 64x64 pixel icon.
- gamescope options (optional) : Parameters to pass to [GameScope](https://github.com/kazetaos/kazeta/wiki/Gamescope-Options).
- runtime: Select the appropriate Kazeta runtime for the game.

When finished, generate the `.kzi` file by clicking "Generate .kzi File". The file will be saved with a name corresponding to the Game ID.

You can also load existing `.kzi` files by clicking "Load .kzi File" and make any necessary adjustments before exporting.

## Development Requirements
- Python 3.x
- Tkinter (usually included with standard Python installations)
- Python libraries: `Pillow` and `certifi`

1. Clone the repository:

```
git clone https://github.com/the-outcaster/kzi-cartridge-generator.git
cd kzi-cartridge-generator
```

2. Install required Python packages using pip:

`pip install Pillow certifi`

*(Note: On some Linux distributions, you may need to use `pip3` and/or install system packages like `python3-pil` and `python3-certifi` using your package manager).*

3. Run the application from your terminal:

`python main.py`

4. When you're ready to build the AppImage, run `./build.sh`. The AppImage will be placed in `~/Applications`.

## Credits
This project was created by [Linux Gaming Central](https://linuxgamingcentral.org).

Learn more about the Kazeta project at [kazeta.org](https://kazeta.org).
