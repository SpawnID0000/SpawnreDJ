# anal_M3U.py

import os
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

# Suppress the MusicBrainz non-official JSON format warning
import warnings
warnings.filterwarnings("ignore", message="The json format is non-official and may change at any time")

from SpawnreDJ.dic_spawnre import genre_mapping

# Set up logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

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
    # Add more synonyms as needed
}

related_genre_map = {
    'funk rock': ['funk metal'],
    'alternative rock': ['alternative metal'],
    'metal': ['nu metal', 'thrash metal', 'thrash'],
    # Add more related genres as needed
}

# Initialize caches
spotify_genre_cache: Dict[str, Tuple[List[str], List[str]]] = {}
musicbrainz_genre_cache: Dict[str, List[str]] = {}

# Set up MusicBrainz user agent
musicbrainzngs.set_useragent("Spawn", "0.1", "spawn.id.0000@gmail.com")
musicbrainzngs.set_format("json")


def fetch_genre_lastfm(artist: str, track: str, api_key: str, retries: int = 3, delay: int = 5, timeout: int = 10) -> List[str]:
    """
    Fetch genres from Last.fm API for a given track and artist.
    """
    url = f"https://ws.audioscrobbler.com/2.0/?method=track.getInfo&api_key={api_key}&artist={artist}&track={track}&format=json"
    for attempt in range(1, retries + 1):
        try:
            response = requests.get(url, timeout=timeout)
            response.raise_for_status()
            data = response.json()
            if 'track' in data and 'toptags' in data['track'] and 'tag' in data['track']['toptags']:
                genres = [tag['name'].lower() for tag in data['track']['toptags']['tag']]
                logging.debug(f"Last.FM genres extracted: {genres}")
                return genres
            else:
                logging.warning(f"No genres found for {artist} - {track} on Last.fm.")
                return []
        except requests.exceptions.HTTPError as e:
            logging.error(f"HTTP error while fetching Last.fm genres: {e}")
        except requests.exceptions.Timeout:
            logging.warning(f"Timeout occurred. Retrying ({attempt}/{retries})...")
        except requests.exceptions.RequestException as e:
            logging.error(f"Request exception: {e}")
            break
        time.sleep(delay)
    return []


def get_spotify_genres(artist_name: str, sp: spotipy.Spotify, retries: int = 3, delay: int = 5) -> Tuple[List[str], List[str]]:
    """
    Fetch genres from Spotify API for a given artist.
    Returns a tuple of (genres, genre_ids).
    """
    if artist_name in spotify_genre_cache:
        logging.debug(f"Spotify genres for '{artist_name}' fetched from cache.")
        return spotify_genre_cache[artist_name]
    
    for attempt in range(1, retries + 1):
        try:
            results = sp.search(q='artist:' + artist_name, type='artist')
            artists = results['artists']['items']
            if artists:
                artist = artists[0]
                genres = artist['genres'][:5]  # Limit to 5 genres
                # Spotify doesn't provide genre IDs; genres are strings
                spotify_genre_cache[artist_name] = (genres, [])
                logging.debug(f"Spotify genres extracted: {genres}")
                return genres, []
            else:
                logging.warning(f"No Spotify genres found for artist: {artist_name}")
                return [], []
        except spotipy.exceptions.SpotifyException as e:
            if e.http_status == 429:
                retry_after = int(e.headers.get('Retry-After', 60))
                jitter = random.uniform(0, 1)
                wait_time = retry_after + jitter
                logging.warning(f"Rate limit exceeded. Waiting for {wait_time:.2f} seconds.")
                time.sleep(wait_time)
            else:
                logging.error(f"Spotify API error: {e}. Retrying ({attempt}/{retries})...")
                time.sleep(delay)
        except requests.exceptions.RequestException as e:
            logging.error(f"Spotify request failed: {e}. Retrying ({attempt}/{retries})...")
            time.sleep(delay)
    return [], []


