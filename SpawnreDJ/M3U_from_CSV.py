# M3U_from_CSV.py

import pandas as pd
import sys
from collections import defaultdict
import math
import random
import argparse
import logging
import os

# Genre mapping dictionary (truncated for brevity)
genre_mapping = {
    'A00': {'Hex': '0x00', 'Genre': 'rock'}, 'A01': {'Hex': '0x01', 'Genre': 'classic rock'},
    'A02': {'Hex': '0x02', 'Genre': 'alternative rock'}, 'A03': {'Hex': '0x03', 'Genre': 'indie rock'},
    'B00': {'Hex': '0x18', 'Genre': 'folk'}, 'C00': {'Hex': '0x30', 'Genre': 'pop'},
    'D00': {'Hex': '0x48', 'Genre': 'jazz'}, 'E00': {'Hex': '0x60', 'Genre': 'reggae'},
    'F00': {'Hex': '0x76', 'Genre': 'R&B'}, 'G00': {'Hex': '0x8C', 'Genre': 'country'},
    'H00': {'Hex': '0xA2', 'Genre': 'blues'}, 'I00': {'Hex': '0xB8', 'Genre': 'hip-hop'},
    'J00': {'Hex': '0xD0', 'Genre': 'electronic'}, 'K00': {'Hex': '0xE8', 'Genre': 'classical'}
}

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

def get_genres_from_hex(hex_code):
    """
    Extracts the genres from the provided hexadecimal code based on genre_mapping.
    """
    genres = []
    for i in range(0, len(hex_code), 2):
        chunk = hex_code[i:i+2]
        formatted_chunk = f'0x{chunk.upper()}'
        for key, value in genre_mapping.items():
            if value['Hex'] == formatted_chunk:
                genres.append(value['Genre'])
    return genres

def create_clusters(df, loved_options=None):
    """
    Function to create clusters of tracks based on genre and optionally filter by loved status.
    """
    clusters = {}
    
    logging.info(f"Processing {len(df)} rows from the CSV file.")
    
    for index, row in df.iterrows():
        # Extract genre from either 'spawnre_tag' or 'embedded_genre'
        genre = row.get('spawnre_tag') or row.get('embedded_genre', 'Unknown')

        # Initialize cluster if it doesn't exist
        if genre not in clusters:
            clusters[genre] = []

        # Handle loved status (if applicable)
        loved_track = row.get('loved_tracks', '').lower() == 'yes' if 'tracks' in (loved_options or []) else False
        loved_album = row.get('loved_albums', '').lower() == 'yes' if 'albums' in (loved_options or []) else False
        loved_artist = row.get('loved_artists', '').lower() == 'yes' if 'artists' in (loved_options or []) else False
        
        # Add the track to the cluster if it meets the loved criteria or if loved options are not being filtered
        if not loved_options or loved_track or loved_album or loved_artist:
            clusters[genre].append(row['file_path'])  # Use 'file_path' to get the track's path

    logging.info(f"Created {len(clusters)} genre clusters.")
    return clusters

    logging.info(f"Loved columns present: Tracks={has_loved_tracks}, Albums={has_loved_albums}, Artists={has_loved_artists}")
    
    # Loop through the rows of the dataframe to organize by genre clusters
    for index, row in df.iterrows():
        # Log the entire row for debugging purposes
        logging.debug(f"Row {index}: {row.to_dict()}")

        # Check if the 'genre' column is available and handle missing values
        genre = row.get('genre', 'Unknown')
        if pd.isna(genre) or not genre:
            genre = 'Unknown'
        logging.debug(f"Row {index}: Genre identified as {genre}")

        # Initialize cluster if it doesn't exist
        if genre not in clusters:
            clusters[genre] = []

        # Determine if the track should be loved based on the loved_options
        loved_track = row.get('loved_tracks', '').lower() == 'yes' if has_loved_tracks and 'tracks' in (loved_options or []) else False
        loved_album = row.get('loved_albums', '').lower() == 'yes' if has_loved_albums and 'albums' in (loved_options or []) else False
        loved_artist = row.get('loved_artists', '').lower() == 'yes' if has_loved_artists and 'artists' in (loved_options or []) else False
        
        logging.debug(f"Loved Track: {loved_track}, Loved Album: {loved_album}, Loved Artist: {loved_artist}")

        # Add the track to the cluster if it meets the loved criteria or if loved options are not being filtered
        if not loved_options or loved_track or loved_album or loved_artist:
            file_path = row.get('file_path', 'Unknown path')  # Use 'Unknown path' if the file path is missing
            clusters[genre].append(row['file_path'])
            logging.debug(f"Row {index} with file path '{file_path}' added to cluster '{genre}'.")

    logging.info(f"Created {len(clusters)} genre clusters.")
    return clusters

def order_clusters(clusters, shuffle=False):
    """
    Orders clusters based on the genre and transition logic. Optionally shuffles tracks within clusters.
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

def write_m3u(ordered_clusters, output_file, root_directory, path_prefix='../'):
    """
    Writes the ordered genre clusters into an M3U playlist file with relative paths.
    """
    with open(output_file, 'w') as f:
        f.write("#EXTM3U\n")
        for genre, tracks in ordered_clusters:
            f.write(f"# Genre: {genre}\n")
            for absolute_path in tracks:
                # Convert absolute path to relative path based on the root_directory
                relative_path = os.path.relpath(absolute_path, root_directory)
                # Prepend the path prefix to the relative path
                f.write(f"{path_prefix}{relative_path}\n")
    return ordered_clusters

def print_summary(ordered_clusters):
    """
    Prints a summary of the clusters and the number of tracks in each.
    """
    print("Clusters summary (in M3U order):")
    for genre, tracks in ordered_clusters:
        print(f"- {genre}: {len(tracks)} tracks")

def main(args):
    """
    Main function to handle input arguments, process the CSV, and create a genre-clustered M3U playlist.
    """
    # Load the CSV file into a DataFrame
    df = pd.read_csv(args.csv_file, delimiter=',', on_bad_lines='skip', quoting=1)  # Handle commas

    # Clean up column names
    df.columns = df.columns.str.strip()

    # Create clusters based on spawnre genres and loved options
    clusters = create_clusters(df, args.loved)

    # Order clusters based on transition logic
    ordered_clusters = order_clusters(clusters, shuffle=args.shuffle)

    # Write output M3U playlist
    output_file = args.csv_file.replace('.csv', '_clustered.m3u')
    ordered_clusters = write_m3u(ordered_clusters, output_file)
    print(f"M3U playlist created: {output_file}")

    # Print cluster summary in the same order as the M3U file
    print_summary(ordered_clusters)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate a genre-clustered M3U playlist from a CSV file.")
    parser.add_argument("csv_file", help="Path to the input CSV file")
    parser.add_argument("-shuffle", action="store_true", help="Shuffle the tracks within each cluster")
    parser.add_argument("-loved", nargs='+', choices=['tracks', 'albums', 'artists'], help="Filter by loved tracks, albums, or artists")

    args = parser.parse_args()
    main(args)
