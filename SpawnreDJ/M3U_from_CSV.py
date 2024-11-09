# M3U_from_CSV.py

import pandas as pd
import random
import logging
import numpy as np
import csv
import json
from types import SimpleNamespace
from typing import Optional, List, Dict
from pathlib import Path
from SpawnreDJ.dic_spawnre import genre_mapping, subgenre_to_parent  # Updated import

# Initialize logger without configuring it
logger = logging.getLogger(__name__)

# Define feature columns and initial tolerances
feature_columns = [
    'danceability', 'energy', 'loudness', 'speechiness', 
    'acousticness', 'instrumentalness', 'liveness', 'valence', 'tempo'
]
initial_tolerances = {col: 0.1 if col not in ['loudness', 'tempo'] else 5.0 for col in feature_columns}

# Create a reverse mapping: genre_name -> genre_code
genre_name_to_code = {
    details['Genre'].lower(): key
    for key, details in genre_mapping.items()
    if details['Genre']
}

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

def get_related_genres(current_genre: str, genre_mapping: Dict[str, Dict], genre_name_to_code: Dict[str, str]) -> List[str]:
    """
    Given the current genre, return a list of related genres based on the 'Related' field.
    """
    # Find the code(s) for the current genre
    current_genre_lower = current_genre.lower()
    current_keys = [key for key, details in genre_mapping.items() if details['Genre'].lower() == current_genre_lower]
    related_genres = []
    for key in current_keys:
        related_keys = genre_mapping[key].get('Related', [])
        for related_key in related_keys:
            related_genre = genre_mapping.get(related_key, {}).get('Genre', '').lower()
            if related_genre:
                related_genres.append(related_genre)
    return related_genres

def create_clusters(df: pd.DataFrame, loved_csv: Optional[Path] = None, loved_categories: Optional[List[str]] = None) -> Dict[str, List[str]]:
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
    
    # Create a unique identifier for each track with standardized formatting
    features_df['unique_track'] = (
        features_df['track']
        .str.strip()
        .str.lower()
        .str.replace(' ', '-', regex=False)
        .str.replace('_', '-', regex=False)
        + "_"
        + features_df['artist']
        .str.strip()
        .str.lower()
        .str.replace(' ', '-', regex=False)
        .str.replace('_', '-', regex=False)
    )
    
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
        unique_current_track = f"{current_track.strip().lower().replace(' ', '-').replace('_', '-')}_{current_artist.strip().lower().replace(' ', '-').replace('_', '-')}"
    
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
            unique_candidate_track = f"{candidate_track.strip().lower().replace(' ', '-').replace('_', '-')}_{candidate_artist.strip().lower().replace(' ', '-').replace('_', '-')}"
    
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

def order_clusters_by_relationships(
    clusters: Dict[str, List[str]],
    genre_mapping: Dict[str, Dict],
    subgenre_to_parent: Dict[str, str]
) -> List[str]:
    """
    Order genre clusters starting with the largest cluster and
    sequencing based on related genres.
    
    Returns a list of genres in the desired order.
    """
    # Calculate the number of tracks in each genre cluster
    cluster_counts = {genre: len(tracks) for genre, tracks in clusters.items()}
    
    # Sort genres by descending number of tracks
    sorted_genres = sorted(cluster_counts.items(), key=lambda x: x[1], reverse=True)
    
    # Initialize ordered list with the largest cluster
    if not sorted_genres:
        return []
    
    ordered_genres = [sorted_genres[0][0]]
    used_genres = set(ordered_genres)
    
    # Function to find the next genre based on related genres
    def find_next_genre(current_genre, clusters, used_genres):
        related = get_related_genres(current_genre, genre_mapping, genre_name_to_code)
        for rel_genre in related:
            if rel_genre in clusters and rel_genre not in used_genres:
                return rel_genre
        return None
    
    current_genre = ordered_genres[0]
    
    while len(used_genres) < len(clusters):
        next_genre = find_next_genre(current_genre, clusters, used_genres)
        if next_genre:
            ordered_genres.append(next_genre)
            used_genres.add(next_genre)
            current_genre = next_genre
        else:
            # If no related genre is found, pick the next largest unused genre
            remaining = sorted_genres.copy()
            for genre, count in remaining:
                if genre not in used_genres:
                    ordered_genres.append(genre)
                    used_genres.add(genre)
                    current_genre = genre
                    break
            else:
                break  # No remaining genres
    return ordered_genres

