#!/bin/bash

# Check if the base directory is provided
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

# Enable nullglob so that non-matching patterns expand to nothing
shopt -s nullglob

files_found=0
# Iterate over all .mp4 or .MP4 files in the video directory
for input_file in "$VIDEO_DIR"/*.[mM][pP]4; do
  files_found=1
  # Extract the base name without the extension
  filename=$(basename "$input_file")
  base="${filename%.*}"

  # The Python script is expected to create its own "frames" folder inside the output parent,
  # resulting in the final output path: <BASE_DIR>/edited/frames/<video_base>
  output_directory="$OUTPUT_PARENT"

  # Execute the Python script with the input and output paths
  python "$PYTHON_SCRIPT" extract "$input_file" "$output_directory" --fps "1/5"

  echo "Processed: $input_file -> (output in ${output_directory}/frames/$base)"
done

# If no files were processed, output a message and exit
if [ $files_found -eq 0 ]; then
  echo "No .mp4 or .MP4 files found in $VIDEO_DIR."
  exit 0
fi

echo "Frame extraction complete."
