#!/bin/bash

# Check if the base directory is provided
if [ -z "$1" ]; then
  echo "Usage: $0 <base_directory>"
  exit 1
fi

# Set the base directory and define the subdirectories
BASE_DIR="$1"
FLAC_DIR="$BASE_DIR/raw/audio"
WAV_DIR="$BASE_DIR/edited"

# Verify that the expected subdirectories exist
if [ ! -d "$FLAC_DIR" ]; then
  echo "Error: $FLAC_DIR is not a valid directory."
  exit 1
fi

if [ ! -d "$WAV_DIR" ]; then
  echo "Error: $WAV_DIR is not a valid directory."
  exit 1
fi

# Iterate over all .flac files in the FLAC directory
for input1 in "$FLAC_DIR"/*.flac; do
  # If no .flac files are found, exit gracefully
  if [ ! -e "$input1" ]; then
    echo "No .flac files found in $FLAC_DIR."
    exit 0
  fi

  # Extract the base filename (without the .flac extension) and trim trailing whitespace
  base=$(basename "$input1" .flac | sed 's/[[:space:]]*$//')

  # Debug: show what base name is being used
  echo "Processing file: $input1"
  echo "Base name: '$base'"

  # Build the pattern for the corresponding .wav file in the WAV directory
  pattern="${base}*.wav"
  echo "Searching for .wav file with pattern: '$pattern' in directory: $WAV_DIR"

  input2=$(find "$WAV_DIR" -maxdepth 1 -type f -name "$pattern" | sort | head -n 1)

  # If the corresponding .wav file is not found, skip this file
  if [ -z "$input2" ] || [ ! -f "$input2" ]; then
    echo "Warning: Corresponding .wav file not found for $input1. Skipping..."
    continue
  fi

  # Define the output file path in the WAV directory (appending -mixed to the base name)
  output="$WAV_DIR/${base}-mixed.flac"

  # Ensure the output directory exists (should be the case)
  mkdir -p "$WAV_DIR"

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
