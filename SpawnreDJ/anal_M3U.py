# anal_M3U.py

import csv
import logging
import requests
import time
import random
from typing import List, Tuple, Dict, Any, Optional
from types import SimpleNamespace

from mutagen.mp4 import MP4
import spotipy
from spotipy.oauth2 import SpotifyClientCredentials
import musicbrainzngs

from pathlib import Path
from collections import Counter

# Suppress the MusicBrainz non-official JSON format warning
import warnings
warnings.filterwarnings("ignore", message="The json format is non-official and may change at any time")

from SpawnreDJ.dic_spawnre import genre_mapping

# Initialize module-specific logger
logger = logging.getLogger(__name__)

# Suppress DEBUG logs from third-party libraries
logging.getLogger('spotipy').setLevel(logging.INFO)
logging.getLogger('requests').setLevel(logging.INFO)
logging.getLogger('musicbrainzngs').setLevel(logging.INFO)


# Define genre synonyms and related genres
genre_synonyms = {
    'hiphop': 'hip-hop',
    'hip hop': 'hip-hop',
    'hip-hop/rap': 'hip-hop',
    'rap': 'hip-hop',
    'rhythm & blues': 'R&B',
    'rhythm and blues': 'R&B',
    'rock-n-roll': 'rock & roll',
    'rock and roll': 'rock & roll',
    'punk rock': 'punk',
    'alternative': 'alternative rock'
}

related_genre_map = {
    'funk rock': ['funk metal'],
    'alternative rock': ['alternative metal'],
    'metal': ['nu metal', 'thrash metal', 'thrash'],
}

# Initialize caches
spotify_genre_cache: Dict[str, Tuple[List[str], List[str]]] = {}
musicbrainz_genre_cache: Dict[str, List[str]] = {}

# Set up MusicBrainz user agent
musicbrainzngs.set_useragent("Spawn", "0.1", "spawn.id.0000@gmail.com")
musicbrainzngs.set_format("json")


def sanitize_path(path: str) -> Path:
    """
    Sanitize the input path by removing backslashes before spaces and normalizing the path.
    
    Args:
        path (str): The original path string input by the user.
        
    Returns:
        Path: The sanitized Path object.
    """
    # Replace escaped spaces (\ ) with regular spaces
    sanitized = path.replace('\\ ', ' ')
    
    # Additionally, handle other common escape characters if necessary
    # For example, replace double backslashes with single backslash
    sanitized = sanitized.replace('\\\\', '\\')
    
    # Create a Path object and normalize it
    sanitized_path = Path(sanitized).expanduser().resolve()
    
    return sanitized_path

def generate_stats_csv(main_csv_path: Path, stats_csv_path: Path, genre_mapping: Dict[str, Dict[str, str]]) -> None:
# NOT WORKING PROPERLY - DEBUG NEEDED!!!
    """
    Generate a stats CSV based on the main CSV file.
    Args:
        main_csv_path (Path): Path to the main CSV file.
        stats_csv_path (Path): Path where the stats CSV should be saved.
        genre_mapping (Dict[str, Dict[str, str]]): Genre mapping dictionary for hex values.
    """
    logger = logging.getLogger(__name__)
    logger.info(f"Generating stats from {main_csv_path}")

    try:
        total_tracks = 0
        tracks_with_genres = 0
        genre_counts = {}

        # Read the main CSV file to calculate stats
        with main_csv_path.open('r', newline='', encoding='utf-8') as csvfile:
            reader = csv.DictReader(csvfile)
            if 'spawnre' not in reader.fieldnames:
                logger.error("The 'spawnre' column is missing from the main CSV file.")
                return
            
            for row in reader:
                total_tracks += 1
                spawnre_raw = row.get('spawnre', '').strip("[]")
                
                # Log the raw `spawnre` data for each row
                logger.debug(f"Raw 'spawnre' data for row: {spawnre_raw}")
                
                # Check if spawnre data is empty or improperly formatted
                if not spawnre_raw:
                    logger.warning(f"No genre data found for track in row: {row}")
                    continue
                
                # Split the data correctly and handle any edge cases
                spawnre = [genre.strip(" '\"") for genre in spawnre_raw.split(",") if genre.strip()]
                
                # Log the parsed spawnre list for each track
                logger.debug(f"Parsed spawnre list for track: {spawnre}")
                
                if spawnre:
                    tracks_with_genres += 1
                    for genre in spawnre:
                        genre_counts[genre] = genre_counts.get(genre, 0) + 1
                else:
                    logger.warning(f"Empty or improperly formatted 'spawnre' for row: {row}")

        # Sort genres by count and retrieve their hex values from genre_mapping
        sorted_genres = sorted(
            [
                (genre, next((value['Hex'] for key, value in genre_mapping.items() if value['Genre'].lower() == genre.lower()), 'N/A'), count)
                for genre, count in genre_counts.items()
            ],
            key=lambda x: x[2],
            reverse=True
        )

        # Write the stats CSV
        with stats_csv_path.open('w', newline='', encoding='utf-8') as csvfile:
            writer = csv.writer(csvfile)
            writer.writerow(['Statistic', 'Count'])
            writer.writerow(['Total Tracks', total_tracks])
            writer.writerow(['Tracks with Genres', tracks_with_genres])
            writer.writerow([])  # Blank line
            writer.writerow(['Genre', 'Hex Value', 'Occurrences'])
            for genre, hex_value, count in sorted_genres:
                writer.writerow([genre, hex_value, count])

        logger.info(f"Stats CSV file created successfully: {stats_csv_path}")

    except Exception as e:
        logger.error(f"Error generating stats CSV: {e}")


