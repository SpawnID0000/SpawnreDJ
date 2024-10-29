import os
import logging
from mutagen import File

def get_track_info(file_path):
    """Extract track metadata including album, disc number, and track number."""
    try:
        audio = File(file_path, easy=True)
        if audio is None:
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

        return duration, title, artist, album, disc_number, track_number
    except Exception as e:
        logging.error(f"Error processing {file_path}: {e}")
        return None

def parse_number(number):
    """Parse a number which could be in a string format like '1/10'."""
    if isinstance(number, str):
        try:
            return int(number.split('/')[0])
        except ValueError:
            return 0
    elif isinstance(number, int):
        return number
    else:
        return 0

def normalize_artist_name(artist_name):
    """Normalize the artist name by removing 'The ' prefix if present."""
    if artist_name.lower().startswith('the '):
        return artist_name[4:]
    return artist_name

def generate_m3u(music_dir, m3u_file_path, flip_order=False, path_prefix='../'):
    """
    Generate an M3U playlist from the specified music directory.

    Args:
        music_dir (str): Path to the music directory.
        m3u_file_path (str): Path where the M3U file will be saved (including filename).
        flip_order (bool): Whether to flip the artist and track in EXTINF lines.
        path_prefix (str): Prefix to add to each path in the playlist (default: '../').

    Returns:
        bool: True if the playlist was successfully generated, False otherwise.
    """
    entries = []
    music_dir = os.path.abspath(music_dir)
    m3u_file_path = os.path.abspath(m3u_file_path)

    print(f"Generating M3U playlist from directory: {music_dir}")
    print(f"Playlist will be saved to: {m3u_file_path}")

    # Ensure the music directory exists
    if not os.path.isdir(music_dir):
        print(f"Error: The directory '{music_dir}' does not exist or is not a directory.")
        return False

    for root, _, files in os.walk(music_dir):
        for file in files:
            if file.lower().endswith(('.opus', '.m4a', '.mp3', '.flac')):
                file_path = os.path.abspath(os.path.join(root, file))
                track_info = get_track_info(file_path)
                if track_info:
                    duration, title, artist, album, disc_number, track_number = track_info
                    relative_path = os.path.relpath(file_path, os.path.dirname(m3u_file_path))
                    relative_path = os.path.join(path_prefix, relative_path).replace(os.sep, '/')
                    entries.append((artist, album, disc_number, track_number, title, duration, relative_path))

    print(f"Number of tracks found: {len(entries)}")

    if not entries:
        print("No audio files found in the specified directory.")
        return False

    # Sorting by normalized artist name, album, disc number, and then track number
    entries.sort(key=lambda x: (normalize_artist_name(x[0]).lower(), x[1].lower(), x[2], x[3]))

    try:
        with open(m3u_file_path, 'w', encoding='utf-8') as m3u_file:
            m3u_file.write("#EXTM3U\n")
            for entry in entries:
                extinf_line = f"#EXTINF:{entry[5]},{entry[0]} - {entry[4]}\n" if flip_order else f"#EXTINF:{entry[5]},{entry[4]} - {entry[0]}\n"
                m3u_file.write(extinf_line)
                m3u_file.write(f"{entry[6]}\n")
    except Exception as e:
        print(f"Error writing M3U file: {e}")
        return False

    print("M3U playlist generation complete.")
    return True

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Create an M3U playlist from a folder of audio files.")
    parser.add_argument("music_dir", help="Path to the music directory")
    parser.add_argument("-flip", action="store_true", help="Flip the order of artist and track in the EXTINF line (default is Track - Artist)")
    parser.add_argument("-prefix", default="../", help="Prefix to add to each path in the playlist (default: '../')")

    args = parser.parse_args()

    generate_m3u(args.music_dir, flip=args.flip, path_prefix=args.prefix)
