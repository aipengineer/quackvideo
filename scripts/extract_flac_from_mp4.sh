#!/bin/bash

# Check if the directory path is provided
if [ -z "$1" ]; then
  echo "Usage: $0 <directory_path>"
  exit 1
fi

# Get the directory path from the first argument
DIRECTORY="$1"

# Check if the provided path is a valid directory
if [ ! -d "$DIRECTORY" ]; then
  echo "Error: $DIRECTORY is not a valid directory."
  exit 1
fi

# Iterate over all .mp4 files in the directory
for file in "$DIRECTORY"/*.mp4; do
  # Skip if no .mp4 files are found
  if [ ! -e "$file" ]; then
    echo "No .mp4 files found in $DIRECTORY."
    exit 0
  fi

  # Get the base name without extension
  base_name="${file%.*}"

  # Run ffmpeg command to extract audio
  ffmpeg -i "$file" -vn -acodec flac "${base_name}.flac"

  echo "Processed: $file -> ${base_name}.flac"
done

echo "Audio extraction complete."
