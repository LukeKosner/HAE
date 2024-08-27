import os
import re
from pathlib import Path

# Define source and destination directories
source_dir = f"{Path(__file__).parent}/sources"
destination_dir = f"{Path(__file__).parent}/optimized_sources"

# Create destination directory if it does not exist
os.makedirs(destination_dir, exist_ok=True)

# Regular expression patterns
timestamp_pattern = re.compile(r"\[\d{2}:\d{2}:\d{2}\]")
multiple_spaces_pattern = re.compile(r"\s+")


# Function to remove the timestamp pattern and reduce multiple spaces
def clean_text(text):
    text = timestamp_pattern.sub("", text)
    text = multiple_spaces_pattern.sub(" ", text)
    return text


# Process each file in the source directory
for filename in os.listdir(source_dir):
    if filename.endswith(".txt"):
        source_file_path = os.path.join(source_dir, filename)
        file_size = os.path.getsize(source_file_path)

        with open(source_file_path, "r", encoding="utf-8") as file:
            content = file.read()

        # Clean the content
        modified_content = clean_text(content)

        # get size of modified content
        modified_file_size = len(modified_content)
        if modified_file_size >= 40960:
            continue

        # Save the modified content to the destination directory
        destination_file_path = os.path.join(destination_dir, filename)
        with open(destination_file_path, "w", encoding="utf-8") as file:
            file.write(modified_content)

print("Processing complete.")
