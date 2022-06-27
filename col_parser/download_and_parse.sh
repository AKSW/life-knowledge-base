#!/bin/bash
mkdir -p data
mkdir -p cache

# Download CoL (if not already in cache)
wget --no-clobber -O "cache/col.zip" http://api.checklistbank.org/dataset/9820/export.zip?format=DwCA

# Parse CoL to nt
python3 parse.py "cache/col.zip" $1 > "data/parsed.nt"
