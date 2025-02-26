#!/bin/bash

# Check if the base directory is provided
if [ -z "$1" ]; then
  echo "Usage: $0 <directory_path>"
  exit 1
fi

# Get the base directory from the first argument
BASE_DIR="$1"

# Verify that the provided path is a valid directory
if [ ! -d "$BASE_DIR" ]; then
  echo "Error: $BASE_DIR is not a valid directory."
  exit 1
fi

# Function to slugify a file name
slugify() {
  local filename="$1"
  # Replace spaces with underscores, convert to lowercase, and remove special characters
  echo "$filename" | \
    tr '[:upper:]' '[:lower:]' | \
    sed -E 's/[^a-z0-9._-]+/_/g' | \
    sed -E 's/_+/_/g' | \
    sed -E 's/^_|_$//g'
}

# Recursively find all files in BASE_DIR and process them
find "$BASE_DIR" -type f -print0 | while IFS= read -r -d '' file; do
  # Get the base name of the file
  base_name="$(basename "$file")"
  
  # Generate the slugified name
  slugified_name="$(slugify "$base_name")"
  
  # If the slugified name differs from the original, rename the file
  if [ "$base_name" != "$slugified_name" ]; then
    file_dir="$(dirname "$file")"
    new_path="$file_dir/$slugified_name"
    
    # Check if a file with the new name already exists to avoid overwriting
    if [ -e "$new_path" ]; then
      echo "Skipping: $file (target $new_path already exists)"
    else
      mv "$file" "$new_path"
      echo "Renamed: $file -> $new_path"
    fi
  fi
done

echo "Slugification complete."