def get_musicbrainz_genres(artist_name: str) -> List[str]:
    """
    Fetch genres from MusicBrainz for a given artist.
    """
    if artist_name in musicbrainz_genre_cache:
        logging.debug(f"MusicBrainz genres for '{artist_name}' fetched from cache.")
        return musicbrainz_genre_cache[artist_name]
    
    logging.info(f"Fetching genres from MusicBrainz for artist: {artist_name}")
    
    try:
        result = musicbrainzngs.search_artists(artist=artist_name, limit=1)
        if 'artists' in result and result['artists']:
            artist_data = result['artists'][0]
            tags = artist_data.get('tags', [])
            genre_names = [tag['name'].lower() for tag in tags]
            musicbrainz_genre_cache[artist_name] = genre_names[:5]
            logging.debug(f"MusicBrainz genres extracted: {genre_names[:5]}")
            return genre_names[:5]
        else:
            logging.warning(f"No genre tags found for artist: {artist_name} on MusicBrainz.")
    except musicbrainzngs.WebServiceError as e:
        logging.error(f"MusicBrainz API request failed: {e}")
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
        logging.debug(f"Genre '{genre_lower}' not found in genre_mapping.")
    else:
        logging.debug(f"Normalized genre: {genre_lower}")

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
    """
    Combine and prioritize genres from multiple sources.
    """
    genre_count: Dict[str, int] = {}
    all_genres = [embedded_genre] + last_fm_genres + spotify_genres + musicbrainz_genres

    logging.debug(f"Initial combined genres: {all_genres}")

    for genre in all_genres:
        if genre:
            normalized_genre = normalize_genre(genre, related_genre_map, genre_synonyms, genre_mapping)
            genre_count[normalized_genre] = genre_count.get(normalized_genre, 0) + 1

    multi_source_genres = [genre for genre, count in genre_count.items() if count > 1]
    single_source_genres = [genre for genre, count in genre_count.items() if count == 1]

    logging.debug(f"Multi-source genres: {multi_source_genres}")
    logging.debug(f"Single-source genres: {single_source_genres}")

    combined_genres = multi_source_genres[:5]

    # Filter single-source genres
    single_source_filtered = [
        genre for genre in single_source_genres
        if genre.lower() != artist_name.lower() and any(value['Genre'].lower() == genre.lower() for value in genre_mapping.values())
    ]

    combined_genres += single_source_filtered[:5 - len(combined_genres)]

    combined_genres = combined_genres[:5]

    logging.debug(f"Final combined genres: {combined_genres}")

    return combined_genres


def find_closest_genre_matches(genres: List[str], genre_mapping: Dict[str, Dict[str, str]], artist_name: str) -> Tuple[List[str], str]:
    """
    Find the closest genre matches from the provided genres based on genre_mapping.
    Returns a tuple of (matched_genres, spawnre_hex).
    """
    matched_genres = []
    spawnre_hex = "x"

    # Predefined rock sub-genres to prioritize
    rock_related_genres = {
        'funk': 'funk rock',
        'piano': 'piano rock',
        'folk': 'folk rock',
        'pop': 'pop rock',
        'country': 'country rock',
        'blues': 'blues rock',
        'metal': 'metal'
    }

    logging.debug(f"Initial genres: {genres}")

    # Ensure "rock" is always included first if found
    if any('rock' in genre.lower() for genre in genres):
        matched_genres.append('rock')

    # Add rock-related sub-genres if "rock" was found
    if 'rock' in matched_genres:
        for genre in genres:
            genre_lower = genre.lower()
            for sub_genre_key, sub_genre_value in rock_related_genres.items():
                if sub_genre_key in genre_lower and sub_genre_value not in matched_genres:
                    matched_genres.append(sub_genre_value)

    # Broad matching for remaining genres
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

    # Sort matched genres based on their order in genre_mapping
    matched_genres.sort(
        key=lambda g: next((idx for idx, (k, v) in enumerate(genre_mapping.items()) if v['Genre'].lower() == g.lower()), len(genre_mapping))
    )

    # Limit to 5 genres
    matched_genres = matched_genres[:5]

    # Generate spawnre_hex
    for genre in matched_genres:
        for key, value in genre_mapping.items():
            if value['Genre'].lower() == genre.lower():
                hex_part = value['Hex'][2:].zfill(2)  # Remove '0x' and ensure two characters
                spawnre_hex += hex_part
                break
        if len(spawnre_hex) >= 10:  # Limit to 'x' + 10 characters
            break

    spawnre_hex = spawnre_hex[:10]

    logging.debug(f"Matched genres: {matched_genres}, Spawnre Hex: {spawnre_hex}")

    return matched_genres, spawnre_hex


