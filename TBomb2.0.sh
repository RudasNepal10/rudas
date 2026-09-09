#!/usr/bin/env sh
# Compatibility launcher for the manual SMS sender.
exec python3 "$(dirname "$0")/bomber.py" "$@"
