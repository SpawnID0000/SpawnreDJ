# anal_M3U.py

import csv
import logging
import requests
import time
import random
from typing import List, Tuple, Dict, Any, Optional

import mutagen
from mutagen.mp4 import MP4, MP4FreeForm
from mutagen.easyid3 import EasyID3
import spotipy
from spotipy.oauth2 import SpotifyClientCredentials
import musicbrainzngs

from pathlib import Path
from collections import defaultdict

# Suppress the MusicBrainz non-official JSON format warning
import warnings
warnings.filterwarnings("ignore", message="The json format is non-official and may change at any time")

from SpawnreDJ.dic_spawnre import genre_mapping, subgenre_to_parent

# Initialize module-specific logger
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)  # Set to DEBUG for detailed logging

# Configure logging format and handlers
if not logger.hasHandlers():
    handler = logging.StreamHandler()
    formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
    handler.setFormatter(formatter)
    logger.addHandler(handler)

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
    'rhythm & blues': 'r&b',
    'rhythm and blues': 'r&b',
    'rock-n-roll': 'rock & roll',
    'rock and roll': 'rock & roll',
    'punk rock': 'punk',
    'alternative': 'alternative rock'
}

# Initialize caches
spotify_genre_cache: Dict[str, List[str]] = {}
musicbrainz_genre_cache: Dict[str, List[str]] = {}

# Set up MusicBrainz user agent
musicbrainzngs.set_useragent("Spawn", "0.1", "spawn.id.0000@gmail.com")
musicbrainzngs.set_format("json")


def sanitize_path(path: str) -> Path:
    sanitized = path.replace('\\ ', ' ').replace('\\\\', '\\')
    sanitized_path = Path(sanitized).expanduser().resolve()
    logger.debug(f"Sanitized path: {sanitized_path}")
    return sanitized_path


def extract_audio_features(file_path: str) -> Dict[str, Any]:
    """
    Extracts audio features from embedded MP4/M4A tags.
    
    Args:
        file_path (str): Path to the MP4/M4A file.
    
    Returns:
        Dict[str, Any]: Dictionary containing audio feature values.
    """
    features = {
        'danceability': '',
        'energy': '',
        'key': '',
        'loudness': '',
        'mode': '',
        'speechiness': '',
        'acousticness': '',
        'instrumentalness': '',
        'liveness': '',
        'valence': '',
        'tempo': '',
        'time_signature': ''
    }

    try:
        audio = MP4(file_path)
        feature_keys = [
            'danceability', 'energy', 'key', 'loudness',
            'mode', 'speechiness', 'acousticness', 'instrumentalness',
            'liveness', 'valence', 'tempo', 'time_signature'
        ]

        for feature in feature_keys:
            tag_key = f'----:com.apple.iTunes:feature_{feature}'
            if tag_key in audio.tags:
                tag = audio.tags[tag_key][0]
                if isinstance(tag, MP4FreeForm):
                    # Correctly access the raw bytes using bytes(tag)
                    try:
                        tag_value_bytes = bytes(tag)
                        tag_value_str = tag_value_bytes.decode('utf-8').strip()
                        # Convert to float or int based on feature
                        if feature in ['key', 'mode', 'time_signature']:
                            features[feature] = int(tag_value_str)
                        else:
                            features[feature] = float(tag_value_str)
                        logger.debug(f"Extracted {feature} for {file_path}: {features[feature]}")
                    except Exception as e:
                        logger.error(f"Error decoding and converting feature '{feature}' for {file_path}: {e}")
                        features[feature] = ''
                else:
                    logger.warning(f"Unexpected tag type for '{feature}' in {file_path}: {type(tag)}")
                    features[feature] = ''
            else:
                logger.debug(f"Feature '{feature}' not found in {file_path}.")
                features[feature] = ''

    except Exception as e:
        logger.error(f"Error reading MP4 tags from {file_path}: {e}")

    return features


def fetch_genre_lastfm(artist: str, track: str, api_key: str, retries: int = 3, delay: int = 5, timeout: int = 10) -> List[str]:
    if not api_key:
        logger.warning("Last.fm API key not provided.")
        return []
    url = f"https://ws.audioscrobbler.com/2.0/?method=track.getInfo&api_key={api_key}&artist={artist}&track={track}&format=json"
    for attempt in range(1, retries + 1):
        try:
            logger.debug(f"Fetching Last.fm genres for '{artist} - {track}' (Attempt {attempt})")
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
    logger.error(f"Failed to fetch Last.fm genres for '{artist} - {track}' after {retries} attempts.")
    return []


def get_spotify_genres(artist_name: str, sp: spotipy.Spotify, retries: int = 3, delay: int = 5) -> List[str]:

    if not sp:
        return []

    for attempt in range(1, retries + 1):
        try:
            logger.debug(f"Fetching Spotify genres for '{artist_name}' (Attempt {attempt})")
            results = sp.search(q='artist:' + artist_name, type='artist')
            artists = results['artists']['items']
            if artists:
                artist = artists[0]
                genres = artist['genres'][:5]
                spotify_genre_cache[artist_name] = genres
                logger.debug(f"Spotify genres extracted: {genres}")
                return genres
            else:
                logger.warning(f"No Spotify genres found for artist: {artist_name}")
                return []
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
    logger.error(f"Failed to fetch Spotify genres for '{artist_name}' after {retries} attempts.")
    return []


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


