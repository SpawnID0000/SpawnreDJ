# M3U_from_folder.py

import logging
import os  # Ensure os is imported
from mutagen import File
from pathlib import Path
import traceback  # For detailed tracebacks

# Initialize module-specific logger
logger = logging.getLogger(__name__)


def sanitize_path(path) -> Path:
    """
    Sanitize the input path by removing backslashes before spaces and normalizing the path.

    Args:
        path (str or Path): The original path input by the user.

    Returns:
        Path: The sanitized Path object.
    """
    try:
        # Convert Path object to string if necessary
        path_str = str(path)
        logger.debug(f"Original path: {path_str}")

        # Replace escaped spaces (\ ) with regular spaces
        sanitized = path_str.replace('\\ ', ' ')
        logger.debug(f"After replacing '\\ ': {sanitized}")

        # Additionally, handle other common escape characters if necessary
        # For example, replace double backslashes with single backslash
        sanitized = sanitized.replace('\\\\', '\\')
        logger.debug(f"After replacing '\\\\': {sanitized}")

        # Create a Path object and normalize it
        sanitized_path = Path(sanitized).expanduser().resolve()
        logger.debug(f"Resolved path: {sanitized_path}")

        return sanitized_path
    except Exception as e:
        logger.error(f"Exception in sanitize_path: {e}")
        logger.debug(traceback.format_exc())
        raise  # Re-raise the exception to be handled by the caller


def get_track_info(file_path: Path):
    """Extract track metadata including album, disc number, and track number."""
    try:
        # logger.debug(f"Processing file: {file_path}")
        audio = File(str(file_path), easy=True)
        if audio is None:
            logger.warning(f"Unsupported audio format or corrupted file: {file_path}")
            return None

        duration = int(audio.info.length)  # Duration in seconds
        title = audio.get('title', ['Unknown Title'])[0]
        artist = audio.get('artist', ['Unknown Artist'])[0]
        album = audio.get('album', ['Unknown Album'])[0]
        track_number = audio.get('tracknumber', [0])[0]
        disc_number = audio.get('discnumber', [0])[0]

        # Handle different types for track numbers and disc numbers
        track_number = parse_number(track_number)
        disc_number = parse_number(disc_number)

        # logger.debug(f"Track Info - Title: {title}, Artist: {artist}, Album: {album}, Disc: {disc_number}, Track: {track_number}, Duration: {duration}")
        return duration, title, artist, album, disc_number, track_number
    except Exception as e:
        logger.error(f"Error processing {file_path}: {e}")
        logger.debug(traceback.format_exc())
        return None


def parse_number(number):
    """Parse a number which could be in a string format like '1/10'."""
    try:
        if isinstance(number, str):
            return int(number.split('/')[0])
        elif isinstance(number, int):
            return number
        else:
            return 0
    except ValueError:
        logger.warning(f"Unable to parse number: {number}")
        return 0


def normalize_artist_name(artist_name: str) -> str:
    """Normalize the artist name by removing 'The ' prefix if present."""
    if artist_name.lower().startswith('the '):
        normalized = artist_name[4:]
        # logger.debug(f"Normalized artist name from '{artist_name}' to '{normalized}'")
        return normalized
    return artist_name


