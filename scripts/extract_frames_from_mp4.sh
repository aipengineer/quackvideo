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

# Python script path
PYTHON_SCRIPT="examples/frame_extraction.py"

# Check if the Python script exists
if [ ! -f "$PYTHON_SCRIPT" ]; then
  echo "Error: Python script $PYTHON_SCRIPT not found."
  exit 1
fi

# Iterate over all .mp4 files in the input directory
for input_file in "$INPUT_DIRECTORY"/*.mp4; do
  # Skip if no .mp4 files are found
  if [ ! -e "$input_file" ]; then
    echo "No .mp4 files found in $INPUT_DIRECTORY."
    exit 0
  fi

  # Deduce the output directory by replacing /raw/video/ with /edited/
  output_directory=$(echo "$input_file" | sed 's|/raw/video/|/edited/|')
  output_directory=$(dirname "$output_directory")

  # Ensure the output directory exists
  mkdir -p "$output_directory"

  # Execute the Python script with the input and output paths
  python "$PYTHON_SCRIPT" extract "$input_file" "$output_directory" --fps "1/5"

  echo "Processed: $input_file -> $output_directory"
done

echo "Frame extraction complete."