def normalize_genre(genre: str, genre_mapping: Dict[str, Dict[str, str]], genre_synonyms: Dict[str, str]) -> str:
    genre_lower = genre.lower()

    # Apply synonyms
    if genre_lower in genre_synonyms:
        genre_lower = genre_synonyms[genre_lower]
        logger.debug(f"Applied synonym: Original genre '{genre}' normalized to '{genre_lower}'")
    else:
        logger.debug(f"No synonym applied for genre '{genre}'. It remains as '{genre_lower}'")

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
    artist_name: str,
    artist_genre_count: Dict[str, Dict[str, int]]
) -> List[str]:
    genre_count: Dict[str, int] = {}
    all_genres = [embedded_genre] + last_fm_genres + spotify_genres + musicbrainz_genres

    logger.debug(f"Initial combined genres: {all_genres}")

    for genre in all_genres:
        if genre:
            normalized_genre = normalize_genre(genre, genre_mapping, genre_synonyms)
            if any(value['Genre'].lower() == normalized_genre for value in genre_mapping.values()):
                genre_count[normalized_genre] = genre_count.get(normalized_genre, 0) + 1
                # Update per-artist genre count
                artist_genre_count[artist_name.lower()][normalized_genre] += 1
                logger.debug(f"Genre '{normalized_genre}' count updated to {genre_count[normalized_genre]}")
            else:
                logger.debug(f"Normalized genre '{normalized_genre}' is not present in genre_mapping and will be skipped.")

    multi_source_genres = [genre for genre, count in genre_count.items() if count > 1]
    single_source_genres = [genre for genre, count in genre_count.items() if count == 1]

    logger.debug(f"Multi-source genres: {multi_source_genres}")
    logger.debug(f"Single-source genres: {single_source_genres}")

    combined_genres = multi_source_genres[:5]
    single_source_filtered = [
        genre for genre in single_source_genres
        if any(value['Genre'].lower() == genre.lower() for value in genre_mapping.values())
    ]
    combined_genres += single_source_filtered[:5 - len(combined_genres)]

    combined_genres = combined_genres[:5]
    logger.debug(f"Final combined genres: {combined_genres}")

    return combined_genres


def find_closest_genre_matches(genres: List[str], genre_mapping: Dict[str, Dict[str, str]]) -> Tuple[List[str], str]:
    matched_genres = []
    spawnre_hex = "x"

    logger.debug(f"Initial genres for matching: {genres}")

    # Sort genres based on their order in genre_mapping
    sorted_genres = sorted(
        genres,
        key=lambda g: next((idx for idx, (k, v) in enumerate(genre_mapping.items()) if v['Genre'].lower() == g.lower()), len(genre_mapping))
    )

    sorted_genres = sorted_genres[:5]

    logger.debug(f"Matched genres before hex assignment: {sorted_genres}")

    for genre in sorted_genres:
        for key, value in genre_mapping.items():
            if value['Genre'].lower() == genre.lower():
                hex_part = value['Hex'].replace('0x', '')  # Remove '0x' prefix
                logger.debug(f"Appending Hex for genre '{genre}': {hex_part}")
                spawnre_hex += hex_part
                matched_genres.append(value['Genre'])
                break
        if len(spawnre_hex) >= 10:
            logger.debug(f"Spawnre Hex reached the maximum length with value: {spawnre_hex}")
            break

    spawnre_hex = spawnre_hex[:10]  # Limit to 10 characters
    logger.debug(f"Final matched genres: {matched_genres}, Spawnre Hex: {spawnre_hex}")

    return matched_genres, spawnre_hex


def parse_m3u_for_loved(m3u_file: Path, music_directory: Path, level: str = 'track') -> set:

    loved_set = set()

    if m3u_file.exists():
        with m3u_file.open('r', encoding='utf-8') as file:
            for line in file:
                line = line.strip()
                if line and not line.startswith("#"):  # Skip comments and empty lines
                    file_path = music_directory / line
                    file_path = file_path.resolve()  # Resolve full path

                    if level == 'track':
                        loved_set.add(file_path)
                    elif level == 'album':
                        loved_set.add(file_path.parent)  # Parent directory = album
                    elif level == 'artist':
                        loved_set.add(file_path.parent.parent)  # Grandparent directory = artist

    return loved_set


def fetch_audio_features(sp: spotipy.Spotify, track_ids: List[str], retries: int = 5) -> Dict[str, Dict[str, Any]]:
    features_data = {}
    batch_size = 50
    track_id_batches = [track_ids[i:i + batch_size] for i in range(0, len(track_ids), batch_size)]

    logger.info(f"Fetching audio features for {len(track_ids)} tracks in batches of {batch_size}...")

    for batch_num, batch in enumerate(track_id_batches, start=1):
        logger.info(f"Processing batch {batch_num}/{len(track_id_batches)} with {len(batch)} track IDs")
        for attempt in range(1, retries + 1):
            try:
                logger.debug(f"Fetching audio features for batch {batch_num}, attempt {attempt}")
                features = sp.audio_features(batch)
                if features:
                    for feature in features:
                        if feature and feature['id']:
                            features_data[feature['id']] = feature
                            logger.debug(f"Fetched features for track ID {feature['id']}")
                    break
                else:
                    logger.warning(f"No audio features found for batch {batch_num}.")
                    break
            except spotipy.exceptions.SpotifyException as e:
                if e.http_status == 429:
                    retry_after = int(e.headers.get('Retry-After', 60))
                    jitter = random.uniform(0, 1)
                    wait_time = retry_after + jitter
                    logger.warning(f"Rate limit exceeded. Waiting for {wait_time:.2f} seconds.")
                    time.sleep(wait_time)
                else:
                    logger.error(f"Spotify API error: {e}. Retrying ({attempt}/{retries})...")
                    time.sleep(5)
            except Exception as e:
                logger.error(f"Unexpected error while fetching audio features for batch {batch_num}: {e}")
                time.sleep(5)
        else:
            logger.error(f"Failed to fetch audio features for batch {batch_num} after {retries} attempts.")

        time.sleep(random.uniform(0.5, 1.5))  # Respectful delay between API calls

    logger.info("Audio features fetching complete.")
    return features_data