def save_genre_order(config_path='genre_order.json', preferred_genre_order: Optional[List[str]] = None):
    """
    Save the preferred genre order to a JSON configuration file.
    """
    if preferred_genre_order:
        try:
            # Store genre names in their original (title case) format for readability
            config = {'preferred_genre_order': [genre.replace('-', ' ').title() for genre in preferred_genre_order]}
            with open(config_path, 'w') as f:
                json.dump(config, f, indent=4)
            logger.info(f"Preferred genre order saved to '{config_path}'.")
            print(f"Preferred genre order saved to '{config_path}'.")
        except Exception as e:
            logger.error(f"Failed to save genre order to '{config_path}': {e}")
            print(f"Error: Failed to save genre order to '{config_path}'. Check logs for details.")

def load_saved_genre_order(config_path='genre_order.json') -> Optional[List[str]]:
    """
    Load the preferred genre order from a JSON configuration file.
    Returns a list of genres or None if not found or invalid.
    """
    config_file = Path(config_path)
    if config_file.is_file():
        try:
            with open(config_path, 'r') as f:
                config = json.load(f)
            preferred_order = config.get('preferred_genre_order', None)
            if preferred_order and isinstance(preferred_order, list):
                # Standardize genre names: lowercase and strip whitespace
                preferred_order = [genre.lower().strip() for genre in preferred_order]
                logger.info(f"Loaded saved genre order from '{config_path}'.")
                return preferred_order
            else:
                logger.warning(f"'preferred_genre_order' not found or invalid in '{config_path}'.")
                return None
        except Exception as e:
            logger.error(f"Error reading genre order from '{config_path}': {e}")
            return None
    else:
        logger.info(f"No saved genre order found at '{config_path}'.")
        return None

def write_m3u(ordered_clusters: List[tuple], output_file: Path, root_directory: Path, path_prefix: str = '../') -> None:
    """
    Write the ordered clusters to an M3U playlist file.
    """
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
    print(f"Curated M3U playlist written to '{output_file}'.")

def print_summary(ordered_clusters: List[tuple]) -> None:
    print("\nClusters summary (in M3U order):")
    for genre, tracks in ordered_clusters:
        print(f"- {genre}: {len(tracks)} tracks")

