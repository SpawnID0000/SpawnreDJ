# M3U_from_CSV.py

import pandas as pd
import os
import random
import logging
import csv
from types import SimpleNamespace
from typing import Any, Optional

# Import the genre mapping dictionary from dic_spawnre.py
from SpawnreDJ.dic_spawnre import genre_mapping

# Define genre clusters and transition logic
cluster_transition_logic = {
    'rock': ['blues', 'folk', 'funk'],
    'folk': ['folk-rock', 'country', 'rock'],
    'pop': ['rock', 'R&B'],
    'jazz': ['blues', 'R&B'],
    'reggae': ['R&B', 'funk'],
    'R&B': ['hip-hop', 'jazz'],
    'country': ['folk', 'blues'],
    'blues': ['rock', 'jazz'],
    'hip-hop': ['R&B', 'electronic'],
    'electronic': ['hip-hop', 'pop'],
    'classical': ['jazz', 'acoustic rock']
}

def get_genres_from_hex(hex_code: str) -> list:
    """
    Extracts the genres from the provided hexadecimal code based on genre_mapping.
    
    Args:
        hex_code (str): The hexadecimal code representing genres.
    
    Returns:
        list: A list of genre names corresponding to the hex code.
    """
    genres = []
    for i in range(0, len(hex_code), 2):
        chunk = hex_code[i:i+2]
        formatted_chunk = f'0x{chunk.upper()}'
        for key, value in genre_mapping.items():
            if value['Hex'] == formatted_chunk:
                genres.append(value['Genre'])
    return genres

def create_clusters(df: pd.DataFrame, loved_csv: Optional[str] = None) -> dict:
    """
    Creates clusters of tracks based on genre and optionally filters by loved status.
    
    Args:
        df (pd.DataFrame): The DataFrame containing track information.
        loved_csv (str, optional): Path to the _loved.csv file for filtering. Defaults to None.
    
    Returns:
        dict: A dictionary where keys are genres and values are lists of track file paths.
    """
    clusters = {}

    # Load the _loved.csv file if provided to filter by loved status
    loved_options = {}
    if loved_csv and os.path.exists(loved_csv):
        loved_df = pd.read_csv(loved_csv)
        loved_options = {
            'tracks': loved_df['loved_tracks'].str.lower() == 'yes',
            'albums': loved_df['loved_albums'].str.lower() == 'yes',
            'artists': loved_df['loved_artists'].str.lower() == 'yes'
        }

    logging.info(f"Processing {len(df)} rows from the CSV file.")

    for index, row in df.iterrows():
        # Extract genre from either 'spawnre_tag' or 'embedded_genre'
        genre = row.get('spawnre_tag') or row.get('embedded_genre', 'Unknown')

        # Initialize cluster if it doesn't exist
        if genre not in clusters:
            clusters[genre] = []

        # Handle loved status (if applicable)
        if loved_csv:
            is_loved_track = loved_options.get('tracks', pd.Series([False])).iloc[index] if 'loved_tracks' in row else False
            is_loved_album = loved_options.get('albums', pd.Series([False])).iloc[index] if 'loved_albums' in row else False
            is_loved_artist = loved_options.get('artists', pd.Series([False])).iloc[index] if 'loved_artists' in row else False

            # Add the track to the cluster if it meets the loved criteria
            if is_loved_track or is_loved_album or is_loved_artist:
                clusters[genre].append(row['file_path'])
        else:
            # If no loved filtering is applied, add all tracks
            clusters[genre].append(row['file_path'])

    logging.info(f"Created {len(clusters)} genre clusters.")
    return clusters

def order_clusters(clusters: dict, shuffle: bool = False) -> list:
    """
    Orders clusters based on the genre and transition logic. Optionally shuffles tracks within clusters.
    
    Args:
        clusters (dict): The dictionary containing genre clusters.
        shuffle (bool, optional): Whether to shuffle tracks within each cluster. Defaults to False.
    
    Returns:
        list: A list of tuples containing genre and ordered list of tracks.
    """
    ordered_clusters = []
    used_genres = set()

    for genre, tracks in clusters.items():
        if genre not in used_genres:
            if shuffle:
                random.shuffle(tracks)
            ordered_clusters.append((genre, tracks))
            used_genres.add(genre)

    return ordered_clusters

def write_m3u(ordered_clusters: list, output_file: str, root_directory: str, path_prefix: str = '../') -> list:
    """
    Writes the ordered genre clusters into an M3U playlist file with relative paths.
    
    Args:
        ordered_clusters (list): List of tuples containing genre and tracks.
        output_file (str): Path to the output M3U file.
        root_directory (str): The root directory to calculate relative paths.
        path_prefix (str, optional): Prefix to add to each path in the playlist. Defaults to '../'.
    
    Returns:
        list: The ordered_clusters list for further use if needed.
    """
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write("#EXTM3U\n")
        for genre, tracks in ordered_clusters:
            f.write(f"# Genre: {genre}\n")
            for absolute_path in tracks:
                # Convert absolute path to relative path based on the root_directory
                relative_path = os.path.relpath(absolute_path, root_directory)
                # Prepend the path prefix to the relative path
                f.write(f"{path_prefix}{relative_path}\n")
    return ordered_clusters