def fetch_musicbrainz_ids_from_api(artist_name: str, track_name: str, album_name: str) -> Dict[str, str]:
    musicbrainz_ids = {'artist_id': '', 'release_group_id': '', 'track_id': ''}

    try:
        logger.debug(f"Fetching MusicBrainz artist ID for '{artist_name}'")
        # Fetch artist ID
        artist_result = musicbrainzngs.search_artists(artist=artist_name, limit=1)
        if 'artists' in artist_result and artist_result['artists']:
            musicbrainz_ids['artist_id'] = artist_result['artists'][0].get('id', '')
            logger.debug(f"Found MusicBrainz artist ID: {musicbrainz_ids['artist_id']}")

        # Fetch release group ID
        if album_name:
            logger.debug(f"Fetching MusicBrainz release group ID for album '{album_name}'")
            release_result = musicbrainzngs.search_release_groups(artist=artist_name, releasegroup=album_name, limit=1)
            if 'release-group-list' in release_result and release_result['release-group-list']:
                musicbrainz_ids['release_group_id'] = release_result['release-group-list'][0].get('id', '')
                logger.debug(f"Found MusicBrainz release group ID: {musicbrainz_ids['release_group_id']}")
            elif not musicbrainz_ids['release_group_id']:
                release_result = musicbrainzngs.search_release_groups(releasegroup=album_name, limit=1)
                if 'release-group-list' in release_result and release_result['release-group-list']:
                    musicbrainz_ids['release_group_id'] = release_result['release-group-list'][0].get('id', '')
                    logger.debug(f"Found MusicBrainz release group ID: {musicbrainz_ids['release_group_id']}")

        # Fetch track ID
        if track_name:
            logger.debug(f"Fetching MusicBrainz track ID for track '{track_name}'")
            track_result = musicbrainzngs.search_recordings(artist=artist_name, recording=track_name, limit=1)
            if 'recording-list' in track_result and track_result['recording-list']:
                musicbrainz_ids['track_id'] = track_result['recording-list'][0].get('id', '')
                logger.debug(f"Found MusicBrainz track ID: {musicbrainz_ids['track_id']}")

        logger.info(f"Fetched MusicBrainz IDs via API for {artist_name} - {track_name}: {musicbrainz_ids}")

    except musicbrainzngs.WebServiceError as e:
        logger.error(f"MusicBrainz API request failed: {e}")

    return musicbrainz_ids


def populate_missing_spotify_ids(data: List[Dict[str, Any]], sp: spotipy.Spotify, batch_size: int = 50) -> None:
    """
    Populates missing Spotify Track IDs for tracks in the given data.
    Processes tracks in batches for efficiency.
    
    Args:
        data (List[Dict[str, Any]]): List of track dictionaries.
        sp (spotipy.Spotify): Authenticated Spotify client.
        batch_size (int): Number of tracks to process per batch.
    """
    # Filter tracks with missing Spotify Track IDs
    missing_ids = [track for track in data if not track.get('spotify_track_ID')]
    logger.info(f"Found {len(missing_ids)} tracks with missing Spotify Track IDs.")

    # Divide the tracks into batches
    for i in range(0, len(missing_ids), batch_size):
        batch = missing_ids[i:i + batch_size]
        logger.info(f"Processing batch {i // batch_size + 1} with {len(batch)} tracks.")
        
        # Construct batch search queries
        queries = []
        track_map = {}
        for track in batch:
            artist = track.get('artist', '').strip()
            track_name = track.get('track', '').strip()
            if artist and track_name:
                query = f"track:{track_name} artist:{artist}"
                queries.append(query)
                track_map[query] = track  # Map query to track for updating

        # Execute Spotify searches
        try:
            for query in queries:
                try:
                    logger.debug(f"Searching Spotify for '{query}'")
                    result = sp.search(q=query, type='track', limit=1)
                    if result['tracks']['items']:
                        # Update the track data
                        track_item = result['tracks']['items'][0]
                        track = track_map[query]
                        track['spotify_track_ID'] = track_item['id']
                        track['spotify_artist_ID'] = track_item['artists'][0]['id'] if track_item['artists'] else ''
                        track['spotify_duration_ms'] = track_item.get('duration_ms', 0)

                        # Fetch artist genres
                        spotify_genres = track_item['artists'][0]['genres'][:5] if 'genres' in track_item['artists'][0] else []
                        for j, genre in enumerate(spotify_genres):
                            track[f'spotify_genre_{j + 1}'] = genre

                        logger.info(f"Populated Spotify data for '{track['artist']} - {track['track']}': "
                                    f"Track ID = {track['spotify_track_ID']}, Artist ID = {track['spotify_artist_ID']}, "
                                    f"Duration = {track['spotify_duration_ms']} ms")
                    else:
                        logger.warning(f"No Spotify Track found for '{query}'.")

                except Exception as e:
                    logger.error(f"Error processing query '{query}': {e}")

            time.sleep(random.uniform(1, 2))  # Delay between batch requests to avoid rate limits

        except Exception as e:
            logger.error(f"Error fetching Spotify data for batch {i // batch_size + 1}: {e}")

    logger.info("Completed populating missing Spotify IDs.")


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


