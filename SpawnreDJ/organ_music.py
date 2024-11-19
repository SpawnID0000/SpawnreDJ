# organ_music.py

import os
import re
import logging
from mutagen import File
from typing import Optional

# Initialize module-specific logger
logger = logging.getLogger(__name__)

# Define a mapping of placeholders to specific metadata keys
PLACEHOLDER_MAPPING = {
    "D": "disc",
    "TR": "track",
}

# Define a mapping of tag names to their actual metadata keys in files
TAG_MAPPING = {
    "disc": ["disk"],
    "track": ["trkn"],
    "title": ["©nam"],
    "MB_trackID": ["----:com.apple.iTunes:MusicBrainz Track Id"],
    "album": ["©alb"],
    "MB_albumID": ["----:com.apple.iTunes:MusicBrainz Release Group Id"],
    "artist": ["©ART", "aART"],
    "MB_artistID": ["----:com.apple.iTunes:MusicBrainz Artist Id"],
    "AcoustID": ["----:com.apple.iTunes:Acoustid Id"],
    "year": ["----:com.apple.iTunes:originalyear", "----:com.apple.iTunes:ORIGINALYEAR"],
}

def get_tag(file_path: str, tag_name: str) -> Optional[str]:
    """Extract the specified tag from the audio file."""
    try:
        audio = File(file_path)
        if audio:
            possible_tags = TAG_MAPPING.get(tag_name, [tag_name])
            for tag in possible_tags:
                if tag in audio:
                    value = audio[tag][0]
                    # Decode bytes to string if necessary
                    if isinstance(value, bytes):
                        value = value.decode('utf-8')
                    # Handle tuple values (e.g., track/disc numbers)
                    if isinstance(value, tuple):
                        return str(value[0])  # Extract the first part (e.g., 1/1 -> 1)
                    return str(value)
        return None
    except Exception as e:
        logger.error(f"Error reading tag '{tag_name}' from file {file_path}: {e}")
    return None

def format_string_with_placeholders(format_string: str, file_path: str) -> str:
    """
    Replace placeholders enclosed in {} with their corresponding tag values.
    """
    # Find all placeholders in the format string enclosed in {}
    # e.g., {D}, {TR}, {MB_trackID}
    pattern = re.compile(r"\{([^}]+)\}")
    placeholders = pattern.findall(format_string)

    tags = {}

    for ph in placeholders:
        tag_key = PLACEHOLDER_MAPPING.get(ph)
        if not tag_key:
            # If placeholder not in mapping, assume it's a custom tag with exact name
            tag_key = ph
        tag_value = get_tag(file_path, tag_key)
        if tag_value:
            # Adjust disc and track numbers
            if ph == "D":
                try:
                    tag_value = str(int(tag_value))  # Remove leading zeros
                except ValueError:
                    tag_value = tag_value  # Keep as is if not an integer
            elif ph == "TR":
                try:
                    track_num = int(tag_value)
                    tag_value = str(track_num).zfill(2)  # Ensure track has at least 2 digits
                except ValueError:
                    tag_value = "00"  # Default if invalid
            tags[ph] = tag_value
        else:
            logger.warning(f"Tag for placeholder '{ph}' not found for file {file_path}. Using 'Unknown'.")
            tags[ph] = "Unknown"

    # Replace all placeholders with their corresponding tag values
    new_string = format_string
    for ph, val in tags.items():
        new_string = new_string.replace(f"{{{ph}}}", val)

    return new_string

def get_unique_filename(directory: str, filename: str, extension: str) -> str:
    """
    Generate a unique filename by appending a suffix if the filename already exists.

    Args:
        directory (str): The directory where the file will be placed.
        filename (str): The desired filename without extension.
        extension (str): The file extension (e.g., '.m4a').

    Returns:
        str: A unique filename with extension.
    """
    base_filename = filename
    counter = 1
    unique_filename = f"{base_filename}{extension}"

    while os.path.exists(os.path.join(directory, unique_filename)):
        unique_filename = f"{base_filename}_{counter}{extension}"
        counter += 1

    return unique_filename

def remove_empty_dirs(root_dir: str):
    """Recursively remove empty directories."""
    for dirpath, dirnames, filenames in os.walk(root_dir, topdown=False):
        # Delete directory if it's empty
        if not dirnames and not filenames:
            try:
                os.rmdir(dirpath)
                logger.info(f"Deleted empty folder: {dirpath}")
            except Exception as e:
                logger.error(f"Error deleting folder {dirpath}: {e}")

def organize_music(
    input_dir: str,
    filename_format: str = "{title}",
    album_folder_format: Optional[str] = None,
    artist_folder_format: Optional[str] = None
):
    """Organize music files based on the specified tags and format strings."""
    for root, _, files in os.walk(input_dir):
        for file in files:
            file_path = os.path.join(root, file)
            ext = os.path.splitext(file)[-1].lower()

            # Only process supported audio formats
            if ext not in [".m4a", ".mp3", ".flac", ".opus"]:
                continue

            # Generate formatted filename
            new_filename = format_string_with_placeholders(filename_format, file_path)
            if not new_filename:
                continue
            # Ensure the extension starts with a dot
            if not ext.startswith('.'):
                ext = f".{ext}"
            new_filename_with_ext = new_filename + ext

            # Generate formatted artist folder name
            if artist_folder_format:
                artist_folder = format_string_with_placeholders(artist_folder_format, file_path)
            else:
                artist_folder = None

            # Generate formatted album folder name
            if album_folder_format:
                album_folder = format_string_with_placeholders(album_folder_format, file_path)
            else:
                album_folder = None

            # Extract folder tags for validation
            artist = artist_folder if artist_folder else None
            album = album_folder if album_folder else None

            # Handle missing tags
            if artist_folder_format and not artist:
                logger.warning(f"Missing artist tag for file {file_path}. Placing in root folder.")
            if album_folder_format and not album:
                logger.warning(f"Missing album tag for file {file_path}. Placing in artist folder or root folder.")

            # Generate new paths
            base_dir = os.path.abspath(input_dir)
            artist_dir = os.path.join(base_dir, artist) if artist else base_dir
            album_dir = os.path.join(artist_dir, album) if album else artist_dir

            # Ensure the target directories exist
            if artist_folder_format and not os.path.exists(artist_dir):
                os.makedirs(artist_dir)
                logger.info(f"Created artist directory: {artist_dir}")
            if album_folder_format and not os.path.exists(album_dir):
                os.makedirs(album_dir)
                logger.info(f"Created album directory: {album_dir}")

            # Determine the final new file path
            target_directory = album_dir
            final_new_filename = new_filename_with_ext

            # Check for filename collisions and generate a unique filename if necessary
            if os.path.exists(os.path.join(target_directory, final_new_filename)):
                final_new_filename = get_unique_filename(target_directory, new_filename, ext)
                logger.info(f"Filename collision detected. Renaming to {final_new_filename}")

            new_file_path = os.path.join(target_directory, final_new_filename)

            # Move or rename the file
            if file_path != new_file_path:
                try:
                    os.rename(file_path, new_file_path)
                    logger.info(f"Moved: {file_path} -> {new_file_path}")
                except Exception as e:
                    logger.error(f"Error moving file {file_path} to {new_file_path}: {e}")
            else:
                logger.info(f"File already in the correct location: {file_path}")

    # Remove empty folders
    remove_empty_dirs(input_dir)
