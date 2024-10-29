# folder_from_M3U.py

import os
import shutil

def convert_size_to_gb(size_in_bytes):
    """Convert size from bytes to gigabytes."""
    return size_in_bytes / (1024 ** 3)

def copy_tracks_with_sequence(m3u_file, music_dir, output_folder, max_size_gb=None):
    """
    Copy tracks listed in an M3U file from the music directory to the output folder,
    renaming them with a six-digit sequence number.

    Args:
        m3u_file (str): Path to the M3U playlist file.
        music_dir (str): Path to the source music directory.
        output_folder (str): Path to the destination folder where tracks will be copied.
        max_size_gb (float, optional): Maximum cumulative size in GB for the copied tracks.
                                        Defaults to None (no limit).

    Returns:
        tuple: (number_of_successful_copies, number_of_failures)
    """
    try:
        # Ensure the output folder exists, and create the "Music" subfolder
        music_folder = os.path.join(output_folder, 'Music')
        os.makedirs(music_folder, exist_ok=True)

        # Convert the max size to bytes if specified
        max_size_bytes = max_size_gb * (1024 ** 3) if max_size_gb else None
        total_copied_size = 0

        # Initialize counters
        success_count = 0
        failure_count = 0

        # Read the M3U file and get the track paths (resolving relative paths)
        with open(m3u_file, 'r', encoding='utf-8') as file:
            tracks = [line.strip() for line in file if line.strip() and not line.startswith('#')]

        # Copy each track to the output folder with the new filename
        for idx, relative_track in enumerate(tracks):
            # Resolve relative path based on music_dir
            track_path = os.path.abspath(os.path.join(music_dir, relative_track))

            if not os.path.isfile(track_path):
                print(f"Track not found: {track_path}")
                failure_count += 1
                continue

            original_size = os.path.getsize(track_path)  # Get the original file size in bytes

            # Stop if adding the next track would exceed the max size limit
            if max_size_bytes and (total_copied_size + original_size) > max_size_bytes:
                print(f"Max size limit of {max_size_gb} GB reached. Stopping execution.")
                break

            # Create the new filename with six-digit sequence number
            sequence_num = f"{idx + 1:06d}"
            original_filename = os.path.basename(track_path)
            new_filename = f"{sequence_num} - {original_filename}"

            # Copy the file to the "Music" folder
            new_filepath = os.path.join(music_folder, new_filename)

            try:
                shutil.copy2(track_path, new_filepath)

                # Ensure that the copied file size matches the original file size
                copied_size = os.path.getsize(new_filepath)
                if copied_size != original_size:
                    raise IOError(f"File size mismatch after copying {track_path} -> {new_filepath}")

                total_copied_size += copied_size
                success_count += 1
                print(f"Copied: {track_path} -> {new_filepath} (Size: {copied_size} bytes)")
                
                # Print cumulative copied size in both bytes and GB
                cumulative_size_gb = convert_size_to_gb(total_copied_size)
                print(f"Cumulative size of copied files: {total_copied_size} bytes ({cumulative_size_gb:.2f} GB)")
                print()

            except Exception as e:
                print(f"Error copying {track_path}: {e}")
                failure_count += 1
                continue

        print("File copying process complete.")
        print(f"Total size copied: {total_copied_size} bytes ({convert_size_to_gb(total_copied_size):.2f} GB)")
        return (success_count, failure_count)

    except Exception as e:
        print(f"An error occurred: {e}")
        return (0, 0)