def extract_embedded_spotify_ids(file_path: str) -> Dict[str, str]:
    spotify_ids = {'spotify_artist_ID': '', 'spotify_track_ID': ''}
    try:
        audio = MP4(file_path)
        artist_id_tag = '----:com.spotify:artist_id'
        track_id_tag = '----:com.spotify:track_id'
        if artist_id_tag in audio.tags:
            spotify_ids['spotify_artist_ID'] = audio.tags[artist_id_tag][0].decode('utf-8')
        if track_id_tag in audio.tags:
            spotify_ids['spotify_track_ID'] = audio.tags[track_id_tag][0].decode('utf-8')
    except Exception as e:
        logger.error(f"Error extracting embedded Spotify IDs from {file_path}: {e}")
    return spotify_ids


def fetch_spotify_data_by_id(artist_id: str, track_id: str, sp: spotipy.Spotify) -> Dict[str, Any]:
    """
    Fetch Spotify track and artist details directly by their IDs.
    """
    spotify_data = {'spotify_artist_ID': artist_id, 'spotify_track_ID': track_id, 'spotify_duration_ms': '', 'spotify_genres': []}
    try:
        if track_id:
            spotify_track = sp.track(track_id)
            spotify_data['spotify_duration_ms'] = spotify_track.get('duration_ms', '')

        if artist_id:
            artist_info = sp.artist(artist_id)
            spotify_data['spotify_genres'] = artist_info.get('genres', [])[:5]

    except Exception as e:
        logger.error(f"Error fetching Spotify data by ID: artist_id={artist_id}, track_id={track_id}, error={e}")

    return spotify_data


def fetch_spotify_data(track: Dict[str, Any], sp: spotipy.Spotify) -> Dict[str, Any]:
    """
    Search Spotify by artist and track name if IDs are not available.
    """
    spotify_data = {'spotify_artist_ID': '', 'spotify_track_ID': '', 'spotify_duration_ms': '', 'spotify_genres': []}
    try:
        query = f"artist:{track['artist']} track:{track['track']}"
        logger.debug(f"Searching Spotify for '{track['artist']} - {track['track']}'")
        results = sp.search(q=query, type='track', limit=1)
        if results['tracks']['items']:
            spotify_track = results['tracks']['items'][0]
            spotify_data['spotify_artist_ID'] = spotify_track['artists'][0]['id']
            spotify_data['spotify_track_ID'] = spotify_track['id']
            spotify_data['spotify_duration_ms'] = spotify_track['duration_ms']
            artist_info = sp.artist(spotify_data['spotify_artist_ID'])
            spotify_data['spotify_genres'] = artist_info.get('genres', [])[:5]
    except Exception as e:
        logger.error(f"Error fetching Spotify data for {track['artist']} - {track['track']}: {e}")

    return spotify_data


def assign_spotify_genres(track: Dict[str, Any], spotify_data: Dict[str, Any]) -> None:
    for i in range(1, 6):
        genre_key = f'spotify_genre_{i}'
        track[genre_key] = spotify_data['spotify_genres'][i - 1] if i - 1 < len(spotify_data['spotify_genres']) else ''


def update_spotify_durations(data: List[Dict[str, Any]], sp: spotipy.Spotify) -> None:
    """
    Updates the 'spotify_duration_ms' field for tracks that have a 'spotify_track_ID' but lack 'spotify_duration_ms'.
    
    Args:
        data (List[Dict[str, Any]]): List of track dictionaries.
        sp (spotipy.Spotify): Authenticated Spotify client.
    """
    if not sp:
        logger.warning("Spotify client not initialized. Cannot update durations.")
        return

    tracks_to_update = [track for track in data if track.get('spotify_track_ID') and not track.get('spotify_duration_ms')]
    logger.info(f"Found {len(tracks_to_update)} tracks to update 'spotify_duration_ms'.")

    for index, track in enumerate(tracks_to_update, start=1):
        track_id = track['spotify_track_ID']
        try:
            logger.debug(f"Fetching duration for Spotify Track ID: {track_id} (Track {index}/{len(tracks_to_update)})")
            spotify_track = sp.track(track_id)
            duration_ms = spotify_track.get('duration_ms', '')
            if duration_ms:
                track['spotify_duration_ms'] = duration_ms
                logger.info(f"Updated 'spotify_duration_ms' for '{track['artist']} - {track['track']}': {duration_ms} ms")
            else:
                logger.warning(f"No 'duration_ms' found for Spotify Track ID: {track_id}")
        except spotipy.exceptions.SpotifyException as e:
            logger.error(f"Spotify API error while fetching duration for Track ID {track_id}: {e}")
        except Exception as e:
            logger.error(f"Unexpected error while fetching duration for Track ID {track_id}: {e}")

        # Respectful delay to avoid hitting rate limits
        time.sleep(random.uniform(0.2, 0.5))


def write_track_to_csv(track: Dict[str, Any], csv_writer: csv.DictWriter) -> None:
    fieldnames = csv_writer.fieldnames
    for field in fieldnames:
        if field not in track:
            track[field] = ''
    csv_writer.writerow(track)


