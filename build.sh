#!/bin/bash
clear

mkdir -p $HOME/Applications/KziCartridgeGenerator.AppDir

echo -e "\nCreating standalone executable..."
sleep 1

pyinstaller --onefile --windowed *.py --distpath $HOME/Applications/KziCartridgeGenerator.AppDir --workpath /tmp/ --specpath /tmp/ --name kzi-cartridge-generator

cd $HOME/Applications/KziCartridgeGenerator.AppDir

echo -e "\nFetching Kazeta logo..."
sleep 1
wget -nc https://kazeta.org/images/logo.svg

echo -e "\nCreating .desktop file..."
sleep 1
touch kzi-cartridge-generator.desktop

echo -e "\nAppending contents to .desktop file..."
sleep 1
grep -qxF "[Desktop Entry]" kzi-cartridge-generator.desktop || echo -e "[Desktop Entry]" >> kzi-cartridge-generator.desktop
grep -qxF "Name=KZI Cartridge Generator" kzi-cartridge-generator.desktop || echo -e "Name=KZI Cartridge Generator" >> kzi-cartridge-generator.desktop
grep -qxF "Exec=kzi-cartridge-generator" kzi-cartridge-generator.desktop || echo -e "Exec=kzi-cartridge-generator" >> kzi-cartridge-generator.desktop
grep -qxF "Icon=logo" kzi-cartridge-generator.desktop || echo -e "Icon=logo" >> kzi-cartridge-generator.desktop
grep -qxF "Type=Application" kzi-cartridge-generator.desktop || echo -e "Type=Application" >> kzi-cartridge-generator.desktop
grep -qxF "Categories=Utility;" kzi-cartridge-generator.desktop || echo -e "Categories=Utility;" >> kzi-cartridge-generator.desktop

echo -e "\nCreating AppRun file..."
sleep 1
touch AppRun
grep -qxF "#!/bin/sh" AppRun || echo -e "#!/bin/sh" >> AppRun
grep -qxF 'cd "$(dirname "$0")"' AppRun || echo -e 'cd "$(dirname "$0")"' >> AppRun
grep -qxF "./kzi-cartridge-generator" AppRun || echo -e "./kzi-cartridge-generator" >> AppRun

echo -e "\nMaking AppRun executable..."
sleep 1
chmod +x AppRun

cd $HOME/Applications/
echo -e "\nFetching appimagetool..."
sleep 1
wget -nc https://github.com/AppImage/AppImageKit/releases/download/continuous/appimagetool-x86_64.AppImage

echo -e "\nMaking appimagetool executable..."
sleep 1
chmod +x appimagetool-x86_64.AppImage

echo -e "\nMaking AppImage for KZI Cartridge Generator..."
sleep 1
./appimagetool-x86_64.AppImage KziCartridgeGenerator.AppDir

echo -e "\nDone!"
sleep 1
