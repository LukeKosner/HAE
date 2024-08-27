import os
import json
from pathlib import Path

# Define the directory and output JSON file
directory = f"{Path(__file__).parent}/optimized_sources"
output_file = "output.json"

# Initialize an empty dictionary to store the words and URLs
word_url_dict = {}

# Define the base URL for aviaryplatform
base_url = "https://aviaryplatform.com/"

# Iterate through each file in the directory
for filename in os.listdir(directory):
    # Get the full file path
    file_path = os.path.join(directory, filename)

    # Check if the path is a file (and not a directory)
    if os.path.isfile(file_path):
        # Open and read the file
        with open(file_path, "r") as file:
            # Read the content of the file
            content = file.read()
            # Split the content into words
            words = content.split()

            # Check if there are at least 5 words in the file
            if len(words) >= 5:
                # Get the fifth word
                fifth_word = words[4]  # Index 4 is the fifth word

                # Construct the URL (assuming the URL ends with the filename)
                url = os.path.join(base_url, filename)

                # Add the word and URL to the dictionary
                word_url_dict[fifth_word] = url

# Write the dictionary to a JSON file
with open(output_file, "w") as json_file:
    json.dump(word_url_dict, json_file, indent=4)

print(f"Output written to {output_file}")