def compute_stats_and_genres(data: List[Dict[str, Any]], genre_mapping: Dict[str, Dict[str, Any]]) -> (Dict[str, Any], List[tuple]):
    """
    Compute stats and genres solely from the final 'spawnre' field in each track.
    """
    # Basic stats
    total_tracks = len(data)
    tracks_with_genres = sum(1 for track in data if track.get('spawnre'))

    # Build a genre_to_hex map
    genre_to_hex = {
        details['Genre'].lower(): details['Hex'].replace('0x', '')
        for details in genre_mapping.values()
        if details['Genre']
    }

    # Count genres from the final 'spawnre' field
    genre_counts = defaultdict(int)
    for track in data:
        spawnre_field = track.get('spawnre', '')
        if spawnre_field:
            # spawnre is a comma-separated string of final genres
            genres = [g.strip().lower() for g in spawnre_field.split(',') if g.strip()]
            for g in genres:
                genre_counts[g] += 1

    # Sort genres by occurrence
    sorted_genres = sorted(
        [
            (genre, genre_to_hex.get(genre.lower(), 'Unknown'), count)
            for genre, count in genre_counts.items()
            if count > 0
        ],
        key=lambda x: x[2],
        reverse=True
    )

    stats = {
        'Total Tracks': total_tracks,
        'Tracks with Genres': tracks_with_genres
    }

    return stats, sorted_genres