def print_summary(ordered_clusters: list) -> None:
    """
    Prints a summary of the clusters and the number of tracks in each.
    
    Args:
        ordered_clusters (list): List of tuples containing genre and tracks.
    """
    print("\nClusters summary (in M3U order):")
    for genre, tracks in ordered_clusters:
        print(f"- {genre}: {len(tracks)} tracks")

def parse_m3u_for_loved(m3u_file: str, music_directory: str) -> set:
    """
    Parses a loved M3U file and returns a set of absolute, normalized file paths.
    
    Args:
        m3u_file (str): Path to the loved M3U file.
        music_directory (str): Root directory of the music files to resolve relative paths.
    
    Returns:
        set: A set of normalized file paths that are marked as loved.
    """
    loved_paths = set()
    if os.path.exists(m3u_file):
        with open(m3u_file, 'r', encoding='utf-8') as file:
            for line in file:
                line = line.strip()
                if line and not line.startswith("#"):
                    # Resolve relative paths to absolute paths
                    if not os.path.isabs(line):
                        path = os.path.join(music_directory, line)
                    else:
                        path = line
                    # Normalize and lowercase the path for consistent comparison
                    normalized_path = os.path.normpath(path).lower()
                    loved_paths.add(normalized_path)
    else:
        logging.warning(f"Loved M3U file '{m3u_file}' does not exist.")
    return loved_paths

def process_m3u_with_loved(args: Any, loved_tracks: set, loved_albums: set, loved_artists: set) -> None:
    """
    Processes the main playlist CSV and appends loved metadata.
    
    Args:
        args (Any): A SimpleNamespace object containing arguments, primarily the m3u_file path.
        loved_tracks (set): Set of loved track file paths.
        loved_albums (set): Set of loved album directory paths.
        loved_artists (set): Set of loved artist directory paths.
    """
    # Define paths based on the m3u_file
    csv_file_path = os.path.splitext(args.m3u_file)[0] + '.csv'
    output_csv_path = os.path.splitext(args.m3u_file)[0] + '_loved.csv'

    try:
        with open(csv_file_path, newline='', encoding='utf-8') as csvfile:
            reader = csv.DictReader(csvfile)
            fieldnames = reader.fieldnames + ['loved_tracks', 'loved_albums', 'loved_artists']
            data = list(reader)  # Store all the data in a list for processing

        with open(output_csv_path, 'w', newline='', encoding='utf-8') as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()

            for track_data in data:
                # Normalize the file path for comparison
                file_path = track_data.get('file_path', '').lower()
                normalized_file_path = os.path.normpath(file_path)

                # Derive album and artist directories
                album_dir = os.path.dirname(normalized_file_path)
                album_dir_normalized = os.path.normpath(album_dir.lower())

                artist_dir = os.path.dirname(album_dir)
                artist_dir_normalized = os.path.normpath(artist_dir.lower())

                # Check if the track, album, or artist is "loved"
                is_loved_track = 'yes' if normalized_file_path in loved_tracks else 'no'
                is_loved_album = 'yes' if album_dir_normalized in loved_albums else 'no'
                is_loved_artist = 'yes' if artist_dir_normalized in loved_artists else 'no'

                # Add the loved metadata
                track_data['loved_tracks'] = is_loved_track
                track_data['loved_albums'] = is_loved_album
                track_data['loved_artists'] = is_loved_artist

                # Write the updated row to the new CSV file
                writer.writerow(track_data)

        logging.info(f"Loved metadata CSV file created successfully: {output_csv_path}")

    except Exception as e:
        logging.error(f"Error processing loved metadata: {e}")

def generate_curated_m3u(args: Any) -> None:
    """
    Generates a curated M3U playlist from the provided CSV file, optionally filtering by loved metadata.
    
    Args:
        args (Any): A SimpleNamespace object containing:
                    - csv_file (str): Path to the input CSV file.
                    - loved_csv (str, optional): Path to the _loved.csv file.
                    - shuffle (bool): Whether to shuffle tracks within clusters.
    """
    # Load the CSV file into a DataFrame
    try:
        df = pd.read_csv(args.csv_file, delimiter=',', on_bad_lines='skip', quoting=1)  # Handle commas
    except Exception as e:
        logging.error(f"Error reading CSV file '{args.csv_file}': {e}")
        return

    # Clean up column names
    df.columns = df.columns.str.strip()

    # Create clusters based on spawnre genres and loved options (_loved.csv)
    clusters = create_clusters(df, loved_csv=args.loved_csv)

    # Order clusters based on transition logic
    ordered_clusters = order_clusters(clusters, shuffle=args.shuffle)

    # Write output M3U playlist
    output_file = args.csv_file.replace('.csv', '_curated.m3u')
    ordered_clusters = write_m3u(ordered_clusters, output_file, root_directory=os.path.dirname(args.csv_file))

    print(f"Curated M3U playlist created: {output_file}")

    # Print cluster summary in the same order as the M3U file
    print_summary(ordered_clusters)

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Generate a curated M3U playlist from a CSV file.")
    parser.add_argument("csv_file", help="Path to the input CSV file")
    parser.add_argument("-loved_csv", help="Path to the _loved.csv file (optional)", default=None)
    parser.add_argument("-shuffle", action="store_true", help="Shuffle the tracks within each cluster")

    args = parser.parse_args()
    generate_curated_m3u(args)
