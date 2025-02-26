#!/bin/bash

# Check if the top-level directory is provided
if [ -z "$1" ]; then
  echo "Usage: $0 <base_directory>"
  exit 1
fi

# Set the base directory
BASE_DIR="$1"

# Define the video directory and the parent directory for frames output
VIDEO_DIR="$BASE_DIR/raw/video"
OUTPUT_PARENT="$BASE_DIR/edited"  # Pass the parent of "frames" to avoid duplication

# Verify that the base directory exists
if [ ! -d "$BASE_DIR" ]; then
  echo "Error: $BASE_DIR is not a valid directory."
  exit 1
fi

# Verify that the video directory exists
if [ ! -d "$VIDEO_DIR" ]; then
  echo "Error: $VIDEO_DIR is not a valid directory."
  exit 1
fi

# Create the output parent directory if it doesn't exist
mkdir -p "$OUTPUT_PARENT"

# Python script path
PYTHON_SCRIPT="examples/frame_extraction.py"

# Check if the Python script exists
if [ ! -f "$PYTHON_SCRIPT" ]; then
  echo "Error: Python script $PYTHON_SCRIPT not found."
  exit 1
fi

# Iterate over all .mp4 files in the video directory
for input_file in "$VIDEO_DIR"/*.mp4; do
  # Skip if no .mp4 files are found
  if [ ! -e "$input_file" ]; then
    echo "No .mp4 files found in $VIDEO_DIR."
    exit 0
  fi

  # Extract the base name without the extension
  base=$(basename "$input_file" .mp4)

  # Pass the parent output directory. The Python script is expected to create its own "frames" folder,
  # resulting in the final output path: <BASE_DIR>/edited/frames/<video_base>
  output_directory="$OUTPUT_PARENT"

  # Execute the Python script with the input and output paths
  python "$PYTHON_SCRIPT" extract "$input_file" "$output_directory" --fps "1/5"

  echo "Processed: $input_file -> (output in ${output_directory}/frames/$base)"
done

echo "Frame extraction complete."