def analyze_m3u(
    m3u_file: str,
    music_directory: str,
    lastfm_api_key: str,
    spotify_client_id: str,
    spotify_client_secret: str,
    generate_stats: bool,
    fetch_features: bool,
    audio_features_source: str,
    post: bool = False,
    csv_file: Optional[str] = None,
    loved_tracks: Optional[str] = None,
    loved_albums: Optional[str] = None,
    loved_artists: Optional[str] = None
) -> List[Dict[str, Any]]:
    """
    Analyzes an M3U playlist and saves musical characteristics in a CSV file.
    """
    # Sanitize input paths
    m3u_path = sanitize_path(m3u_file)
    music_dir_path = sanitize_path(music_directory)

    if post and csv_file:
        csv_path = sanitize_path(csv_file)
    else:
        csv_path = None

    # Initialize loved sets
    analyzed_tracks = []
    loved_tracks_set = set()
    loved_albums_set = set()
    loved_artists_set = set()

    # Open and parse the M3U file
    try:
        with open(m3u_file, 'r', encoding='utf-8') as m3u_file:
            for line in m3u_file:
                line = line.strip()
                if line and not line.startswith("#"):  # Skip empty lines and comments
                    track_path = Path(line).resolve()
                    analyzed_tracks.append({
                        'file_path': str(track_path),
                        'metadata': {},  # Placeholder for additional track metadata
                    })
        logger.debug(f"Total tracks analyzed: {len(analyzed_tracks)}")
    except Exception as e:
        logger.error(f"Failed to process M3U file: {e}")
        return

    # Process loved tracks, albums, and artists
    if loved_tracks:
        loved_tracks_path = sanitize_path(loved_tracks)
        loved_tracks_set = parse_m3u_for_loved(loved_tracks_path, music_dir_path, level='track')
        logger.debug(f"Loaded {len(loved_tracks_set)} loved tracks.")

    if loved_albums:
        loved_albums_path = sanitize_path(loved_albums)
        loved_albums_set = parse_m3u_for_loved(loved_albums_path, music_dir_path, level='album')
        logger.debug(f"Loaded {len(loved_albums_set)} loved albums.")

    if loved_artists:
        loved_artists_path = sanitize_path(loved_artists)
        loved_artists_set = parse_m3u_for_loved(loved_artists_path, music_dir_path, level='artist')
        logger.debug(f"Loaded {len(loved_artists_set)} loved artists.")

    # Normalize loved_*_set once for consistent case-insensitive comparisons
    loved_tracks_set = {Path(p).resolve().as_posix().lower() for p in loved_tracks_set}
    loved_albums_set = {Path(p).resolve().as_posix().lower() for p in loved_albums_set}
    loved_artists_set = {Path(p).resolve().as_posix().lower() for p in loved_artists_set}

    # Process each track and assign "loved" flags
    for track in analyzed_tracks:
        # Resolve and normalize the current track path
        track_path = Path(track['file_path']).resolve()
        track_path_str = track_path.as_posix().lower()

        # Perform comparisons directly with normalized sets
        track['loved_track'] = track_path_str in loved_tracks_set
        track['loved_album'] = track_path.parent.as_posix().lower() in loved_albums_set
        track['loved_artist'] = track_path.parent.parent.as_posix().lower() in loved_artists_set

        # Log debug information
        logger.debug(f"Track: {track_path}, Loved Track: {track['loved_track']}, "
                     f"Loved Album: {track['loved_album']}, Loved Artist: {track['loved_artist']}")

    # Initialize genre-related mappings
    data: List[Dict[str, Any]] = []
    artist_genre_count: Dict[str, Dict[str, int]] = defaultdict(lambda: defaultdict(int))
    artist_spawnre_tags: Dict[str, str] = {}

    # Build related_genre_map from genre_mapping
    related_genre_map: Dict[str, List[str]] = {}
    for code, details in genre_mapping.items():
        genre = details['Genre'].lower()
        related_codes = details.get('Related', [])
        related_genres = [
            genre_mapping[rel_code]['Genre'].lower()
            for rel_code in related_codes
            if genre_mapping.get(rel_code)
        ]
        if related_genres:
            related_genre_map[genre] = related_genres

    logger.debug(f"Constructed related_genre_map: {related_genre_map}")

    # Create a mapping from genre name to Hex value
    genre_to_hex = {
        details['Genre'].lower(): details['Hex'].replace('0x', '')
        for details in genre_mapping.values()
        if details['Genre']
    }

    # Always try to initialize Spotify client if credentials provided
    sp = None
    if spotify_client_id and spotify_client_secret:
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
            sp = None

    # Handle post-processing scenario
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

        # Process loved metadata
        for track_data in data:
            file_path = Path(track_data.get('file_path', '')).as_posix().lower()
            album_dir = Path(file_path).parent.as_posix().lower()
            artist_dir = Path(file_path).parent.parent.as_posix().lower()

            if loved_tracks_set:
                track_data['loved_tracks'] = 'yes' if file_path in loved_tracks_set else 'no'
            if loved_albums_set:
                track_data['loved_albums'] = 'yes' if album_dir in loved_albums_set else 'no'
            if loved_artists_set:
                track_data['loved_artists'] = 'yes' if artist_dir in loved_artists_set else 'no'

            logger.debug(
                f"Updated loved metadata for '{track_data['artist']} - {track_data['track']}': "
                f"loved_tracks={track_data.get('loved_tracks', '')}, "
                f"loved_albums={track_data.get('loved_albums', '')}, "
                f"loved_artists={track_data.get('loved_artists', '')}"
            )

    else:
        # Non-post-processing mode: parse M3U and process tracks
        try:
            with m3u_path.open('r', encoding='utf-8') as file:
                lines = file.readlines()
            logger.info(f"Opened M3U file: {m3u_path}")
        except Exception as e:
            logger.error(f"Error reading M3U file '{m3u_path}': {e}")
            return []

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

                if not file_path.is_file():
                    logger.warning(f"File path does not exist: {file_path}")
                    continue

                format_type = determine_format_using_metadata(track_info[1].strip(), track_info[0].strip(), file_path)

                if format_type == 'Track - Artist':
                    artist = track_info[1].strip()
                    track = track_info[0].strip()
                elif format_type == 'Artist - Track':
                    artist = track_info[0].strip()
                    track = track_info[1].strip()
                else:
                    artist = track_info[0].strip()
                    track = track_info[1].strip()

                # Initialize fields
                spotify_artist_id = ''
                spotify_track_id = ''
                spotify_duration_ms = ''
                file_duration_ms = ''
                embedded_genre = ''
                year = 'Unknown'

                try:
                    audio = MP4(str(file_path))
                    album_tag = audio.tags.get('\xa9alb', ['Unknown Album'])[0]

                    # Attempt to extract embedded genre from the iTunes-specific tag first
                    embedded_genre_list = audio.tags.get('----:com.apple.iTunes:genre')

                    # If the iTunes-specific tag isn't present, try the standard ©gen tag
                    if not embedded_genre_list:
                        embedded_genre_list = audio.tags.get('\xa9gen', [])

                    embedded_genre = embedded_genre_list[0].lower() if embedded_genre_list else ''

                    logger.info(f"Extracted embedded genre: {embedded_genre}")

                    file_duration_ms = int(audio.info.length * 1000) if hasattr(audio, 'info') and audio.info.length else 0
                    logger.info(f"Extracted file duration (ms): {file_duration_ms}")

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
                    logger.info(
                        f"Extracted MusicBrainz IDs for {file_path}: Artist ID = {mb_artistid}, "
                        f"Release Group ID = {mb_releasegroupid}, Track ID = {mb_trackid}"
                    )

                except Exception as e:
                    logger.error(f"Error reading metadata from {file_path}: {e}")
                    embedded_genre = ''
                    file_duration_ms = 0
                    mb_artistid = ''
                    mb_releasegroupid = ''
                    mb_trackid = ''
                    year = 'Unknown'

                last_fm_genres = fetch_genre_lastfm(artist, track, lastfm_api_key)
                spotify_genres = get_spotify_genres(artist, sp) if sp else []
                musicbrainz_genres = get_musicbrainz_genres(artist)

                combined_genres = combine_and_prioritize_genres_refined(
                    embedded_genre,
                    last_fm_genres,
                    spotify_genres,
                    musicbrainz_genres,
                    related_genre_map,
                    genre_mapping,
                    genre_synonyms,
                    artist.lower(),
                    artist_genre_count
                )

                closest_genres, spawnre_hex = find_closest_genre_matches(combined_genres, genre_mapping)

                logger.info(f"Final matched genres: {combined_genres}")
                logger.info(f"Spawnre Hex: {spawnre_hex}")
                logger.debug("-----------------------")

                spotify_genre_columns = {
                    f'spotify_genre_{i+1}': spotify_genres[i] if i < len(spotify_genres) else ''
                    for i in range(5)
                }
                last_fm_genre_columns = {
                    f'last_FM_genre_{i+1}': last_fm_genres[i] if i < len(last_fm_genres) else ''
                    for i in range(5)
                }
                musicbrainz_genre_columns = {
                    f'musicbrainz_genre_{i+1}': musicbrainz_genres[i] if i < len(musicbrainz_genres) else ''
                    for i in range(5)
                }

                # After extracting combined_genres and spawnre_hex:
                # Set loved_* fields
                normalized_file_path = file_path.as_posix().lower()
                album_dir = Path(file_path).parent.as_posix().lower()
                artist_dir = Path(album_dir).parent.as_posix().lower()

                track_dict = {
                    'artist': artist,
                    'album': album_tag,
                    'track': track,
                    'year': year,
                    'spawnre': ', '.join(closest_genres),
                    'spawnre_hex': spawnre_hex,
                    'spawnre_tag': '',  # Placeholder, will assign later
                    'embedded_genre': embedded_genre,
                    'musicbrainz_artist_ID': mb_artistid,
                    'musicbrainz_release_group_ID': mb_releasegroupid,
                    'musicbrainz_track_ID': mb_trackid,
                    'spotify_artist_ID': spotify_artist_id,
                    'spotify_track_ID': spotify_track_id,
                    'file_duration_ms': file_duration_ms,
                    'spotify_duration_ms': spotify_duration_ms,
                    'file_path': file_path.as_posix(),
                    'loved_tracks': 'yes' if normalized_file_path in loved_tracks_set else 'no',
                    'loved_albums': 'yes' if album_dir in loved_albums_set else 'no',
                    'loved_artists': 'yes' if artist_dir in loved_artists_set else 'no'
                }

                track_dict.update(spotify_genre_columns)
                track_dict.update(last_fm_genre_columns)
                track_dict.update(musicbrainz_genre_columns)

                audio_feature_columns = [
                    'danceability', 'energy', 'key', 'loudness',
                    'mode', 'speechiness', 'acousticness', 'instrumentalness',
                    'liveness', 'valence', 'tempo', 'time_signature'
                ]
                for feature in audio_feature_columns:
                    track_dict[feature] = ''

                data.append(track_dict)

    # After processing all tracks
    if not post:
        # Determine spawnre_tag per artist
        for artist_lower, genres in artist_genre_count.items():
            if genres:
                most_frequent_genre = max(genres, key=genres.get)
                artist_spawnre_tags[artist_lower] = most_frequent_genre
                logger.debug(f"Assigned spawnre_tag for artist '{artist_lower}': {most_frequent_genre}")
            else:
                artist_spawnre_tags[artist_lower] = ''
                logger.debug(f"No genres found for artist '{artist_lower}'. spawnre_tag set to empty.")

        # Assign spawnre_tag to each track
        for track_data in data:
            artist_lower = track_data['artist'].lower()
            spawnre_tag = artist_spawnre_tags.get(artist_lower, '')
            track_data['spawnre_tag'] = spawnre_tag
            logger.debug(
                f"Assigned spawnre_tag for '{track_data['artist']} - {track_data['track']}': {spawnre_tag}"
            )

        # Populate Spotify IDs
        if sp:
            logger.info("Populating missing Spotify IDs...")
            populate_missing_spotify_ids(data, sp)
            logger.info("Completed populating Spotify IDs.")
        else:
            logger.warning("Spotify client not initialized. Skipping Spotify data population.")

    else:
        # Post-processing specific code...
        if post and csv_path:
            # Existing post-processing code...
            pass  # Already handled above

        # Assign spawnre_tag is already done above
        # Now, update spotify_duration_ms for tracks with spotify_track_ID

        if sp:
            logger.info("Updating missing Spotify durations...")
            update_spotify_durations(data, sp)
            logger.info("Completed updating Spotify durations.")
        else:
            logger.warning("Spotify client not initialized. Cannot update Spotify durations.")

    if post and csv_path:
        output_csv_path = csv_path
        stats_csv_path = csv_path.with_name(f"{csv_path.stem}_stats.csv")
    else:
        output_csv_path = m3u_path.with_suffix('.csv')
        stats_csv_path = m3u_path.with_name(f"{m3u_path.stem}_stats.csv")

    logger.debug(f"Output CSV path set to: {output_csv_path}")
    logger.debug(f"Stats CSV path set to: {stats_csv_path}")

    # Fetch audio features if requested
    if fetch_features:
        if audio_features_source.lower() == 'embedded':
            logger.info("Extracting audio features from embedded tags...")
            for track_data in data:
                file_path = track_data.get('file_path', '')
                if file_path:
                    try:
                        audio_features = extract_audio_features(file_path)
                        valid_features = {k: v for k, v in audio_features.items() if k in [
                            'danceability', 'energy', 'key', 'loudness',
                            'mode', 'speechiness', 'acousticness', 'instrumentalness',
                            'liveness', 'valence', 'tempo', 'time_signature'
                        ]}
                        track_data.update(valid_features)
                        logger.debug(
                            f"Extracted audio features for '{track_data['artist']} - {track_data['track']}': {valid_features}"
                        )
                    except Exception as e:
                        logger.error(
                            f"Error extracting embedded audio features for '{track_data['artist']} - {track_data['track']}': {e}"
                        )
                        for feature in ['danceability', 'energy', 'key', 'loudness',
                                        'mode', 'speechiness', 'acousticness', 'instrumentalness',
                                        'liveness', 'valence', 'tempo', 'time_signature']:
                            track_data[feature] = ''
            logger.info("Completed extracting embedded audio features.")
        elif audio_features_source.lower() == 'spotify' and sp:
            logger.info("Fetching Spotify audio features...")
            track_ids = [track_data['spotify_track_ID'] for track_data in data if track_data.get('spotify_track_ID')]
            if track_ids:
                try:
                    features_data = {}
                    for i in range(0, len(track_ids), 100):
                        batch_ids = track_ids[i:i+100]
                        response = sp.audio_features(tracks=batch_ids)
                        for feature in response:
                            if feature and feature['id']:
                                features_data[feature['id']] = feature
                    logger.debug(f"Fetched audio features data: {features_data}")

                    for track_data in data:
                        spotify_track_id = track_data.get('spotify_track_ID', '')
                        if spotify_track_id in features_data:
                            feature = features_data[spotify_track_id]
                            audio_feature_updates = {
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
                                'time_signature': feature.get('time_signature', '')
                            }
                            track_data.update(audio_feature_updates)
                            logger.debug(
                                f"Fetched Spotify audio features for '{track_data['artist']} - {track_data['track']}': {audio_feature_updates}"
                            )
                except Exception as e:
                    logger.error(f"Error fetching Spotify audio features: {e}")
            else:
                logger.warning("No Spotify Track IDs found to fetch audio features.")
            logger.info("Completed fetching Spotify audio features.")
        else:
            logger.info("Skipping audio features extraction as per 'none' option.")

    fieldnames = [
        'artist', 'album', 'track', 'year', 'spawnre', 'spawnre_hex', 'spawnre_tag',
        'embedded_genre', 'musicbrainz_artist_ID', 'musicbrainz_release_group_ID',
        'musicbrainz_track_ID', 'spotify_artist_ID', 'spotify_track_ID',
        'file_duration_ms', 'spotify_duration_ms', 'file_path',
        'spotify_genre_1', 'spotify_genre_2', 'spotify_genre_3',
        'spotify_genre_4', 'spotify_genre_5',
        'last_FM_genre_1', 'last_FM_genre_2', 'last_FM_genre_3',
        'last_FM_genre_4', 'last_FM_genre_5',
        'musicbrainz_genre_1', 'musicbrainz_genre_2', 'musicbrainz_genre_3',
        'musicbrainz_genre_4', 'musicbrainz_genre_5',
        'danceability', 'energy', 'key', 'loudness', 'mode',
        'speechiness', 'acousticness', 'instrumentalness',
        'liveness', 'valence', 'tempo', 'time_signature',
        'loved_tracks', 'loved_albums', 'loved_artists'
    ]

    # Write the final CSV using process_tracks to ensure Spotify data is fetched
    try:
        with output_csv_path.open('w', newline='', encoding='utf-8') as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()
            for track_data in data:
                writer.writerow(track_data)

        logger.info(f"\nMain CSV file created successfully: {output_csv_path}")
    except Exception as e:
        logger.error(f"Error writing main CSV file: {e}")

    if generate_stats:
        # Re-compute stats and sorted genres regardless of post or not
        stats, sorted_genres = compute_stats_and_genres(data, genre_mapping)

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
                for genre, hex_value, count in sorted_genres:
                    writer.writerow([genre, hex_value, count])
                    logger.debug(f"Wrote genre stat to CSV: Genre={genre}, Hex={hex_value}, Count={count}")

            logger.info(f"Stats CSV file created successfully: {stats_csv_path}\n")
        except Exception as e:
            logger.error(f"Error writing stats CSV file: {e}")

    return data


