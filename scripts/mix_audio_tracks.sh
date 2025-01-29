#!/bin/bash

# Check if the directory path is provided
if [ -z "$1" ]; then
  echo "Usage: $0 <directory_path>"
  exit 1
fi

# Get the directory path from the first argument
INPUT_DIRECTORY="$1"

# Check if the provided path is a valid directory
if [ ! -d "$INPUT_DIRECTORY" ]; then
  echo "Error: $INPUT_DIRECTORY is not a valid directory."
  exit 1
fi

# Iterate over all .flac files in the input directory
for input1 in "$INPUT_DIRECTORY"/*.flac; do
  # Skip if no .flac files are found
  if [ ! -e "$input1" ]; then
    echo "No .flac files found in $INPUT_DIRECTORY."
    exit 0
  fi

  # Deduce the corresponding .wav file path
  input2=$(echo "$input1" | sed 's|/raw/audio/|/edited/|' | sed 's|\.flac$|-enhanced-v2-90p.wav|')

  # Check if the corresponding .wav file exists
  if [ ! -f "$input2" ]; then
    echo "Warning: Corresponding .wav file not found for $input1. Skipping..."
    continue
  fi

  # Deduce the output file path in the /edited directory
  output=$(echo "$input1" | sed 's|/raw/audio/|/edited/|' | sed 's|\.flac$|-mixed.flac|')

  # Ensure the output directory exists
  output_dir=$(dirname "$output")
  mkdir -p "$output_dir"

  # Run the ffmpeg command to mix the audio tracks
  ffmpeg -i "$input1" -i "$input2" -filter_complex "[0:a]volume=0.20[a1];[1:a]volume=0.80[a2];[a1][a2]amix=inputs=2:duration=longest" -c:a flac "$output"

  if [ $? -eq 0 ]; then
    echo "Mixed: $input1 + $input2 -> $output"

    # Delete the .wav file after successful processing
    rm -f "$input2"
    echo "Deleted: $input2"
  else
    echo "Error: Failed to mix $input1 and $input2."
  fi
done

echo "Audio mixing complete."