def fetch_genre_lastfm(artist: str, track: str, api_key: str, retries: int = 3, delay: int = 5, timeout: int = 10) -> List[str]:
    url = f"https://ws.audioscrobbler.com/2.0/?method=track.getInfo&api_key={api_key}&artist={artist}&track={track}&format=json"
    for attempt in range(1, retries + 1):
        try:
            response = requests.get(url, timeout=timeout)
            response.raise_for_status()
            data = response.json()
            if 'track' in data and 'toptags' in data['track'] and 'tag' in data['track']['toptags']:
                genres = [tag['name'].lower() for tag in data['track']['toptags']['tag']]
                logger.debug(f"Last.FM genres extracted: {genres}")
                return genres
            else:
                logger.warning(f"No genres found for {artist} - {track} on Last.fm.")
                return []
        except requests.exceptions.HTTPError as e:
            logger.error(f"HTTP error while fetching Last.fm genres: {e}")
        except requests.exceptions.Timeout:
            logger.warning(f"Timeout occurred. Retrying ({attempt}/{retries})...")
        except requests.exceptions.RequestException as e:
            logger.error(f"Request exception: {e}")
            break
        time.sleep(delay)
    return []


def get_spotify_genres(artist_name: str, sp: spotipy.Spotify, retries: int = 3, delay: int = 5) -> Tuple[List[str], List[str]]:
    if artist_name in spotify_genre_cache:
        logger.debug(f"Spotify genres for '{artist_name}' fetched from cache.")
        return spotify_genre_cache[artist_name]

    for attempt in range(1, retries + 1):
        try:
            results = sp.search(q='artist:' + artist_name, type='artist')
            artists = results['artists']['items']
            if artists:
                artist = artists[0]
                genres = artist['genres'][:5]  # Limit to 5 genres
                spotify_genre_cache[artist_name] = (genres, [])
                logger.debug(f"Spotify genres extracted: {genres}")
                return genres, []
            else:
                logger.warning(f"No Spotify genres found for artist: {artist_name}")
                return [], []
        except spotipy.exceptions.SpotifyException as e:
            if e.http_status == 429:
                retry_after = int(e.headers.get('Retry-After', 60))
                jitter = random.uniform(0, 1)
                wait_time = retry_after + jitter
                logger.warning(f"Rate limit exceeded. Waiting for {wait_time:.2f} seconds.")
                time.sleep(wait_time)
            else:
                logger.error(f"Spotify API error: {e}. Retrying ({attempt}/{retries})...")
                time.sleep(delay)
        except requests.exceptions.RequestException as e:
            logger.error(f"Spotify request failed: {e}. Retrying ({attempt}/{retries})...")
            time.sleep(delay)
    return [], []


def get_musicbrainz_genres(artist_name: str) -> List[str]:
    if artist_name in musicbrainz_genre_cache:
        logger.debug(f"MusicBrainz genres for '{artist_name}' fetched from cache.")
        return musicbrainz_genre_cache[artist_name]

    logger.info(f"Fetching genres from MusicBrainz for artist: {artist_name}")

    try:
        result = musicbrainzngs.search_artists(artist=artist_name, limit=1)
        if 'artists' in result and result['artists']:
            artist_data = result['artists'][0]
            tags = artist_data.get('tags', [])
            genre_names = [tag['name'].lower() for tag in tags]
            musicbrainz_genre_cache[artist_name] = genre_names[:5]
            logger.debug(f"MusicBrainz genres extracted: {genre_names[:5]}")
            return genre_names[:5]
        else:
            logger.warning(f"No genre tags found for artist: {artist_name} on MusicBrainz.")
    except musicbrainzngs.WebServiceError as e:
        logger.error(f"MusicBrainz API request failed: {e}")
    return []


def normalize_genre(genre: str, related_genre_map: Dict[str, List[str]], genre_synonyms: Dict[str, str], genre_mapping: Dict[str, Dict[str, str]]) -> str:
    """
    Normalize genre using related_genre_map and genre_synonyms.
    """
    genre_lower = genre.lower()

    # Apply synonyms
    if genre_lower in genre_synonyms:
        genre_lower = genre_synonyms[genre_lower]

    # Apply related genre normalization
    for base_genre, related_genres in related_genre_map.items():
        if genre_lower in related_genres:
            genre_lower = base_genre
            break

    # Verify against genre_mapping
    if not any(value['Genre'].lower() == genre_lower for value in genre_mapping.values()):
        logger.debug(f"Genre '{genre_lower}' not found in genre_mapping.")
    else:
        logger.debug(f"Normalized genre: {genre_lower}")

    return genre_lower


