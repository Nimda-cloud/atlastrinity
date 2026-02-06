#!/bin/bash

# Define paths
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
DMG_PATH="$SCRIPT_DIR/output.dmg"
LOG_FILE="$SCRIPT_DIR/signing_notarization.log"

# Signing the DMG
codesign --sign "Developer ID Application: Your Name (TEAMID)" --timestamp --options runtime "$DMG_PATH" &>> "$LOG_FILE"

# Notarizing the DMG
xcrun altool --notarize-app --primary-bundle-id "com.example.app" --username "apple_id@example.com" --password "app-specific-password" --file "$DMG_PATH" &>> "$LOG_FILE"

# Validate the signature
echo "
Validating signature..." &>> "$LOG_FILE"
codesign -dv --verbose=4 "$DMG_PATH" &>> "$LOG_FILE"

# Verify Gatekeeper trust
echo "
Verifying Gatekeeper trust..." &>> "$LOG_FILE"
spctl --assess --type open --context context:primary-signature "$DMG_PATH" &>> "$LOG_FILE"

# Completion message
echo "
Signing, notarization, and validation completed. Logs saved to $LOG_FILE"
