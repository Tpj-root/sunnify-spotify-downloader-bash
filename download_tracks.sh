#!/bin/bash

# --- Conda environment activation ---
# Adjust the environment name if needed
CONDA_ENV="base"  # replace with your env name if not "base"
source "$HOME/miniconda3/bin/activate" "$CONDA_ENV"

# --- Track IDs file ---
track_file="track_ids.txt"
base_url="https://open.spotify.com/track"

# Check if file exists
if [ ! -f "$track_file" ]; then
    echo "❌ Track ID file not found: $track_file"
    exit 1
fi

# Loop through each track ID in the file
while IFS= read -r track_id || [ -n "$track_id" ]; do
    # Skip empty lines
    [ -z "$track_id" ] && continue

    full_url="$base_url/$track_id"
    echo "Downloading track: $track_id"

    # Run the Python downloader using conda env
    python Spotify_Downloader.py "$full_url"
    exit_code=$?

    if [ $exit_code -eq 0 ]; then
        echo "✅ Download successful for $track_id"
    else
        echo "❌ Download failed for $track_id (exit code $exit_code)"
    fi
done < "$track_file"