def combine_and_prioritize_genres_refined(
    embedded_genre: str, 
    last_fm_genres: List[str], 
    spotify_genres: List[str], 
    musicbrainz_genres: List[str], 
    related_genre_map: Dict[str, List[str]], 
    genre_mapping: Dict[str, Dict[str, str]], 
    genre_synonyms: Dict[str, str], 
    artist_name: str
) -> List[str]:
    genre_count: Dict[str, int] = {}
    all_genres = [embedded_genre] + last_fm_genres + spotify_genres + musicbrainz_genres

    logger.debug(f"Initial combined genres: {all_genres}")

    for genre in all_genres:
        if genre:
            normalized_genre = normalize_genre(genre, related_genre_map, genre_synonyms, genre_mapping)
            genre_count[normalized_genre] = genre_count.get(normalized_genre, 0) + 1

    multi_source_genres = [genre for genre, count in genre_count.items() if count > 1]
    single_source_genres = [genre for genre, count in genre_count.items() if count == 1]

    logger.debug(f"Multi-source genres: {multi_source_genres}")
    logger.debug(f"Single-source genres: {single_source_genres}")

    combined_genres = multi_source_genres[:5]
    single_source_filtered = [
        genre for genre in single_source_genres
        if genre.lower() != artist_name.lower() and any(value['Genre'].lower() == genre.lower() for value in genre_mapping.values())
    ]
    combined_genres += single_source_filtered[:5 - len(combined_genres)]

    combined_genres = combined_genres[:5]
    logger.debug(f"Final combined genres: {combined_genres}")

    return combined_genres


def find_closest_genre_matches(genres: List[str], genre_mapping: Dict[str, Dict[str, str]], artist_name: str) -> Tuple[List[str], str]:
    matched_genres = []
    spawnre_hex = "x"

    rock_related_genres = {
        'funk': 'funk rock',
        'piano': 'piano rock',
        'folk': 'folk rock',
        'pop': 'pop rock',
        'country': 'country rock',
        'blues': 'blues rock',
        'metal': 'metal'
    }

    logger.debug(f"Initial genres: {genres}")

    if any('rock' in genre.lower() for genre in genres):
        matched_genres.append('rock')

    if 'rock' in matched_genres:
        for genre in genres:
            genre_lower = genre.lower()
            for sub_genre_key, sub_genre_value in rock_related_genres.items():
                if sub_genre_key in genre_lower and sub_genre_value not in matched_genres:
                    matched_genres.append(sub_genre_value)

    for genre in genres:
        genre_lower = genre.lower()
        if genre_lower and genre_lower not in matched_genres:
            for key, value in genre_mapping.items():
                if genre_lower == value['Genre'].lower():
                    matched_genres.append(value['Genre'])
                    if len(matched_genres) == 5:
                        break
        if len(matched_genres) == 5:
            break

    matched_genres.sort(
        key=lambda g: next((idx for idx, (k, v) in enumerate(genre_mapping.items()) if v['Genre'].lower() == g.lower()), len(genre_mapping))
    )

    matched_genres = matched_genres[:5]

    for genre in matched_genres:
        for key, value in genre_mapping.items():
            if value['Genre'].lower() == genre.lower():
                hex_part = value['Hex'][2:].zfill(2)
                spawnre_hex += hex_part
                break
        if len(spawnre_hex) >= 10:
            break

    spawnre_hex = spawnre_hex[:10]
    logger.debug(f"Matched genres: {matched_genres}, Spawnre Hex: {spawnre_hex}")

    return matched_genres, spawnre_hex


def determine_format_using_metadata(track_name: str, artist_name: str, file_path: Path) -> str:
    """
    Determine the format of the #EXTINF line based on embedded metadata.
    Returns 'Artist - Track', 'Track - Artist', or 'Unknown'.
    """
    try:
        audio = MP4(str(file_path))
        embedded_artist_list = audio.tags.get('\xa9ART', [''])
        embedded_artist = embedded_artist_list[0].strip().lower() if embedded_artist_list else ''

        embedded_track_list = audio.tags.get('\xa9nam', [''])
        embedded_track = embedded_track_list[0].strip().lower() if embedded_track_list else ''

        # Compare metadata with provided track and artist names
        if embedded_artist == artist_name.lower() and embedded_track == track_name.lower():
            return 'Artist - Track'
        elif embedded_artist == track_name.lower() and embedded_track == artist_name.lower():
            return 'Track - Artist'
        else:
            return 'Unknown'
    except Exception as e:
        logger.error(f"Error determining format using metadata for {file_path}: {e}")
        return 'Unknown'


def parse_m3u_for_loved(m3u_file: Path, music_directory: Path) -> set:
    """
    Read an M3U file and return a set of absolute, normalized paths.
    Resolves relative paths based on the provided music_directory.
    """
    loved_paths = set()
    if m3u_file.exists():
        with m3u_file.open('r', encoding='utf-8') as file:
            for line in file:
                line = line.strip()
                if not line.startswith('#') and line:
                    # Resolve relative paths to absolute paths
                    track_path = (music_directory / line).resolve() if not Path(line).is_absolute() else Path(line).resolve()
                    # Normalize and lowercase the path for consistent comparison
                    normalized_path = track_path.as_posix().lower()
                    loved_paths.add(normalized_path)
    else:
        logger.warning(f"Loved M3U file '{m3u_file}' does not exist.")
    return loved_paths


