# M3U_from_CSV.py

import pandas as pd
import random
import logging
import numpy as np
import csv  # Import for csv module
from types import SimpleNamespace
from typing import Optional, List, Dict
from pathlib import Path
from SpawnreDJ.dic_spawnre import genre_mapping

# Define feature columns and initial tolerances
feature_columns = [
    'danceability', 'energy', 'loudness', 'speechiness', 
    'acousticness', 'instrumentalness', 'liveness', 'valence', 'tempo'
]
initial_tolerances = {col: 0.1 if col not in ['loudness', 'tempo'] else 5.0 for col in feature_columns}

logger = logging.getLogger(__name__)

def sanitize_path(path: str) -> Path:
    sanitized = path.replace('\\ ', ' ').replace('\\\\', '\\')
    return Path(sanitized).expanduser().resolve()

def load_csv(file_path: Path, delimiter=',', quoting=csv.QUOTE_MINIMAL) -> pd.DataFrame:
    try:
        df = pd.read_csv(file_path, delimiter=delimiter, quoting=quoting, on_bad_lines='skip')
        df.columns = df.columns.str.strip().str.lower()
        return df
    except Exception as e:
        logger.error(f"Error loading CSV file '{file_path}': {e}")
        return pd.DataFrame()

def create_clusters(df: pd.DataFrame, loved_csv: Optional[Path] = None, loved_categories: Optional[List[str]] = None) -> dict:
    clusters = {}
    
    # Load the _loved.csv file if provided to filter by loved status
    loved_options = {}
    if loved_csv and loved_csv.exists() and loved_categories:
        loved_df = load_csv(loved_csv)
        if not loved_df.empty:
            loved_options = {
                'tracks': loved_df['loved_tracks'].str.lower() == 'yes',
                'albums': loved_df['loved_albums'].str.lower() == 'yes',
                'artists': loved_df['loved_artists'].str.lower() == 'yes'
            }
        else:
            logger.warning(f"Loved CSV file '{loved_csv}' is empty.")
    
    logger.info(f"Processing {len(df)} rows from the CSV file.")
    
    for index, row in df.iterrows():
        genre = row.get('spawnre_tag') or row.get('embedded_genre', 'Unknown')
        genre = genre.strip().lower() if isinstance(genre, str) else 'unknown'
        
        # Initialize the genre cluster if not present
        if genre not in clusters:
            clusters[genre] = []
        
        # Determine if the track should be included based on loved categories
        include_track = True
        if loved_options and loved_categories:
            is_loved = False
            for category in loved_categories:
                if category in loved_options and loved_options[category].iloc[index]:
                    is_loved = True
                    break
            include_track = is_loved
            if not include_track:
                continue  # Skip adding this track as it does not meet loved criteria
        
        clusters[genre].append(row['file_path'])
    
    return clusters

def clean_features_df(features_df: pd.DataFrame) -> pd.DataFrame:
    """ Ensure that `features_df` contains only rows with all necessary feature columns. """
    missing_columns = [col for col in feature_columns if col not in features_df.columns]
    if missing_columns:
        logger.error(f"Missing required feature columns in features CSV: {missing_columns}")
        return pd.DataFrame()
    
    # Drop rows with NaNs in required feature columns
    features_df.dropna(subset=feature_columns, inplace=True)
    
    # Convert feature columns to numeric types
    for col in feature_columns:
        features_df[col] = pd.to_numeric(features_df[col], errors='coerce')
    
    # After conversion, drop any rows that have NaN in feature columns due to conversion errors
    features_df.dropna(subset=feature_columns, inplace=True)
    
    # Create a unique identifier for each track
    features_df['unique_track'] = features_df['track'].str.strip().str.lower() + "_" + features_df['artist'].str.strip().str.lower()
    
    # Drop duplicates based on unique_track to ensure uniqueness
    features_df.drop_duplicates(subset=['unique_track'], inplace=True)
    
    # Set 'unique_track' as the index for easy lookup
    features_df.set_index('unique_track', inplace=True)
    
    # Select only feature_columns to ensure no extra columns are present
    features_df = features_df[feature_columns]
    
    logger.info(f"Cleaned features DataFrame: {features_df.shape[0]} records remaining after cleaning.")
    
    # Log data types to ensure correct conversion
    logger.debug(f"Data types after cleaning:\n{features_df.dtypes}")
    
    return features_df