def determine_format_using_metadata(track_name: str, artist_name: str, file_path: str) -> str:
    """
    Determine the format of the #EXTINF line based on embedded metadata.
    Returns 'Artist - Track', 'Track - Artist', or 'Unknown'.
    """
    try:
        audio = MP4(file_path)
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
        logging.error(f"Error determining format using metadata for {file_path}: {e}")
        return 'Unknown'


def fetch_audio_features_to_csv(data: List[Dict[str, Any]], sp: spotipy.Spotify, output_csv_path: str, retries: int = 5) -> None:
    """
    Fetch audio features for tracks in batches and write the results to a separate CSV file.
    """
    features_csv_path = os.path.splitext(output_csv_path)[0] + '_features.csv'
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
        with open(features_csv_path, 'w', newline='', encoding='utf-8') as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=features_fieldnames)
            writer.writeheader()
    except Exception as e:
        logging.error(f"Error initializing features CSV file '{features_csv_path}': {e}")
        return

    # Collect all Spotify Track IDs
    track_ids = [track_data['spotify_track_ID'] for track_data in data if track_data.get('spotify_track_ID')]

    # Batch track IDs into chunks
    batch_size = 50
    track_id_batches = [track_ids[i:i + batch_size] for i in range(0, len(track_ids), batch_size)]

    logging.info(f"Fetching audio features for {len(track_ids)} tracks in batches of {batch_size}...")

    for batch_num, batch in enumerate(track_id_batches, start=1):
        logging.info(f"Processing batch {batch_num}/{len(track_id_batches)}")
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
                            with open(features_csv_path, 'a', newline='', encoding='utf-8') as csvfile:
                                writer = csv.DictWriter(csvfile, fieldnames=features_fieldnames)
                                writer.writerow(feature_row)
            else:
                logging.warning(f"No audio features found for batch {batch_num}.")
        except spotipy.exceptions.SpotifyException as e:
            if e.http_status == 429:
                retry_after = int(e.headers.get('Retry-After', 60))
                jitter = random.uniform(0, 1)
                wait_time = retry_after + jitter
                logging.warning(f"Rate limit exceeded. Waiting for {wait_time:.2f} seconds.")
                time.sleep(wait_time)
                continue
            else:
                logging.error(f"Spotify API error: {e}. Skipping batch {batch_num}.")
        except Exception as e:
            logging.error(f"Unexpected error while fetching audio features for batch {batch_num}: {e}")

        # Introduce a small delay to respect API rate limits
        time.sleep(random.uniform(0.5, 1.5))

    logging.info("Audio features fetching complete.")