def process_m3u_with_loved(args: Any, loved_tracks: set, loved_albums: set, loved_artists: set) -> None:
    """
    Process the main playlist CSV and append loved metadata.
    """
    # Determine input and output CSV paths based on post-processing
    if hasattr(args, 'post') and args.post and args.csv_file:
        input_csv_path = Path(args.csv_file)
    else:
        input_csv_path = Path(args.m3u_file).with_suffix('.csv')
    output_csv_path = input_csv_path.with_name(input_csv_path.stem + '_loved.csv')

    try:
        with input_csv_path.open('r', newline='', encoding='utf-8') as csvfile:
            reader = csv.DictReader(csvfile)
            fieldnames = reader.fieldnames + ['loved_tracks', 'loved_albums', 'loved_artists']
            data = list(reader)  # Store all the data in a list for processing

        with output_csv_path.open('w', newline='', encoding='utf-8') as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()

            for track_data in data:
                # Normalize the file path for comparison
                file_path = Path(track_data.get('file_path', '')).as_posix().lower()
                normalized_file_path = Path(file_path)

                # Derive album and artist directories
                album_dir = normalized_file_path.parent
                album_dir_normalized = album_dir.as_posix().lower()

                artist_dir = album_dir.parent
                artist_dir_normalized = artist_dir.as_posix().lower()

                # Check if the track, album, or artist is "loved"
                is_loved_track = 'yes' if file_path in loved_tracks else 'no'
                is_loved_album = 'yes' if album_dir_normalized in loved_albums else 'no'
                is_loved_artist = 'yes' if artist_dir_normalized in loved_artists else 'no'

                # Add the loved metadata
                track_data['loved_tracks'] = is_loved_track
                track_data['loved_albums'] = is_loved_album
                track_data['loved_artists'] = is_loved_artist

                # Write the updated row to the new CSV file
                writer.writerow(track_data)

        logger.info(f"Loved metadata CSV file created successfully: {output_csv_path}")

    except Exception as e:
        logger.error(f"Error processing loved metadata: {e}")


def fetch_audio_features_to_csv(data: List[Dict[str, Any]], sp: spotipy.Spotify, output_csv_path: Path, retries: int = 5) -> None:
    """
    Fetch audio features for tracks in batches and write the results to a separate CSV file.
    """
    features_csv_path = output_csv_path.with_name(output_csv_path.stem + '_features.csv')
    main_fieldnames = [
        'artist', 'album', 'track', 'year', 'spawnre', 'spawnre_hex',
        'musicbrainz_artist_ID', 'musicbrainz_release_group_ID', 'musicbrainz_track_ID',
        'spotify_artist_ID', 'spotify_track_ID',
        'file_duration_ms', 'spotify_duration_ms', 
        'embedded_genre', 'spawnre_tag'
    ]
    audio_feature_columns = [
        'danceability', 'energy', 'key', 'loudness',
        'mode', 'speechiness', 'acousticness', 'instrumentalness',
        'liveness', 'valence', 'tempo', 'duration_ms', 'time_signature'
    ]
    features_fieldnames = main_fieldnames + audio_feature_columns

    # Initialize the features CSV with headers
    try:
        with features_csv_path.open('w', newline='', encoding='utf-8') as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=features_fieldnames)
            writer.writeheader()
        logger.info(f"Initialized features CSV file: {features_csv_path}")
    except Exception as e:
        logger.error(f"Error initializing features CSV file '{features_csv_path}': {e}")
        return

    # Collect all Spotify Track IDs
    track_ids = [track_data['spotify_track_ID'] for track_data in data if track_data.get('spotify_track_ID')]
    logger.info(f"Total Spotify Track IDs to fetch: {len(track_ids)}")

    if not track_ids:
        logger.warning("No Spotify Track IDs found. Skipping audio features fetching.")
        return

    batch_size = 50
    track_id_batches = [track_ids[i:i + batch_size] for i in range(0, len(track_ids), batch_size)]

    logger.info(f"Fetching audio features for {len(track_ids)} tracks in batches of {batch_size}...")

    for batch_num, batch in enumerate(track_id_batches, start=1):
        logger.info(f"Processing batch {batch_num}/{len(track_id_batches)} with {len(batch)} track IDs")
        try:
            features = sp.audio_features(batch)
            if features:
                for feature in features:
                    if feature:
                        spotify_track_id = feature.get('id', '')
                        track_data = next((td for td in data if td.get('spotify_track_ID') == spotify_track_id), None)
                        if track_data:
                            feature_row = {key: track_data.get(key, '') for key in main_fieldnames}
                            feature_row.update({
                                'danceability': feature.get('danceability', ''),
                                'energy': feature.get('energy', ''),
                                'key': feature.get('key', ''),
                                'loudness': feature.get('loudness', ''),
                                'mode': feature.get('mode', ''),
                                'speechiness': feature.get('speechiness', ''),
                                'acousticness': feature.get('acousticness', ''),
                                'instrumentalness': feature.get('instrumentalness', ''),
                                'liveness': feature.get('liveness', ''),
                                'valence': feature.get('valence', ''),
                                'tempo': feature.get('tempo', ''),
                                'duration_ms': feature.get('duration_ms', ''),
                                'time_signature': feature.get('time_signature', '')
                            })
                            with features_csv_path.open('a', newline='', encoding='utf-8') as csvfile:
                                writer = csv.DictWriter(csvfile, fieldnames=features_fieldnames)
                                writer.writerow(feature_row)
                            logger.debug(f"Fetched audio features for Track ID: {spotify_track_id}")
            else:
                logger.warning(f"No audio features found for batch {batch_num}.")
        except spotipy.exceptions.SpotifyException as e:
            if e.http_status == 429:
                retry_after = int(e.headers.get('Retry-After', 60))
                jitter = random.uniform(0, 1)
                wait_time = retry_after + jitter
                logger.warning(f"Rate limit exceeded. Waiting for {wait_time:.2f} seconds.")
                time.sleep(wait_time)
                # Retry the same batch after waiting
                try:
                    features = sp.audio_features(batch)
                    if features:
                        for feature in features:
                            if feature:
                                spotify_track_id = feature.get('id', '')
                                track_data = next((td for td in data if td.get('spotify_track_ID') == spotify_track_id), None)
                                if track_data:
                                    feature_row = {key: track_data.get(key, '') for key in main_fieldnames}
                                    feature_row.update({
                                        'danceability': feature.get('danceability', ''),
                                        'energy': feature.get('energy', ''),
                                        'key': feature.get('key', ''),
                                        'loudness': feature.get('loudness', ''),
                                        'mode': feature.get('mode', ''),
                                        'speechiness': feature.get('speechiness', ''),
                                        'acousticness': feature.get('acousticness', ''),
                                        'instrumentalness': feature.get('instrumentalness', ''),
                                        'liveness': feature.get('liveness', ''),
                                        'valence': feature.get('valence', ''),
                                        'tempo': feature.get('tempo', ''),
                                        'duration_ms': feature.get('duration_ms', ''),
                                        'time_signature': feature.get('time_signature', '')
                                    })
                                    with features_csv_path.open('a', newline='', encoding='utf-8') as csvfile:
                                        writer = csv.DictWriter(csvfile, fieldnames=features_fieldnames)
                                        writer.writerow(feature_row)
                                    logger.debug(f"Fetched audio features for Track ID: {spotify_track_id}")
                except Exception as e_retry:
                    logger.error(f"Failed to retry fetching audio features for batch {batch_num}: {e_retry}")
            else:
                logger.error(f"Spotify API error: {e}. Skipping batch {batch_num}/{len(track_id_batches)}.")
        except Exception as e:
            logger.error(f"Unexpected error while fetching audio features for batch {batch_num}: {e}")

        time.sleep(random.uniform(0.5, 1.5))  # Respectful delay between API calls

    logger.info("Audio features fetching complete.")


