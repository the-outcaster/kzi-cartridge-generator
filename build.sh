#!/bin/bash
clear

APPLICATION_DIR="$HOME/Applications"
VERSION="2.0"

mkdir -p $APPLICATION_DIR
mkdir -p $APPLICATION_DIR/KziCartridgeGenerator.AppDir

echo -e "\nCreating standalone executable..."

pyinstaller --onefile --windowed *.py --distpath $APPLICATION_DIR/KziCartridgeGenerator.AppDir --workpath /tmp/ --specpath /tmp/ --name kzi-cartridge-generator

cd $APPLICATION_DIR/KziCartridgeGenerator.AppDir

if [ ! -f logo.svg ]; then
    echo -e "\nFetching Kazeta logo..."
    wget https://kazeta.org/images/logo.svg
fi

if [ ! -f kzi-cartridge-generator.desktop ]; then
    echo -e "\nCreating .desktop file..."
    touch kzi-cartridge-generator.desktop

    echo -e "\nAppending contents to .desktop file..."
    grep -qxF "[Desktop Entry]" kzi-cartridge-generator.desktop || echo -e "[Desktop Entry]" >> kzi-cartridge-generator.desktop
    grep -qxF "Name=KZI Cartridge Generator" kzi-cartridge-generator.desktop || echo -e "Name=KZI Cartridge Generator" >> kzi-cartridge-generator.desktop
    grep -qxF "Exec=kzi-cartridge-generator" kzi-cartridge-generator.desktop || echo -e "Exec=kzi-cartridge-generator" >> kzi-cartridge-generator.desktop
    grep -qxF "Icon=logo" kzi-cartridge-generator.desktop || echo -e "Icon=logo" >> kzi-cartridge-generator.desktop
    grep -qxF "Type=Application" kzi-cartridge-generator.desktop || echo -e "Type=Application" >> kzi-cartridge-generator.desktop
    grep -qxF "Categories=Utility;" kzi-cartridge-generator.desktop || echo -e "Categories=Utility;" >> kzi-cartridge-generator.desktop
fi

if [ ! -f AppRun ]; then
    echo -e "\nCreating AppRun file and appending contents..."
    touch AppRun
    grep -qxF "#!/bin/sh" AppRun || echo -e "#!/bin/sh" >> AppRun
    grep -qxF 'cd "$(dirname "$0")"' AppRun || echo -e 'cd "$(dirname "$0")"' >> AppRun
    grep -qxF "./kzi-cartridge-generator" AppRun || echo -e "./kzi-cartridge-generator" >> AppRun

    echo -e "\nMaking AppRun executable..."
    chmod +x AppRun
fi

cd $APPLICATION_DIR/

if [ ! -f appimagetool-x86_64.AppImage ]; then
    echo -e "\nDownloading appimagetool..."
    wget https://github.com/AppImage/AppImageKit/releases/download/continuous/appimagetool-x86_64.AppImage

    echo -e "\nMaking appimagetool executable..."
    chmod +x appimagetool-x86_64.AppImage
fi

echo -e "\nMaking AppImage for KZI Cartridge Generator..."
OUTPUT_NAME="KZI-Cartridge-Generator-${VERSION}-x86_64.AppImage"
./appimagetool-x86_64.AppImage KziCartridgeGenerator.AppDir "$OUTPUT_NAME"

echo -e "\nDone! AppImage has been stored in $APPLICATION_DIR/$OUTPUT_NAME"