def curate_cluster(cluster: List[str], main_df: pd.DataFrame, features_df: pd.DataFrame) -> List[str]:
    if len(cluster) <= 1:
        return cluster.copy()
    
    curated_order = [cluster.pop(0)]
    tolerance = initial_tolerances.copy()
    
    while cluster:
        current_file_path = curated_order[-1]
        # Normalize the file path for comparison
        normalized_current_path = Path(current_file_path).as_posix().lower()
        current_row = main_df[main_df['file_path'].str.lower() == normalized_current_path]
    
        if current_row.empty:
            logger.error(f"Current file path '{current_file_path}' not found in main CSV.")
            break  # Alternatively, continue to the next track
    
        current_track = current_row['track'].values[0]
        current_artist = current_row['artist'].values[0]
        unique_current_track = f"{current_track.strip().lower()}_{current_artist.strip().lower()}"
    
        if unique_current_track not in features_df.index:
            logger.warning(f"Missing features for current track '{unique_current_track}'. Skipping to next track.")
            # Instead of breaking, try to find the next track in the cluster
            if cluster:
                curated_order.append(cluster.pop(0))
            else:
                break
            continue
    
        current_features = features_df.loc[unique_current_track].to_numpy()
        
        # Debugging: Log the type and content of current_features
        logger.debug(f"Current Features ({unique_current_track}): {current_features}")
        logger.debug(f"Type of current_features: {type(current_features)}")
    
        next_track, min_distance = None, float('inf')
    
        for candidate_path in cluster:
            normalized_candidate_path = Path(candidate_path).as_posix().lower()
            candidate_row = main_df[main_df['file_path'].str.lower() == normalized_candidate_path]
            if candidate_row.empty:
                logger.error(f"Candidate file path '{candidate_path}' not found in main CSV.")
                continue
    
            candidate_track = candidate_row['track'].values[0]
            candidate_artist = candidate_row['artist'].values[0]
            unique_candidate_track = f"{candidate_track.strip().lower()}_{candidate_artist.strip().lower()}"
    
            if unique_candidate_track not in features_df.index:
                logger.warning(f"Incomplete features for candidate track '{unique_candidate_track}'. Skipping.")
                continue
    
            candidate_features = features_df.loc[unique_candidate_track].to_numpy()
            
            # Debugging: Log the type and content of candidate_features
            logger.debug(f"Candidate Features ({unique_candidate_track}): {candidate_features}")
            logger.debug(f"Type of candidate_features: {type(candidate_features)}")
    
            # Ensure that both feature arrays are numeric
            if not (isinstance(candidate_features, np.ndarray) and isinstance(current_features, np.ndarray)):
                logger.error(f"Feature data types are not compatible for '{unique_candidate_track}'. Skipping.")
                continue
    
            distance = np.linalg.norm(candidate_features - current_features)
            logger.debug(f"Distance between '{unique_current_track}' and '{unique_candidate_track}': {distance}")
            if distance < min_distance:
                next_track, min_distance = candidate_path, distance
    
        if next_track:
            curated_order.append(next_track)
            cluster.remove(next_track)
        else:
            # If no similar next track found, append the next available track randomly
            logger.info("No similar next track found based on audio features. Appending the next track randomly.")
            curated_order.append(cluster.pop(0))
    
    return curated_order

def order_clusters(clusters: dict, main_df: pd.DataFrame, features_df: Optional[pd.DataFrame], curate: bool = False) -> list:
    ordered_clusters = []
    for genre, tracks in clusters.items():
        if tracks:
            if curate and features_df is not None:
                curated_paths = curate_cluster(tracks.copy(), main_df, features_df)
            else:
                curated_paths = tracks.copy()
                random.shuffle(curated_paths)
            ordered_clusters.append((genre, curated_paths))
    return ordered_clusters

def write_m3u(ordered_clusters: list, output_file: Path, root_directory: Path, path_prefix: str = '../') -> None:
    with output_file.open('w', encoding='utf-8') as f:
        f.write("#EXTM3U\n")
        for genre, tracks in ordered_clusters:
            if tracks:
                f.write(f"# Genre: {genre}\n")
                for path in tracks:
                    absolute_path = (root_directory / path).resolve()
                    try:
                        relative_path = absolute_path.relative_to(root_directory)
                        f.write(f"{path_prefix}{relative_path.as_posix()}\n")
                    except ValueError:
                        # If absolute_path is not under root_directory, use absolute path
                        f.write(f"{absolute_path.as_posix()}\n")
    logger.info(f"Curated M3U playlist written to '{output_file}'.")

def print_summary(ordered_clusters: list) -> None:
    print("\nClusters summary (in M3U order):")
    for genre, tracks in ordered_clusters:
        print(f"- {genre}: {len(tracks)} tracks")

def generate_curated_m3u(args: SimpleNamespace) -> None:
    csv_file = Path(args.csv_file)
    df = load_csv(csv_file)
    
    if 'file_path' not in df.columns:
        logger.error(f"'file_path' column is missing in the main CSV file '{csv_file}'. Please check the CSV structure.")
        return
    
    features_file = csv_file.with_name(csv_file.stem + '_features.csv')
    features_df = None
    if features_file.exists():
        features_df = load_csv(features_file)
        if 'track' not in features_df.columns or 'artist' not in features_df.columns:
            logger.error(f"'track' and 'artist' columns are missing in the features CSV file '{features_file}'. Please check the CSV structure.")
            return
        features_df = clean_features_df(features_df)
        if features_df.empty:
            logger.error("Features DataFrame is empty after cleaning. Check the features CSV.")
            return
        logger.info("Successfully loaded and cleaned features CSV for curation support.")
    else:
        logger.warning(f"Features file '{features_file}' not found. Proceeding without features.")
    
    clusters = create_clusters(df, loved_csv=args.loved_csv, loved_categories=args.loved)
    ordered_clusters = order_clusters(clusters, df, features_df, curate=args.shuffle)
    
    output_file = csv_file.with_name(csv_file.stem + '_curated.m3u')
    write_m3u(ordered_clusters, output_file, csv_file.parent)
    
    print(f"Curated M3U playlist created: {output_file}")
    print_summary(ordered_clusters)

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Generate a curated M3U playlist from a CSV file.")
    parser.add_argument("csv_file", type=str, help="Path to the input CSV file")
    parser.add_argument("-loved_csv", type=str, help="Path to the _loved.csv file (optional)", default=None)
    parser.add_argument("-shuffle", action="store_true", help="Curate the tracks within each cluster based on audio features")
    args = parser.parse_args()
    
    generate_curated_m3u(SimpleNamespace(
        csv_file=sanitize_path(args.csv_file),
        loved_csv=sanitize_path(args.loved_csv) if args.loved_csv else None,
        shuffle=args.shuffle
    ))
