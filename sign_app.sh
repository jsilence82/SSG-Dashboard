#!/bin/bash
# Re-sign the SSG Ticket Dashboard.app after edits.
# Run this whenever you modify the launcher script inside the .app bundle.
APP="$(cd "$(dirname "$0")" && pwd)/SSG Ticket Dashboard.app"

xattr -d com.apple.FinderInfo "$APP" 2>/dev/null
xattr -d "com.apple.fileprovider.fpfs#P" "$APP" 2>/dev/null
rm -rf "$APP/Contents/_CodeSignature"
codesign -s - --force --deep "$APP" && echo "Signed OK: $APP"