# ---------------------------- Entry Point ----------------------------

if __name__ == "__main__":
    import argparse

    def main():
        parser = argparse.ArgumentParser(description="SpawnreDJ: Analyze M3U playlists and generate CSV reports.")
        parser.add_argument('--m3u', type=str, help='Path to the M3U playlist file.')
        parser.add_argument('--music_dir', type=str, help='Root directory of the music files.')
        parser.add_argument('--lastfm_api_key', type=str, help='API key for Last.fm.')
        parser.add_argument('--spotify_client_id', type=str, help='Spotify API client ID.')
        parser.add_argument('--spotify_client_secret', type=str, help='Spotify API client secret.')
        parser.add_argument('--generate_stats', action='store_true', help='Generate a stats CSV.')
        parser.add_argument('--fetch_features', action='store_true', help='Fetch Spotify audio features.')
        parser.add_argument('--audio_features_source', type=str, choices=['embedded', 'spotify', 'none'], default='none', help='Source for audio features extraction.')
        parser.add_argument('--post', action='store_true', help='Perform post-processing.')
        parser.add_argument('--csv_file', type=str, help='Path to an existing CSV file for post-processing.')
        parser.add_argument('--loved_tracks', type=str, help='Path to a loved tracks M3U file.')
        parser.add_argument('--loved_albums', type=str, help='Path to a loved albums M3U file.')
        parser.add_argument('--loved_artists', type=str, help='Path to a loved artists M3U file.')

        args = parser.parse_args()

        if not args.m3u and not args.post:
            logger.error("Error: Either M3U playlist file or post-processing mode must be specified.")
            parser.print_help()
            return

        if not args.post:
            if not args.m3u or not args.music_dir:
                logger.error("Error: M3U playlist file and music directory are required for analysis.")
                parser.print_help()
                return

        if args.post and not args.csv_file:
            logger.error("Error: CSV file must be specified for post-processing.")
            parser.print_help()
            return

        # Validate audio_features_source when fetch_features is True
        if args.fetch_features and not args.audio_features_source:
            logger.error("Error: Audio features source must be specified when fetch_features is enabled.")
            parser.print_help()
            return

        analyze_m3u(
            m3u_file=args.m3u or '',
            music_directory=args.music_dir or '',
            lastfm_api_key=args.lastfm_api_key or '',
            spotify_client_id=args.spotify_client_id or '',
            spotify_client_secret=args.spotify_client_secret or '',
            generate_stats=args.generate_stats,
            fetch_features=args.fetch_features,
            audio_features_source=args.audio_features_source,
            post=args.post,
            csv_file=args.csv_file,
            loved_tracks=args.loved_tracks,
            loved_albums=args.loved_albums,
            loved_artists=args.loved_artists
        )

    main()
