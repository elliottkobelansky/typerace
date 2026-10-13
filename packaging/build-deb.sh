#!/bin/sh
# Build dist/typerace_VERSION_all.deb: the program as a single zipapp in
# /usr/bin, needing only python3.
#
#   sh packaging/build-deb.sh
set -eu
cd "$(dirname "$0")/.."
VERSION=$(sed -n 's/^__version__ = "\(.*\)"/\1/p' src/typerace/__init__.py)
BUILD=$(mktemp -d)
trap 'rm -rf "$BUILD"' EXIT
PKG="$BUILD/typerace_${VERSION}_all"

mkdir -p "$BUILD/app" "$PKG/DEBIAN" "$PKG/usr/bin" "$PKG/usr/share/applications" "$PKG/usr/share/doc/typerace"
cp -r src/typerace "$BUILD/app/"
find "$BUILD/app" -name __pycache__ -prune -exec rm -rf {} +
python3 -m zipapp "$BUILD/app" -m "typerace.app:cli" -p "/usr/bin/env python3" -c -o "$PKG/usr/bin/typerace"
chmod 755 "$PKG/usr/bin/typerace"
cp packaging/typerace.desktop "$PKG/usr/share/applications/"
cp README.md "$PKG/usr/share/doc/typerace/"
{
    echo "Format: https://www.debian.org/doc/packaging-manuals/copyright-format/1.0/"
    echo "Upstream-Name: typerace"
    echo "Source: https://github.com/elliottkobelansky/typerace"
    echo
    echo "Files: *"
    echo "Copyright: Elliott Kobelansky"
    echo "License: GPL-3+"
    echo
    echo "Files: quotes.json"
    echo "Copyright: Monkeytype contributors; each quote belongs to its original source"
    echo "License: GPL-3"
    echo
    echo "License: GPL-3+"
    echo " On Debian systems, the full text is in /usr/share/common-licenses/GPL-3."
} > "$PKG/usr/share/doc/typerace/copyright"
cat > "$PKG/DEBIAN/control" <<CONTROL
Package: typerace
Version: $VERSION
Architecture: all
Depends: python3 (>= 3.9)
Section: games
Priority: optional
Maintainer: Elliott Kobelansky <elliottkobelansky@gmail.com>
Homepage: https://github.com/elliottkobelansky/typerace
Description: TypeRacer-style typing races in the terminal
 Type quotes from movies, TV, books, speeches and songs word by word, with
 live WPM, a speed chart, and speedcubing-style averages (ao5 to ao100).
CONTROL

chmod -R u=rwX,go=rX "$PKG"
mkdir -p dist
dpkg-deb --build --root-owner-group "$PKG" "dist/typerace_${VERSION}_all.deb"
