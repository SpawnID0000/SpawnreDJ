# folder_from_M3U.py

import shutil
import logging
from pathlib import Path
from typing import Optional, Tuple

# Initialize module-specific logger
logger = logging.getLogger(__name__)

def convert_size_to_gb(size_in_bytes: int) -> float:
    """Convert size from bytes to gigabytes."""
    return size_in_bytes / (1024 ** 3)

def sanitize_path(path: str) -> Path:
    """
    Sanitize the input path by removing backslashes before spaces and normalizing the path.
    
    Args:
        path (str): The original path string input by the user.
        
    Returns:
        Path: The sanitized Path object.
    """
    try:
        # Replace escaped spaces (\ ) with regular spaces
        sanitized_str = path.replace('\\ ', ' ')
        
        # Additionally, handle other common escape characters if necessary
        # For example, replace double backslashes with single backslash
        sanitized_str = sanitized_str.replace('\\\\', '\\')
        
        # Create a Path object and normalize it
        sanitized_path = Path(sanitized_str).expanduser().resolve()
        
        return sanitized_path
    except Exception as e:
        logger.error(f"Exception in sanitize_path: {e}")
        raise  # Re-raise the exception to be handled by the caller

def validate_path(path: Path, description: str) -> bool:
    """
    Validate that the provided path exists and is of the expected type.
    
    Args:
        path (Path): The Path object to validate.
        description (str): Description of the path for logging purposes.
    
    Returns:
        bool: True if valid, False otherwise.
    """
    if not path.exists():
        logger.error(f"The {description} '{path}' does not exist.")
        return False
    if description == "M3U playlist file" and not path.is_file():
        logger.error(f"The {description} '{path}' is not a file.")
        return False
    if description == "music directory" and not path.is_dir():
        logger.error(f"The {description} '{path}' is not a directory.")
        return False
    return True

def copy_tracks_with_sequence(
    m3u_file: str,
    music_dir: str,
    output_folder: str,
    max_size_gb: Optional[float] = None,
    dry_run: bool = False
) -> Tuple[int, int]:
    """
    Copy tracks listed in an M3U file from the music directory to the output folder,
    renaming them with a six-digit sequence number.
    
    Args:
        m3u_file (str): Path to the M3U playlist file.
        music_dir (str): Path to the source music directory.
        output_folder (str): Path to the destination folder where tracks will be copied.
        max_size_gb (float, optional): Maximum cumulative size in GB for the copied tracks.
                                        Defaults to None (no limit).
        dry_run (bool, optional): If True, simulates the copying process without making changes.
                                   Defaults to False.
    
    Returns:
        tuple: (number_of_successful_copies, number_of_failures)
    """
    try:
        # Sanitize input paths
        m3u_path = sanitize_path(m3u_file)
        music_directory = sanitize_path(music_dir)
        output_dir = sanitize_path(output_folder)

        # Validate input paths
        if not validate_path(m3u_path, "M3U playlist file"):
            return (0, 0)
        if not validate_path(music_directory, "music directory"):
            return (0, 0)
        if not validate_path(output_dir, "output directory"):
            return (0, 0)

        # Ensure the output "Music" subfolder exists
        music_folder = output_dir / 'Music'
        if not dry_run:
            music_folder.mkdir(parents=True, exist_ok=True)
            logger.info(f"Ensured existence of output subfolder: {music_folder}")
        else:
            logger.info(f"[Dry Run] Would ensure existence of output subfolder: {music_folder}")

        # Convert max size to bytes if specified
        max_size_bytes = max_size_gb * (1024 ** 3) if max_size_gb else None
        total_copied_size = 0

        # Initialize counters
        success_count = 0
        failure_count = 0

        # Read the M3U file and get the track paths (resolving relative paths)
        with m3u_path.open('r', encoding='utf-8') as file:
            tracks = [line.strip() for line in file if line.strip() and not line.startswith('#')]

        logger.info(f"Total tracks to process from M3U: {len(tracks)}")

        # Copy each track to the output folder with the new filename
        for idx, relative_track in enumerate(tracks):
            # Sanitize relative track path
            relative_track_path = sanitize_path(relative_track)

            # Resolve the absolute path of the track
            track_path = (music_directory / relative_track_path).resolve()

            if not track_path.is_file():
                logger.warning(f"Track not found: {track_path}")
                failure_count += 1
                continue

            original_size = track_path.stat().st_size  # File size in bytes

            # Check if adding this track exceeds the max size limit
            if max_size_bytes and (total_copied_size + original_size) > max_size_bytes:
                logger.info(f"Max size limit of {max_size_gb} GB reached. Stopping execution.")
                break

            # Create the new filename with six-digit sequence number
            sequence_num = f"{idx + 1:06d}"
            original_filename = track_path.name
            new_filename = f"{sequence_num} - {original_filename}"
            new_filepath = music_folder / new_filename

            # Check for duplicate filenames
            if new_filepath.exists():
                logger.warning(f"File already exists and will be skipped: {new_filepath}")
                failure_count += 1
                continue

            if dry_run:
                logger.info(f"[Dry Run] Would copy: {track_path} -> {new_filepath} (Size: {original_size} bytes)")
                success_count += 1
                total_copied_size += original_size
                continue

            try:
                shutil.copy2(track_path, new_filepath)

                # Verify the copied file size
                copied_size = new_filepath.stat().st_size
                if copied_size != original_size:
                    raise IOError(f"File size mismatch after copying {track_path} -> {new_filepath}")

                total_copied_size += copied_size
                success_count += 1
                logger.info(f"Copied: {track_path} -> {new_filepath} (Size: {copied_size} bytes)")

                # Log cumulative size in bytes and GB
                cumulative_size_gb = convert_size_to_gb(total_copied_size)
                logger.info(f"Cumulative size of copied files: {total_copied_size} bytes ({cumulative_size_gb:.2f} GB)")
                logger.info("")  # For readability

            except Exception as e:
                logger.error(f"Error copying {track_path}: {e}")
                failure_count += 1
                continue

        logger.info("File copying process complete.")
        logger.info(f"Total successful copies: {success_count}")
        logger.info(f"Total failures: {failure_count}")
        logger.info(f"Total size copied: {total_copied_size} bytes ({convert_size_to_gb(total_copied_size):.2f} GB)")
        return (success_count, failure_count)

    except Exception as e:
        logger.error(f"An error occurred: {e}")
        return (0, 0)