def format_genre_name(genre: str) -> str:
    """
    Format genre names to title case, handling special characters appropriately.
    Example: "rock & roll" -> "Rock & Roll"
    """
    return ' '.join(word.capitalize() for word in genre.split(' '))

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
    
    if not clusters:
        logger.error("No clusters found. Exiting playlist generation.")
        return
    
    # Order clusters by relationships
    ordered_genres = order_clusters_by_relationships(clusters, genre_mapping, subgenre_to_parent)
    
    if not ordered_genres:
        logger.error("Failed to order genres. Exiting playlist generation.")
        return
    
    # Create ordered_clusters list based on ordered_genres
    ordered_clusters = []
    for genre in ordered_genres:
        tracks = clusters.get(genre, [])
        if not tracks:
            continue  # Skip empty clusters
        
        if args.shuffle and features_df is not None:
            curated_paths = curate_cluster(tracks.copy(), df, features_df)
        else:
            curated_paths = tracks.copy()
            random.shuffle(curated_paths)
        
        ordered_clusters.append((genre, curated_paths))
    
    # Present summary to the user
    print("\nClusters summary (in current M3U order):")
    for genre, tracks in ordered_clusters:
        print(f"- {genre}: {len(tracks)} tracks")
    
    # Generate and print the comma-separated Clusters list
    clusters_list = ", ".join([format_genre_name(genre) for genre, _ in ordered_clusters])
    print(f"\nClusters list: {clusters_list}")
    
    # Prompt user for confirmation or modification
    user_choice = input("\nWould you like to modify the genre order? (y/n): ").strip().lower()
    if user_choice == 'y':
        # Allow user to input a new genre order or recall saved order
        print("\nEnter your preferred genre order, separated by commas.")
        print("Ensure that all genres are listed and spelled correctly.")
        print("Leave blank to recall a previously saved genre order.")
        print("Or enter the path to a different genre order JSON file.")
        print("Example: classic rock, alternative rock, pop rock, indie pop")
        new_order_input = input("Preferred Genre Order: ").strip().lower()
        
        if not new_order_input:
            # User chose to recall the saved genre order
            saved_order = load_saved_genre_order()
            if saved_order:
                # Validate that saved genres exist in current clusters
                valid_saved_order = [genre for genre in saved_order if genre in clusters]
                if not valid_saved_order:
                    print("Saved genre order does not match current playlist genres. Proceeding with the existing order.")
                else:
                    # Reorder based on saved order
                    ordered_genres_user = valid_saved_order.copy()
                    remaining_genres = [genre for genre in ordered_genres if genre not in ordered_genres_user]
                    ordered_genres_user.extend(remaining_genres)
                    
                    # Recreate ordered_clusters based on saved order
                    ordered_clusters = []
                    for genre in ordered_genres_user:
                        tracks = clusters.get(genre, [])
                        if not tracks:
                            continue  # Skip empty clusters
                        
                        if args.shuffle and features_df is not None:
                            curated_paths = curate_cluster(tracks.copy(), df, features_df)
                        else:
                            curated_paths = tracks.copy()
                            random.shuffle(curated_paths)
                        
                        ordered_clusters.append((genre, curated_paths))
                    
                    # Present updated summary
                    print("\nUpdated Clusters summary (using saved genre order):")
                    for genre, tracks in ordered_clusters:
                        print(f"- {genre}: {len(tracks)} tracks")
                    
                    # Generate and print the updated comma-separated Clusters list
                    updated_clusters_list = ", ".join([format_genre_name(genre) for genre, _ in ordered_clusters])
                    print(f"\nClusters list: {updated_clusters_list}")
                    
                    # Proceed to write the M3U file
                    output_file = csv_file.with_name(csv_file.stem + '_curated.m3u')
                    write_m3u(ordered_clusters, output_file, csv_file.parent)
                    
                    print(f"\nCurated M3U playlist created: {output_file}")
                    print_summary(ordered_clusters)
                    return  # Exit after using saved order
            else:
                print("No saved genre order found. Please enter a new genre order.")
        
        # Check if the user entered a path to a JSON file
        elif new_order_input.endswith('.json'):
            json_path = Path(new_order_input)
            if json_path.is_file():
                try:
                    with open(json_path, 'r') as f:
                        config = json.load(f)
                    new_preferred_order = config.get('preferred_genre_order', None)
                    if new_preferred_order and isinstance(new_preferred_order, list):
                        # Standardize genre names
                        new_preferred_order = [genre.lower().strip() for genre in new_preferred_order]
                        
                        # Validate that entered genres exist in clusters
                        valid_genres = [genre for genre in new_preferred_order if genre in clusters]
                        invalid_genres = [genre for genre in new_preferred_order if genre not in clusters]
                        
                        if invalid_genres:
                            print(f"Warning: The following genres are not present in your playlist and will be ignored: {', '.join(invalid_genres)}")
                        
                        if valid_genres:
                            # Reorder based on JSON file
                            ordered_genres_user = valid_genres.copy()
                            remaining_genres = [genre for genre in ordered_genres if genre not in ordered_genres_user]
                            ordered_genres_user.extend(remaining_genres)
                            
                            # Recreate ordered_clusters based on JSON order
                            ordered_clusters = []
                            for genre in ordered_genres_user:
                                tracks = clusters.get(genre, [])
                                if not tracks:
                                    continue  # Skip empty clusters
                                
                                if args.shuffle and features_df is not None:
                                    curated_paths = curate_cluster(tracks.copy(), df, features_df)
                                else:
                                    curated_paths = tracks.copy()
                                    random.shuffle(curated_paths)
                                
                                ordered_clusters.append((genre, curated_paths))
                            
                            # Present updated summary
                            print("\nUpdated Clusters summary (using specified JSON genre order):")
                            for genre, tracks in ordered_clusters:
                                print(f"- {genre}: {len(tracks)} tracks")
                            
                            # Generate and print the updated comma-separated Clusters list
                            updated_clusters_list = ", ".join([format_genre_name(genre) for genre, _ in ordered_clusters])
                            print(f"\nClusters list: {updated_clusters_list}")
                            
                            # Offer to save the new order
                            save_choice = input("\nWould you like to save this new genre order for future use? (y/n): ").strip().lower()
                            if save_choice == 'y':
                                save_genre_order(preferred_genre_order=new_preferred_order)
                            
                            # Proceed to write the M3U file
                            output_file = csv_file.with_name(csv_file.stem + '_curated.m3u')
                            write_m3u(ordered_clusters, output_file, csv_file.parent)
                            
                            print(f"\nCurated M3U playlist created: {output_file}")
                            print_summary(ordered_clusters)
                            return  # Exit after using specified JSON order
                        else:
                            print("No valid genres found in the specified JSON file. Proceeding with the existing order.")
                    else:
                        print("Invalid genre order format in the specified JSON file. Please ensure it contains a 'preferred_genre_order' list.")
                except Exception as e:
                    logger.error(f"Error loading genre order from '{json_path}': {e}")
                    print(f"Error: Could not load genre order from '{json_path}'. Please check the file and try again.")
            else:
                print(f"The specified JSON file '{json_path}' does not exist. Please enter a valid path.")
        
        # User entered a new genre order manually
        else:
            # Process the manually entered genre order
            new_preferred_order = [genre.strip().lower() for genre in new_order_input.split(",") if genre.strip()]
            
            if new_preferred_order:
                # Validate that entered genres exist in clusters
                valid_genres = [genre for genre in new_preferred_order if genre in clusters]
                invalid_genres = [genre for genre in new_preferred_order if genre not in clusters]
                
                if invalid_genres:
                    print(f"Warning: The following genres are not present in your playlist and will be ignored: {', '.join(invalid_genres)}")
                
                if valid_genres:
                    # Reorder based on user input
                    ordered_genres_user = valid_genres.copy()
                    remaining_genres = [genre for genre in ordered_genres if genre not in ordered_genres_user]
                    ordered_genres_user.extend(remaining_genres)
                    
                    # Recreate ordered_clusters based on user-defined order
                    ordered_clusters = []
                    for genre in ordered_genres_user:
                        tracks = clusters.get(genre, [])
                        if not tracks:
                            continue  # Skip empty clusters
                        
                        if args.shuffle and features_df is not None:
                            curated_paths = curate_cluster(tracks.copy(), df, features_df)
                        else:
                            curated_paths = tracks.copy()
                            random.shuffle(curated_paths)
                        
                        ordered_clusters.append((genre, curated_paths))
                    
                    # Present updated summary
                    print("\nUpdated Clusters summary (in new M3U order):")
                    for genre, tracks in ordered_clusters:
                        print(f"- {genre}: {len(tracks)} tracks")
                    
                    # Generate and print the updated comma-separated Clusters list
                    updated_clusters_list = ", ".join([format_genre_name(genre) for genre, _ in ordered_clusters])
                    print(f"\nClusters list: {updated_clusters_list}")
                    
                    # Offer to save the new order
                    save_choice = input("\nWould you like to save this new genre order for future use? (y/n): ").strip().lower()
                    if save_choice == 'y':
                        save_genre_order(preferred_genre_order=new_preferred_order)
            else:
                print("No genre order entered. Proceeding with the existing order.")
    
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