def populate_missing_spotify_ids(data: List[Dict[str, Any]], sp: spotipy.Spotify) -> None:
    """
    Populate the 'spotify_track_ID' for tracks missing it.
    """
    missing_ids = [track_data for track_data in data if not track_data.get('spotify_track_ID')]
    logger.info(f"Found {len(missing_ids)} tracks with missing Spotify Track IDs.")
    
    for track_data in missing_ids:
        artist = track_data.get('artist', '').strip()
        track = track_data.get('track', '').strip()
        if not artist or not track:
            logger.warning(f"Missing artist or track name for row: {track_data}")
            continue
        try:
            query = f"track:{track} artist:{artist}"
            result = sp.search(q=query, type='track', limit=1)
            if result['tracks']['items']:
                track_item = result['tracks']['items'][0]
                spotify_track_id = track_item['id']
                track_data['spotify_track_ID'] = spotify_track_id
                logger.info(f"Populated Spotify Track ID for '{artist} - {track}': {spotify_track_id}")
            else:
                logger.warning(f"No Spotify Track found for '{artist} - {track}'.")
        except spotipy.exceptions.SpotifyException as e:
            logger.error(f"Spotify API error for '{artist} - {track}': {e}")
        except Exception as e:
            logger.error(f"Unexpected error for '{artist} - {track}': {e}")

def fetch_musicbrainz_ids_from_api(artist_name: str, track_name: str, album_name: str) -> Dict[str, str]:
    """
    Fetch MusicBrainz artist, release group, and track IDs using the MusicBrainz API.
    Returns a dictionary with keys: 'artist_id', 'release_group_id', 'track_id'.
    """
    musicbrainz_ids = {'artist_id': '', 'release_group_id': '', 'track_id': ''}

    try:
        # Fetch artist ID
        artist_result = musicbrainzngs.search_artists(artist=artist_name, limit=1)
        if 'artists' in artist_result and artist_result['artists']:
            musicbrainz_ids['artist_id'] = artist_result['artists'][0].get('id', '')

        # Fetch release group ID - try searching by album alone if artist+album search fails
        if album_name:
            release_result = musicbrainzngs.search_release_groups(artist=artist_name, releasegroup=album_name, limit=1)
            if 'release-group-list' in release_result and release_result['release-group-list']:
                musicbrainz_ids['release_group_id'] = release_result['release-group-list'][0].get('id', '')
            elif not musicbrainz_ids['release_group_id']:  # Try searching only by album name
                release_result = musicbrainzngs.search_release_groups(releasegroup=album_name, limit=1)
                if 'release-group-list' in release_result and release_result['release-group-list']:
                    musicbrainz_ids['release_group_id'] = release_result['release-group-list'][0].get('id', '')

        # Fetch track ID - try different combinations if the first attempt fails
        if track_name:
            track_result = musicbrainzngs.search_recordings(artist=artist_name, recording=track_name, limit=1)
            if 'recording-list' in track_result and track_result['recording-list']:
                musicbrainz_ids['track_id'] = track_result['recording-list'][0].get('id', '')

        logger.info(f"Fetched MusicBrainz IDs via API for {artist_name} - {track_name}: {musicbrainz_ids}")

    except musicbrainzngs.WebServiceError as e:
        logger.error(f"MusicBrainz API request failed: {e}")

    return musicbrainz_ids