def generate_m3u(music_dir, m3u_file_path, flip_order: bool = False, path_prefix: str = '../') -> bool:
    """
    Generate an M3U playlist from the specified music directory.

    Args:
        music_dir (str or Path): Path to the music directory.
        m3u_file_path (str or Path): Path where the M3U file will be saved (including filename).
        flip_order (bool): Whether to flip the artist and track in EXTINF lines.
        path_prefix (str): Prefix to add to each path in the playlist (default: '../').

    Returns:
        bool: True if the playlist was successfully generated, False otherwise.
    """
    entries = []
    try:
        logger.debug("Sanitizing music directory path.")
        music_dir = sanitize_path(music_dir)
        logger.debug("Sanitizing M3U file path.")
        m3u_file_path = sanitize_path(m3u_file_path)
    except Exception as e:
        logger.error(f"Error sanitizing paths: {e}")
        return False

    print(f"Generating M3U playlist from directory: {music_dir}")
    print(f"Playlist will be saved to: {m3u_file_path}")

    # Ensure the music directory exists
    if not music_dir.is_dir():
        print(f"Error: The directory '{music_dir}' does not exist or is not a directory.")
        logger.error(f"The directory '{music_dir}' does not exist or is not a directory.")
        return False

    try:
        for root, _, files in os.walk(music_dir):
            root_path = Path(root)
            for file in files:
                if file.lower().endswith(('.opus', '.m4a', '.mp3', '.flac')):
                    file_path = (root_path / file).resolve()
                    track_info = get_track_info(file_path)
                    if track_info:
                        duration, title, artist, album, disc_number, track_number = track_info
                        try:
                            relative_path = file_path.relative_to(m3u_file_path.parent)
                            relative_path = Path(path_prefix) / relative_path
                        except ValueError:
                            # If file is not under m3u_file_path.parent, use absolute path
                            relative_path = file_path
                        relative_path_str = relative_path.as_posix()
                        entries.append((artist, album, disc_number, track_number, title, duration, relative_path_str))
    except Exception as e:
        logger.error(f"Error during directory traversal: {e}")
        logger.debug(traceback.format_exc())
        return False

    print(f"Number of tracks found: {len(entries)}")
    logger.debug(f"Number of tracks found: {len(entries)}")

    if not entries:
        print("No audio files found in the specified directory.")
        logger.warning("No audio files found in the specified directory.")
        return False

    # Sorting by normalized artist name, album, disc number, and then track number
    try:
        entries.sort(key=lambda x: (
            normalize_artist_name(x[0]).lower(),
            x[1].lower(),
            x[2],
            x[3]
        ))
        logger.debug("Sorted playlist entries.")
    except Exception as e:
        logger.error(f"Error sorting entries: {e}")
        logger.debug(traceback.format_exc())
        return False

    try:
        # Ensure the parent directory exists
        m3u_file_path.parent.mkdir(parents=True, exist_ok=True)
        logger.debug(f"Ensured that the directory '{m3u_file_path.parent}' exists.")

        with m3u_file_path.open('w', encoding='utf-8') as m3u_file:
            m3u_file.write("#EXTM3U\n")
            for entry in entries:
                if flip_order:
                    extinf_line = f"#EXTINF:{entry[5]},{entry[0]} - {entry[4]}\n"
                else:
                    extinf_line = f"#EXTINF:{entry[5]},{entry[4]} - {entry[0]}\n"
                m3u_file.write(extinf_line)
                m3u_file.write(f"{entry[6]}\n")
        logger.debug(f"M3U playlist written to {m3u_file_path}")
    except Exception as e:
        print(f"Error writing M3U file: {e}")
        logger.error(f"Error writing M3U file: {e}")
        logger.debug(traceback.format_exc())
        return False

    print("M3U playlist generation complete.")
    logger.info("M3U playlist generation complete.")
    return True


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Create an M3U playlist from a folder of audio files.")
    parser.add_argument("music_dir", help="Path to the music directory")
    parser.add_argument("m3u_file_path", help="Path where the M3U file will be saved (including filename)")
    parser.add_argument("-flip", action="store_true", help="Flip the order of artist and track in the EXTINF line (default is Track - Artist)")
    parser.add_argument("-prefix", default="../", help="Prefix to add to each path in the playlist (default: '../')")

    args = parser.parse_args()

    # Sanitize input paths
    try:
        sanitized_music_dir = sanitize_path(args.music_dir)
        sanitized_m3u_file_path = sanitize_path(args.m3u_file_path)
    except Exception as e:
        logger.error(f"Error sanitizing input paths: {e}")
        exit(1)

    success = generate_m3u(sanitized_music_dir, sanitized_m3u_file_path, flip_order=args.flip, path_prefix=args.prefix)
    if success:
        print(f"Playlist generated at {sanitized_m3u_file_path}")
    else:
        print("Failed to generate playlist.")
