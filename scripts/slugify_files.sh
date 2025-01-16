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

# Function to slugify a file name
slugify() {
  local filename="$1"
  # Replace spaces with underscores, convert to lowercase, and remove special characters
  echo "$filename" |\
    tr '[:upper:]' '[:lower:]' | \
    sed -E 's/[^a-z0-9._-]+/_/g' | \
    sed -E 's/_+/_/g' | \
    sed -E 's/^_|_$//g'
}

# Iterate over all files in the directory
for file in "$DIRECTORY"/*; do
  # Skip if not a file
  if [ ! -f "$file" ]; then
    continue
  fi

  # Get the base name of the file
  base_name="$(basename "$file")"

  # Generate the slugified name
  slugified_name="$(slugify "$base_name")"

  # If the slugified name is different, rename the file
  if [ "$base_name" != "$slugified_name" ]; then
    mv "$file" "$DIRECTORY/$slugified_name"
    echo "Renamed: $base_name -> $slugified_name"
  fi

done

echo "Slugification complete."