def analyze_m3u(
    m3u_file: str,
    music_directory: str,
    lastfm_api_key: str,
    spotify_client_id: str,
    spotify_client_secret: str,
    generate_stats: bool,
    fetch_features: bool,
    fetch_analysis: bool,
    post: bool = False,
    csv_file: Optional[str] = None,
    loved_tracks: Optional[str] = None,
    loved_albums: Optional[str] = None,
    loved_artists: Optional[str] = None
) -> List[Dict[str, Any]]:
    """
    Main function to parse and analyze M3U playlists.
    """
    # Sanitize input paths
    m3u_path = sanitize_path(m3u_file)
    music_dir_path = sanitize_path(music_directory)
    
    if post and csv_file:
        csv_path = sanitize_path(csv_file)
    else:
        csv_path = None

    if loved_tracks:
        loved_tracks_path = sanitize_path(loved_tracks)
    else:
        loved_tracks_path = None

    if loved_albums:
        loved_albums_path = sanitize_path(loved_albums)
    else:
        loved_albums_path = None

    if loved_artists:
        loved_artists_path = sanitize_path(loved_artists)
    else:
        loved_artists_path = None

    data: List[Dict[str, Any]] = []
    artist_spawnre_tags: Dict[str, str] = {}
    genre_counts: Dict[str, int] = {}
    artist_subgenre_count: Dict[str, Dict[str, int]] = {}
    stats = {'Total Tracks': 0, 'Tracks with Genres': 0}

    # Initialize Spotify client at the very beginning
    try:
        sp = spotipy.Spotify(
            auth_manager=SpotifyClientCredentials(
                client_id=spotify_client_id,
                client_secret=spotify_client_secret
            ),
            requests_timeout=30
        )
        logger.info("Spotify client initialized successfully.")
    except Exception as e:
        logger.error(f"Failed to initialize Spotify client: {e}")
        return []

    if post and csv_path:
        # Validate CSV path
        if not csv_path.is_file():
            logger.error(f"The existing CSV file '{csv_path}' is not a file or does not exist.")
            return []
        
        # Load existing CSV data
        try:
            logger.info(f"Loading existing CSV file: {csv_path}")
            with csv_path.open('r', encoding='utf-8') as csvfile:
                reader = csv.DictReader(csvfile)
                data = [row for row in reader]
                logger.info(f"Loaded {len(data)} tracks from the existing CSV.")
        except FileNotFoundError:
            logger.error(f"CSV file '{csv_path}' not found.")
            return []
        except Exception as e:
            logger.error(f"Error loading CSV file '{csv_path}': {e}")
            return []
        
        # Populate missing Spotify Track IDs
        populate_missing_spotify_ids(data, sp)
        
        # Set output_csv_path based on csv_file
        output_csv_path = csv_path
        logger.info(f"Output CSV path set to: {output_csv_path}")
    else:
        # Existing behavior: parse M3U and extract genres
        try:
            with m3u_path.open('r', encoding='utf-8') as file:
                lines = file.readlines()
            logger.info(f"Opened M3U file: {m3u_path}")
        except Exception as e:
            logger.error(f"Error reading M3U file '{m3u_path}': {e}")
            return []

        # Get total number of tracks in the M3U
        total_tracks = sum(1 for line in lines if line.strip() and not line.startswith('#'))
        logger.info(f"\nTotal number of tracks: {total_tracks}\n")

        track_counter = 0

        for i, line in enumerate(lines):
            line = line.strip()
            if line.startswith("#EXTINF"):
                track_counter += 1
                logger.info(f"\nTrack {track_counter} of {total_tracks}")

                parts = line.split(',', 1)
                if len(parts) < 2:
                    logger.warning(f"Invalid EXTINF line format: {line}")
                    continue
                track_info = parts[1].split(' - ')

                if len(track_info) < 2:
                    logger.warning(f"Invalid track info format: {parts[1]}")
                    continue

                if i + 1 >= len(lines):
                    logger.warning("No file path found for the last EXTINF line.")
                    continue
                file_line = lines[i + 1].strip()
                file_path = (music_dir_path / file_line).resolve()

                # Determine the format using metadata
                format_type = determine_format_using_metadata(track_info[1].strip(), track_info[0].strip(), file_path)

                if format_type == 'Track - Artist':
                    artist = track_info[1].strip()
                    track = track_info[0].strip()
                elif format_type == 'Artist - Track':
                    artist = track_info[0].strip()
                    track = track_info[1].strip()
                else:
                    # Default to 'Track - Artist' if unknown
                    artist = track_info[1].strip()
                    track = track_info[0].strip()

                # Initialize Spotify variables to avoid NameError
                spotify_artist_id = ''
                spotify_track_id = ''
                spotify_duration_ms = ''

                # Proceed with fetching metadata, genres, etc.
                try:
                    audio = MP4(str(file_path))
                    album_tag = audio.tags.get('\xa9alb', ['Unknown Album'])[0]

                    # Attempt to extract embedded genre
                    embedded_genre_list = audio.tags.get('\xa9gen', [''])
                    embedded_genre = embedded_genre_list[0].lower() if embedded_genre_list else ''
                    logger.info(f"Extracted embedded genre: {embedded_genre}")

                    # Attempt to get file duration in ms
                    file_duration_ms = int(audio.info.length * 1000) if hasattr(audio, 'info') and audio.info.length else 0
                    logger.info(f"Extracted file duration (ms): {file_duration_ms}")

                    # Extract MusicBrainz IDs with fallback to API if they remain blank
                    mb_artistid = (
                        audio.tags.get('----:com.apple.iTunes:MusicBrainz Artist Id', [b''])[0].decode('utf-8')
                        if '----:com.apple.iTunes:MusicBrainz Artist Id' in audio.tags else ''
                    )
                    mb_releasegroupid = (
                        audio.tags.get('----:com.apple.iTunes:MusicBrainz Release Group Id', [b''])[0].decode('utf-8')
                        if '----:com.apple.iTunes:MusicBrainz Release Group Id' in audio.tags else ''
                    )
                    mb_trackid = (
                        audio.tags.get('----:com.apple.iTunes:MusicBrainz Track Id', [b''])[0].decode('utf-8')
                        if '----:com.apple.iTunes:MusicBrainz Track Id' in audio.tags else ''
                    )

                    if not mb_artistid or not mb_releasegroupid or not mb_trackid:
                        musicbrainz_data = fetch_musicbrainz_ids_from_api(artist, track, album_tag)
                        mb_artistid = mb_artistid or musicbrainz_data.get('artist_id', '')
                        mb_releasegroupid = mb_releasegroupid or musicbrainz_data.get('release_group_id', '')
                        mb_trackid = mb_trackid or musicbrainz_data.get('track_id', '')

                    year = audio.tags.get('\xa9day', ['Unknown'])[0]
                    logger.info(f"Extracted MusicBrainz IDs for {file_path}: Artist ID = {mb_artistid}, Release Group ID = {mb_releasegroupid}, Track ID = {mb_trackid}")

                except Exception as e:
                    logger.error(f"Error reading metadata from {file_path}: {e}")
                    embedded_genre = ''
                    file_duration_ms = 0
                    mb_artistid = ''
                    mb_releasegroupid = ''
                    mb_trackid = ''
                    year = 'Unknown'

                # Fetch genres from various sources
                last_fm_genres = fetch_genre_lastfm(artist, track, lastfm_api_key)
                spotify_genres, _ = get_spotify_genres(artist, sp)
                musicbrainz_genres = get_musicbrainz_genres(artist)

                # Combine and prioritize genres based on multi-source validation
                combined_genres = combine_and_prioritize_genres_refined(
                    embedded_genre, 
                    last_fm_genres, 
                    spotify_genres,  
                    musicbrainz_genres,  
                    related_genre_map, 
                    genre_mapping, 
                    genre_synonyms, 
                    artist  
                )

                # Find closest genre matches
                closest_genres, spawnre_hex = find_closest_genre_matches(combined_genres, genre_mapping, artist)

                logger.info(f"Final matched genres: {closest_genres}")
                logger.info(f"Spawnre Hex: {spawnre_hex}")
                logger.debug("-----------------------")

                # Track sub-genres for the artist
                if artist not in artist_subgenre_count:
                    artist_subgenre_count[artist] = {}

                for genre in closest_genres:
                    genre_lower = genre.lower()
                    genre_counts[genre_lower] = genre_counts.get(genre_lower, 0) + 1

                    # Identify sub-genres
                    for key, value in genre_mapping.items():
                        if value['Genre'].lower() == genre_lower and key[1:] != "00":  # Ensure it's a sub-genre
                            artist_subgenre_count[artist][genre] = artist_subgenre_count[artist].get(genre, 0) + 1

                # Fetch Spotify Track ID and Audio Features
                try:
                    result = sp.search(q=f'track:{track} artist:{artist}', type='track', limit=1)
                    if result['tracks']['items']:
                        track_item = result['tracks']['items'][0]
                        spotify_track_id = track_item['id']
                        spotify_artist_id = track_item['artists'][0]['id']
                        spotify_duration_ms = track_item['duration_ms']
                        logger.info(f"Spotify Artist ID for {artist}: {spotify_artist_id}")
                        logger.info(f"Spotify Track ID for {track}: {spotify_track_id}")
                        logger.info(f"Spotify Duration: {spotify_duration_ms} ms")
                except Exception as e:
                    logger.error(f"Error fetching Spotify track ID for {track}: {e}")

                # Assign genres to their respective columns (up to 5)
                spotify_genre_columns = {f'spotify_genre_{i+1}': spotify_genres[i] if i < len(spotify_genres) else '' for i in range(5)}
                last_fm_genre_columns = {f'last_FM_genre_{i+1}': last_fm_genres[i] if i < len(last_fm_genres) else '' for i in range(5)}
                musicbrainz_genre_columns = {f'musicbrainz_genre_{i+1}': musicbrainz_genres[i] if i < len(musicbrainz_genres) else '' for i in range(5)}

                # Add track data for CSV
                track_dict = {
                    'artist': artist,
                    'album': album_tag,
                    'track': track,
                    'year': year,
                    'spawnre': closest_genres,
                    'spawnre_hex': spawnre_hex,
                    'musicbrainz_artist_ID': mb_artistid,
                    'musicbrainz_release_group_ID': mb_releasegroupid,
                    'musicbrainz_track_ID': mb_trackid,
                    'spotify_artist_ID': spotify_artist_id,
                    'spotify_track_ID': spotify_track_id,
                    'file_duration_ms': file_duration_ms,
                    'spotify_duration_ms': spotify_duration_ms,
                    'embedded_genre': embedded_genre,
                    'spawnre_tag': '',  # Placeholder
                    'file_path': file_path.as_posix()
                }

                # Merge genre columns
                track_dict.update(spotify_genre_columns)
                track_dict.update(last_fm_genre_columns)
                track_dict.update(musicbrainz_genre_columns)

                data.append(track_dict)

                stats['Total Tracks'] += 1
                if closest_genres:
                    stats['Tracks with Genres'] += 1

    # After data loading/parsing

    # Determine the most frequent sub-genre or main genre for each artist
    for artist, subgenre_counts in artist_subgenre_count.items():
        if subgenre_counts:
            most_frequent_subgenre = max(subgenre_counts, key=subgenre_counts.get)
            artist_spawnre_tags[artist] = most_frequent_subgenre
        else:
            main_genre_counts = {}
            for track_data in data:
                if track_data['artist'] == artist:
                    for genre in track_data['spawnre']:
                        for key, value in genre_mapping.items():
                            if value['Genre'].lower() == genre.lower() and key[1:] == "00":
                                main_genre_counts[genre] = main_genre_counts.get(genre, 0) + 1
            if main_genre_counts:
                most_frequent_main_genre = max(main_genre_counts, key=main_genre_counts.get)
                artist_spawnre_tags[artist] = most_frequent_main_genre
            else:
                artist_spawnre_tags[artist] = ''

    # Writing the main CSV if not in post mode
    if not post:
        output_csv_path = m3u_path.with_suffix('.csv')
        fieldnames = [
            'artist', 'album', 'track', 'year', 'spawnre', 'spawnre_hex',
            'musicbrainz_artist_ID', 'musicbrainz_release_group_ID', 'musicbrainz_track_ID',
            'spotify_artist_ID', 'spotify_track_ID',
            'file_duration_ms', 'spotify_duration_ms', 
            'embedded_genre', 'spawnre_tag', 'file_path',
            'spotify_genre_1', 'spotify_genre_2', 'spotify_genre_3', 'spotify_genre_4', 'spotify_genre_5',
            'last_FM_genre_1', 'last_FM_genre_2', 'last_FM_genre_3', 'last_FM_genre_4', 'last_FM_genre_5',
            'musicbrainz_genre_1', 'musicbrainz_genre_2', 'musicbrainz_genre_3', 'musicbrainz_genre_4', 'musicbrainz_genre_5'
        ]

        try:
            with output_csv_path.open('w', newline='', encoding='utf-8') as csvfile:
                writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                writer.writeheader()

                for track_data in data:
                    track_data['spawnre_tag'] = artist_spawnre_tags.get(track_data['artist'], '')
                    filtered_track_data = {key: track_data.get(key, '') for key in fieldnames}
                    writer.writerow(filtered_track_data)

            logger.info(f"\nMain CSV file created successfully: {output_csv_path}")
        except Exception as e:
            logger.error(f"Error writing main CSV file: {e}")

    # Writing stats CSV if requested
    if generate_stats:
        stats_csv_path = m3u_path.with_stem(m3u_path.stem + '_stats').with_suffix('.csv')
        generate_stats_csv(main_csv_path=output_csv_path, stats_csv_path=stats_csv_path, genre_mapping=genre_mapping)
        try:
            with stats_csv_path.open('w', newline='', encoding='utf-8') as csvfile:
                writer = csv.writer(csvfile)
                
                # Write basic statistics
                writer.writerow(['Statistic', 'Count'])
                writer.writerow(['Total Tracks', stats['Total Tracks']])
                writer.writerow(['Tracks with Genres', stats['Tracks with Genres']])
                writer.writerow([])  # Blank line
                
                # Write genre occurrence stats
                writer.writerow(['Genre', 'Hex Value', 'Occurrences'])
                
                # Sort genres by occurrence count, highest first
                sorted_genres = sorted(
                    [
                        (
                            genre, 
                            next((value['Hex'] for key, value in genre_mapping.items() if value['Genre'].lower() == genre), None), 
                            count
                        ) 
                        for genre, count in genre_counts.items() 
                        if count > 0  # Only include genres that occurred
                    ],
                    key=lambda x: x[2],  # Sort by count (occurrences)
                    reverse=True
                )

                # Write each genre's stats to the CSV
                for genre, hex_value, count in sorted_genres:
                    writer.writerow([genre, hex_value, count])

            logger.info(f"Stats CSV file created successfully: {stats_csv_path}\n")
        except Exception as e:
            logger.error(f"Error writing stats CSV file: {e}")

    # Fetch audio features if requested
    if fetch_features:
        logger.info("Fetching Spotify audio features...")
        if post and csv_path:
            fetch_audio_features_to_csv(data, sp, csv_path, retries=5)
        else:
            fetch_audio_features_to_csv(data, sp, output_csv_path, retries=5)
        logger.info("Completed fetching Spotify audio features.")

    # Fetch audio analysis if requested
    if fetch_analysis:
        logger.info("Fetching Spotify audio analysis data...")
        fetch_audio_analysis_to_csv(data, sp, output_csv_path, retries=5)
        logger.info("Completed fetching Spotify audio analysis data.")

    # Process loved metadata if loved M3U files are provided
    if loved_tracks_path or loved_albums_path or loved_artists_path:
        logger.info("Processing loved metadata...")
        # Parse loved M3U files
        loved_tracks_set = parse_m3u_for_loved(loved_tracks_path, music_dir_path) if loved_tracks_path else set()
        loved_albums_set = parse_m3u_for_loved(loved_albums_path, music_dir_path) if loved_albums_path else set()
        loved_artists_set = parse_m3u_for_loved(loved_artists_path, music_dir_path) if loved_artists_path else set()
        # Process and generate _loved.csv
        process_m3u_with_loved(
            args=SimpleNamespace(
                m3u_file=m3u_file,
                post=post,
                csv_file=csv_file
            ),
            loved_tracks=loved_tracks_set,
            loved_albums=loved_albums_set,
            loved_artists=loved_artists_set
        )

    return data  # Return data for further processing if needed
