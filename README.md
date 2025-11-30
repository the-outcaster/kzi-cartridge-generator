# Kazeta Cartridge Generator
Swiss army knife utility for [Kazeta](https://kazeta.org)/[Kazeta+](https://github.com/the-outcaster/kazeta-plus) that allows you to do the following:
- create, edit, and test Kazeta information (`.kzi`) files
- Kazeta runtime (`.kzr`) creator -- create Windows runtime files, Linux runtime files, or emulator runtimes
- Kazeta package (`.kzp`) creator -- compress your games to save space and simplify the way your games are transferred (Kazeta+ only)
- mount and unmount `.kzr` and `.kzp` files with `erofsfuse`
- create ISOs for your cartridges, and burn them onto CDs/DVDs (Kazeta+ only)
- create and burn audio CDs (Kazeta+ only)
- create and edit themes for the BIOS (Kazeta+ only)

## Screenshots
<details>
<summary><b>Click to expand Screenshot Gallery</b></summary>

| Main Window | Sonic Adventure 2 Example |
| :---: | :---: |
| <img src="https://github.com/user-attachments/assets/40e08e97-ef53-416c-bc1b-3002714e718a" width="400" /> | <img src="https://github.com/user-attachments/assets/7d7bbe8b-ec4f-4c84-8f83-bad1c535a9bd" width="400" /> |

| Runtime/Package Manager | Runtime/Package Mounting |
| :---: | :---: |
| <img src="https://github.com/user-attachments/assets/4f2c5a83-bb46-47bc-969b-4ba782991080" width="400" /> | <img src="https://github.com/user-attachments/assets/09ca5cad-2a0d-4076-91f9-72c4b8121cc5" width="400" /> |

| ISO Creator | Audio CD Creator |
| :---: | :---: |
| <img src="https://github.com/user-attachments/assets/4638f20e-3ddf-4cee-909c-39e22151aeac" width="400" /> | <img src="https://github.com/user-attachments/assets/0b877b73-d824-4510-9d7b-0f2b8488a7fb" width="400" /> |

| Theme Creator | About Window |
| :---: | :---: |
| <img src="https://github.com/user-attachments/assets/8b4a9775-d79c-436f-b28f-b0fb05d31dbd" width="400" /> | <img src="https://github.com/user-attachments/assets/bec18525-638b-4f08-b77c-b474c4490c19" width="400" /> |
</details>

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
Simply head over to the [Releases](https://github.com/the-outcaster/kzi-cartridge-generator/releases) page, download the latest AppImage, and execute it. Note that you may have to mark it as executable in order to run it.

*NOTE: fetching icons from SteamGridDB requires you to log in to the website with your Steam account, and supplying your [API key](https://www.steamgriddb.com/profile/preferences/api) when the application asks you for it.*

## Development Requirements
Python libraries needed: 
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

`pip install pillow certifi toml pydub`

Run the application from your terminal:

`python main.py`

When you're ready to build the AppImage, run `./build.sh`. The AppImage will be placed in `~/Applications`.

## Credits
This project was created by [Linux Gaming Central](https://linuxgamingcentral.org).

Learn more about the Kazeta project at [kazeta.org](https://kazeta.org).