def parse_m3u_for_loved(m3u_file: str, music_directory: str) -> set:
    """
    Read an M3U file and return a set of absolute, normalized paths.
    Resolves relative paths based on the provided music_directory.
    """
    loved_paths = set()
    if os.path.exists(m3u_file):
        with open(m3u_file, 'r', encoding='utf-8') as file:
            for line in file:
                line = line.strip()
                if not line.startswith('#') and line:
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
    Process the main playlist CSV and append loved metadata.
    """
    # Load the original CSV generated from the main analyze function
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
                album_dir = os.path.dirname(normalized_file_path)  # /music_dir/artist/album
                album_dir_normalized = os.path.normpath(album_dir.lower())

                artist_dir = os.path.dirname(album_dir)  # /music_dir/artist
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


def fetch_audio_analysis_to_csv(data: List[Dict[str, Any]], sp: spotipy.Spotify, output_csv_path: str, retries: int = 5) -> None:
    """
    Fetch audio analysis data for tracks and write the results to a separate CSV file.
    """
    analysis_csv_path = os.path.splitext(output_csv_path)[0] + '_analysis.csv'

    # Check if analysis CSV file exists and load it if -post is used
    existing_analysis = {}
    if os.path.exists(analysis_csv_path):
        try:
            with open(analysis_csv_path, 'r', newline='', encoding='utf-8') as csvfile:
                reader = csv.DictReader(csvfile)
                for row in reader:
                    existing_analysis[row['spotify_track_ID']] = row  # Save rows based on track ID
            logging.info(f"Resuming from existing analysis file: {analysis_csv_path}")
        except Exception as e:
            logging.error(f"Error reading analysis CSV file '{analysis_csv_path}': {e}")

    # Define the fieldnames including new genre columns and audio analysis columns
    fieldnames = [
        'artist', 'album', 'track', 'year', 'spawnre', 'spawnre_hex',
        'musicbrainz_artist_ID', 'musicbrainz_release_group_ID', 'musicbrainz_track_ID',
        'spotify_artist_ID', 'spotify_track_ID',
        'file_duration_ms', 'spotify_duration_ms', 
        'embedded_genre', 'spawnre_tag', 'file_path',
        'spotify_genre_1', 'spotify_genre_2', 'spotify_genre_3', 'spotify_genre_4', 'spotify_genre_5',
        'last_FM_genre_1', 'last_FM_genre_2', 'last_FM_genre_3', 'last_FM_genre_4', 'last_FM_genre_5',
        'musicbrainz_genre_1', 'musicbrainz_genre_2', 'musicbrainz_genre_3', 'musicbrainz_genre_4', 'musicbrainz_genre_5',
        # Audio analysis columns
        'loudness_range', 'section_start', 'section_duration',
        'segment_loudness_start', 'segment_start', 'segment_duration'
    ]

    # Initialize the analysis CSV with headers if it doesn't exist
    if not os.path.exists(analysis_csv_path):
        try:
            with open(analysis_csv_path, 'w', newline='', encoding='utf-8') as csvfile:
                writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                writer.writeheader()
            logging.info(f"Created analysis CSV file with headers: {analysis_csv_path}")
        except Exception as e:
            logging.error(f"Error initializing analysis CSV file '{analysis_csv_path}': {e}")
            return

    logging.info(f"Fetching audio analysis for {len(data)} tracks...")

    for track_num, track_data in enumerate(data, start=1):
        spotify_track_id = track_data.get('spotify_track_ID')
        if not spotify_track_id:
            logging.warning(f"No Spotify Track ID found for {track_data['track']}. Skipping.")
            continue

        # Skip tracks already processed in the existing _analysis.csv
        if spotify_track_id in existing_analysis:
            logging.info(f"Skipping already processed track: {track_data['track']} (ID: {spotify_track_id})")
            continue

        logging.info(f"\nProcessing track {track_num}/{len(data)}: Spotify Track ID: {spotify_track_id}")

        attempt = 0
        success = False  # Flag to track success

        while attempt < retries:
            try:
                logging.info(f"Attempt {attempt + 1} to fetch audio analysis for track ID: {spotify_track_id}")
                analysis = sp.audio_analysis(spotify_track_id)
                if analysis:
                    # Collect section and segment data
                    sections = analysis.get('sections', [])
                    segments = analysis.get('segments', [])

                    if sections:
                        loudness_range = sections[0].get('loudness_range', '')
                        section_start = sections[0].get('start', '')
                        section_duration = sections[0].get('duration', '')
                        track_data.update({
                            'loudness_range': loudness_range,
                            'section_start': section_start,
                            'section_duration': section_duration
                        })
                    if segments:
                        segment_loudness_start = segments[0].get('loudness_start', '')
                        segment_start = segments[0].get('start', '')
                        segment_duration = segments[0].get('duration', '')
                        track_data.update({
                            'segment_loudness_start': segment_loudness_start,
                            'segment_start': segment_start,
                            'segment_duration': segment_duration
                        })
                    success = True
                    logging.debug(f"Audio analysis fetched successfully for track ID: {spotify_track_id}.")

                    # Append the processed track's data to the analysis CSV
                    try:
                        with open(analysis_csv_path, 'a', newline='', encoding='utf-8') as csvfile:
                            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                            writer.writerow({k: track_data.get(k, '') for k in fieldnames})  # Write track data
                        logging.debug(f"Audio analysis written for track ID: {spotify_track_id}.")
                    except Exception as e:
                        logging.error(f"Error writing to analysis CSV file '{analysis_csv_path}': {e}")

                    break  # Exit loop on success
                else:
                    logging.warning(f"Failed to fetch audio analysis for {spotify_track_id}.")
            except spotipy.exceptions.SpotifyException as e:
                if e.http_status == 429:  # Handling API throttle (rate limit)
                    retry_after = int(e.headers.get('Retry-After', 60))  # Default to 60 seconds
                    jitter = random.uniform(0, 1)  # Add a small jitter
                    wait_time = retry_after + jitter
                    logging.warning(f"Rate limit encountered (HTTP 429). Retrying after {wait_time:.2f} seconds...")
                    time.sleep(wait_time)
                    attempt += 1
                else:
                    logging.error(f"Spotify API error: {e}")
                    break
            except http.client.RemoteDisconnected as e:  # Handling connection errors
                logging.warning(f"RemoteDisconnected error: {e}. Retrying ({attempt + 1}/{retries})...")
                time.sleep(random.uniform(1, 3))  # Random delay to reduce strain on the server
                attempt += 1
            except Exception as e:  # Catch-all for any other exceptions
                logging.error(f"Unexpected error: {e}")
                break

        if not success:
            logging.warning(f"Max retries reached. Failed to fetch audio analysis for track {spotify_track_id}.")

            # Implement 3 retries with exponential backoff (1 min, 2 min, 4 min) before prompting the user
            max_backoff_retries = 3
            base_backoff_time = 60  # Start with 1 minute

            for retry in range(max_backoff_retries):
                retry_delay = base_backoff_time * (2 ** retry)  # Exponential backoff
                logging.info(f"Retrying in {retry_delay // 60} minute(s)...")
                time.sleep(retry_delay)

                attempt = 0
                try:
                    logging.info(f"Retry {retry + 1}/{max_backoff_retries} for track {spotify_track_id}.")
                    analysis = sp.audio_analysis(spotify_track_id)
                    if analysis:
                        # Collect section and segment data
                        sections = analysis.get('sections', [])
                        segments = analysis.get('segments', [])

                        if sections:
                            loudness_range = sections[0].get('loudness_range', '')
                            section_start = sections[0].get('start', '')
                            section_duration = sections[0].get('duration', '')
                            track_data.update({
                                'loudness_range': loudness_range,
                                'section_start': section_start,
                                'section_duration': section_duration
                            })
                        if segments:
                            segment_loudness_start = segments[0].get('loudness_start', '')
                            segment_start = segments[0].get('start', '')
                            segment_duration = segments[0].get('duration', '')
                            track_data.update({
                                'segment_loudness_start': segment_loudness_start,
                                'segment_start': segment_start,
                                'segment_duration': segment_duration
                            })
                        success = True
                        logging.debug(f"Audio analysis fetched successfully for track ID: {spotify_track_id} on retry {retry + 1}.")

                        # Append the processed track's data to the analysis CSV
                        try:
                            with open(analysis_csv_path, 'a', newline='', encoding='utf-8') as csvfile:
                                writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                                writer.writerow({k: track_data.get(k, '') for k in fieldnames})  # Write track data
                            logging.debug(f"Audio analysis written for track ID: {spotify_track_id} on retry {retry + 1}.")
                        except Exception as e:
                            logging.error(f"Error writing to analysis CSV file '{analysis_csv_path}': {e}")

                        break  # Exit loop on success
                    else:
                        logging.warning(f"Failed to fetch audio analysis for track {spotify_track_id} on retry {retry + 1}.")
                except Exception as e:
                    logging.error(f"Unexpected error during retry {retry + 1}: {e}")

            if not success:
                logging.warning(f"Retries failed for track {spotify_track_id}.")
                user_input = input("Do you want to retry (y) or continue to the next track (n)? ").lower().strip()
                if user_input == 'y':
                    # Reset the loop to retry again
                    logging.info(f"Retrying track {spotify_track_id} as per user request.")
                    data.remove(track_data)  # Remove from data to reprocess
                    data.append(track_data)  # Re-add to process again
                else:
                    logging.info(f"Continuing to the next track without analysis for {spotify_track_id}.")

        # Introduce delay between API calls to avoid rapid consecutive requests
        time.sleep(random.uniform(0.5, 1.5))


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
    loved_tracks: Optional[str] = None,
    loved_albums: Optional[str] = None,
    loved_artists: Optional[str] = None
) -> List[Dict[str, Any]]:
    """
    Main function to parse and analyze M3U playlists.
    """
    # Initialize Spotify client
    sp = spotipy.Spotify(
        auth_manager=SpotifyClientCredentials(
            client_id=spotify_client_id,
            client_secret=spotify_client_secret
        ),
        requests_timeout=30
    )

    with open(m3u_file, 'r', encoding='utf-8') as file:
        lines = file.readlines()

    # Get total number of tracks in the M3U
    total_tracks = sum(1 for line in lines if line.strip() and not line.startswith('#'))
    logging.info(f"\nTotal number of tracks: {total_tracks}\n")

    data: List[Dict[str, Any]] = []
    stats = {'Total Tracks': 0, 'Tracks with Genres': 0}
    genre_counts = {value['Genre'].lower(): 0 for key, value in genre_mapping.items() if value['Genre']}

    # Dictionary to store sub-genre counts for each artist
    artist_subgenre_count: Dict[str, Dict[str, int]] = {}
    artist_spawnre_tags: Dict[str, str] = {}

    track_counter = 0

    for i, line in enumerate(lines):
        line = line.strip()
        if line.startswith("#EXTINF"):
            track_counter += 1
            logging.info(f"\nTrack {track_counter} of {total_tracks}")
    
            parts = line.split(',', 1)
            if len(parts) < 2:
                logging.warning(f"Invalid EXTINF line format: {line}")
                continue
            track_info = parts[1].split(' - ')

            if len(track_info) < 2:
                logging.warning(f"Invalid track info format: {parts[1]}")
                continue

            if i + 1 >= len(lines):
                logging.warning("No file path found for the last EXTINF line.")
                continue
            file_line = lines[i + 1].strip()
            file_path = os.path.join(music_directory, file_line)
            resolved_path = os.path.normpath(file_path)

            # Determine the format using metadata
            format_type = determine_format_using_metadata(track_info[1].strip(), track_info[0].strip(), resolved_path)

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
                audio = MP4(resolved_path)
                album_tag = audio.tags.get('\xa9alb', ['Unknown Album'])[0]
                
                # Corrected embedded_genre extraction
                embedded_genre_list = audio.tags.get('\xa9gen', [''])
                if isinstance(embedded_genre_list, list) and len(embedded_genre_list) > 0:
                    embedded_genre = embedded_genre_list[0].lower()
                else:
                    embedded_genre = ''
                
                file_duration_ms = int(audio.info.length * 1000)
                mb_artistid = audio.tags.get('----:com.apple.iTunes:MusicBrainz Artist Id', [b''])[0].decode('utf-8') if isinstance(audio.tags.get('----:com.apple.iTunes:MusicBrainz Artist Id', [b''])[0], bytes) else ''
                mb_releasegroupid = audio.tags.get('----:com.apple.iTunes:MusicBrainz Release Group Id', [b''])[0].decode('utf-8') if isinstance(audio.tags.get('----:com.apple.iTunes:MusicBrainz Release Group Id', [b''])[0], bytes) else ''
                mb_trackid = audio.tags.get('----:com.apple.iTunes:MusicBrainz Track Id', [b''])[0].decode('utf-8') if isinstance(audio.tags.get('----:com.apple.iTunes:MusicBrainz Track Id', [b''])[0], bytes) else ''
                year = audio.tags.get('\xa9day', ['Unknown'])[0]
                logging.info(f"Artist: {artist}, Album: {album_tag}, Track: {track}")
                logging.debug("-----------------------")
                logging.info(f"File Duration: {file_duration_ms} ms")
                logging.info(f"Embedded genre tag extracted: {embedded_genre}")
            except Exception as e:
                logging.error(f"Error reading embedded genre from {resolved_path}: {e}")
                embedded_genre = ''
                file_duration_ms = ''
                mb_artistid = ''
                mb_releasegroupid = ''
                mb_trackid = ''
                year = ''

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

            logging.info(f"Final matched genres: {closest_genres}")
            logging.info(f"Spawnre Hex: {spawnre_hex}")
            logging.debug("-----------------------")

            # Track sub-genres for the artist
            if artist not in artist_subgenre_count:
                artist_subgenre_count[artist] = {}

            for genre in closest_genres:
                genre_lower = genre.lower()
                if genre_lower in genre_counts:
                    genre_counts[genre_lower] += 1

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
                    logging.info(f"Spotify Artist ID for {artist}: {spotify_artist_id}")
                    logging.info(f"Spotify Track ID for {track}: {spotify_track_id}")
                    logging.info(f"Spotify Duration: {spotify_duration_ms} ms")
            except Exception as e:
                logging.error(f"Error fetching Spotify track ID for {track}: {e}")

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
                'file_path': resolved_path
            }

            # Merge genre columns
            track_dict.update(spotify_genre_columns)
            track_dict.update(last_fm_genre_columns)
            track_dict.update(musicbrainz_genre_columns)

            data.append(track_dict)

            stats['Total Tracks'] += 1
            if closest_genres:
                stats['Tracks with Genres'] += 1

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

    # Writing main CSV
    output_csv_path = os.path.splitext(m3u_file)[0] + '.csv'
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
        with open(output_csv_path, 'w', newline='', encoding='utf-8') as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()

            for track_data in data:
                track_data['spawnre_tag'] = artist_spawnre_tags.get(track_data['artist'], '')
                filtered_track_data = {key: track_data.get(key, '') for key in fieldnames}
                writer.writerow(filtered_track_data)
        
        logging.info(f"\nMain CSV file created successfully: {output_csv_path}")
    except Exception as e:
        logging.error(f"Error writing main CSV file: {e}")

    # Write stats CSV if requested
    if generate_stats:
        stats_csv_path = os.path.splitext(m3u_file)[0] + '_stats.csv'
        try:
            with open(stats_csv_path, 'w', newline='', encoding='utf-8') as csvfile:
                writer = csv.writer(csvfile)
                writer.writerow(['Statistic', 'Count'])
                for key, value in stats.items():
                    writer.writerow([key, value])
                writer.writerow([])  # Blank line
                writer.writerow(['Genre', 'Hex Value', 'Occurrences'])

                sorted_genres = sorted(
                    [
                        (
                            genre, 
                            next((value['Hex'] for key, value in genre_mapping.items() if value['Genre'].lower() == genre), None), 
                            count
                        ) 
                        for genre, count in genre_counts.items() 
                        if count > 0
                    ],
                    key=lambda x: x[2],
                    reverse=True
                )

                for genre, hex_value, count in sorted_genres:
                    writer.writerow([genre, hex_value, count])

            logging.info(f"Stats CSV file created successfully: {stats_csv_path}\n")
        except Exception as e:
            logging.error(f"Error writing stats CSV file: {e}")

    # Fetch audio features if requested
    if fetch_features:
        logging.info("Fetching Spotify audio features...")
        fetch_audio_features_to_csv(data, sp, output_csv_path, retries=5)

    # Fetch audio analysis if requested
    if fetch_analysis:
        logging.info("Fetching Spotify audio analysis data...")
        fetch_audio_analysis_to_csv(data, sp, output_csv_path, retries=5)

    # Process loved metadata if loved M3U files are provided
    if loved_tracks or loved_albums or loved_artists:
        logging.info("Processing loved metadata...")
        # Parse loved M3U files
        loved_tracks_set = parse_m3u_for_loved(loved_tracks, music_directory) if loved_tracks else set()
        loved_albums_set = parse_m3u_for_loved(loved_albums, music_directory) if loved_albums else set()
        loved_artists_set = parse_m3u_for_loved(loved_artists, music_directory) if loved_artists else set()
        # Process and generate _loved.csv
        process_m3u_with_loved(
            args=SimpleNamespace(
                m3u_file=m3u_file
            ),
            loved_tracks=loved_tracks_set,
            loved_albums=loved_albums_set,
            loved_artists=loved_artists_set
        )

    return data  # Return data for further processing if needed
