#!/bin/sh
# Rebuild both archives from music-composer/ so they stay identical apart from the README.
set -e
cd "$(dirname "$0")"
rm -f music-composer.skill music-composer-skill.zip
zip -qrX music-composer.skill music-composer -x '*/__pycache__/*' '*.pyc' '*/.DS_Store'
zip -qrX music-composer-skill.zip README.md music-composer -x '*/__pycache__/*' '*.pyc' '*/.DS_Store'
echo "built music-composer.skill and music-composer-skill.zip"
