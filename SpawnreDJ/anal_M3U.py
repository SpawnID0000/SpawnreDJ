# anal_M3U.py

import csv
import logging
import requests
import time
import random
from typing import List, Tuple, Dict, Any, Optional

from mutagen.mp4 import MP4
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
    if artist_name in spotify_genre_cache:
        logger.debug(f"Spotify genres for '{artist_name}' fetched from cache.")
        return spotify_genre_cache[artist_name]

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
        if genre.lower() != artist_name.lower() and any(value['Genre'].lower() == genre.lower() for value in genre_mapping.values())
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


def parse_m3u_for_loved(m3u_file: Path, music_directory: Path) -> set:
    loved_paths = set()
    if m3u_file.exists():
        with m3u_file.open('r', encoding='utf-8') as file:
            for line in file:
                line = line.strip()
                if not line.startswith('#') and line:
                    track_path = (music_directory / line).resolve() if not Path(line).is_absolute() else Path(line).resolve()
                    normalized_path = track_path.as_posix().lower()
                    loved_paths.add(normalized_path)
                    logger.debug(f"Added loved path: {normalized_path}")
    else:
        logger.warning(f"Loved M3U file '{m3u_file}' does not exist.")
    return loved_paths


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


def populate_missing_spotify_ids(data: List[Dict[str, Any]], sp: spotipy.Spotify) -> None:
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
            logger.debug(f"Searching Spotify for '{artist} - {track}'")
            result = sp.search(q=query, type='track', limit=1)
            if result['tracks']['items']:
                track_item = result['tracks']['items'][0]
                spotify_track_id = track_item['id']
                spotify_artist_id = track_item['artists'][0]['id'] if track_item['artists'] else ''
                spotify_duration_ms = track_item.get('duration_ms', 0)

                # Fetch artist genres with caching
                spotify_genres = get_spotify_genres(artist, sp)

                # Populate the track data
                track_data['spotify_track_ID'] = spotify_track_id
                track_data['spotify_artist_ID'] = spotify_artist_id
                track_data['spotify_duration_ms'] = spotify_duration_ms

                # Populate up to 5 genres
                for i in range(1, 6):
                    genre_key = f'spotify_genre_{i}'
                    track_data[genre_key] = spotify_genres[i-1] if i-1 < len(spotify_genres) else ''

                logger.info(f"Populated Spotify data for '{artist} - {track}': Track ID = {spotify_track_id}, Artist ID = {spotify_artist_id}, Duration = {spotify_duration_ms} ms")
            else:
                logger.warning(f"No Spotify Track found for '{artist} - {track}'.")
        except spotipy.exceptions.SpotifyException as e:
            logger.error(f"Spotify API error for '{artist} - {track}': {e}")
        except Exception as e:
            logger.error(f"Unexpected error for '{artist} - {track}': {e}")


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


def analyze_m3u(
    m3u_file: str,
    music_directory: str,
    lastfm_api_key: str,
    spotify_client_id: str,
    spotify_client_secret: str,
    generate_stats: bool,
    fetch_features: bool,
    post: bool = False,
    csv_file: Optional[str] = None,
    loved_tracks: Optional[str] = None,
    loved_albums: Optional[str] = None,
    loved_artists: Optional[str] = None
) -> List[Dict[str, Any]]:
    # Sanitize input paths
    m3u_path = sanitize_path(m3u_file)
    music_dir_path = sanitize_path(music_directory)

    if post and csv_file:
        csv_path = sanitize_path(csv_file)
    else:
        csv_path = None

    # Initialize loved sets
    loved_tracks_set = set()
    loved_albums_set = set()
    loved_artists_set = set()

    if loved_tracks:
        loved_tracks_path = sanitize_path(loved_tracks)
        loved_tracks_set = parse_m3u_for_loved(loved_tracks_path, music_dir_path)
        logger.debug(f"Loaded {len(loved_tracks_set)} loved tracks.")

    if loved_albums:
        loved_albums_path = sanitize_path(loved_albums)
        loved_albums_set = parse_m3u_for_loved(loved_albums_path, music_dir_path)
        logger.debug(f"Loaded {len(loved_albums_set)} loved albums.")

    if loved_artists:
        loved_artists_path = sanitize_path(loved_artists)
        loved_artists_set = parse_m3u_for_loved(loved_artists_path, music_dir_path)
        logger.debug(f"Loaded {len(loved_artists_set)} loved artists.")

    data: List[Dict[str, Any]] = []
    artist_spawnre_tags: Dict[str, str] = {}
    genre_counts: Dict[str, int] = defaultdict(int)
    artist_genre_count: Dict[str, Dict[str, int]] = defaultdict(lambda: defaultdict(int))
    stats = {'Total Tracks': 0, 'Tracks with Genres': 0}

    # Build related_genre_map from genre_mapping
    related_genre_map: Dict[str, List[str]] = {}
    for code, details in genre_mapping.items():
        genre = details['Genre'].lower()
        related_codes = details.get('Related', [])
        related_genres = [genre_mapping[rel_code]['Genre'].lower() for rel_code in related_codes if rel_code in genre_mapping and genre_mapping[rel_code]['Genre']]
        if related_genres:
            related_genre_map[genre] = related_genres

    logger.debug(f"Constructed related_genre_map: {related_genre_map}")

    # Create a mapping from genre name to Hex value (ensure it's defined)
    genre_to_hex = {
        details['Genre'].lower(): details['Hex'].replace('0x', '')  # Remove '0x' prefix
        for details in genre_mapping.values()
        if details['Genre']
    }

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

        # Process loved metadata
        for track_data in data:
            # Normalize the file path for comparison
            file_path = Path(track_data.get('file_path', '')).as_posix().lower()
            normalized_file_path = Path(file_path)

            # Derive album and artist directories
            album_dir = Path(file_path).parent
            album_dir_normalized = album_dir.as_posix().lower()

            artist_dir = album_dir.parent
            artist_dir_normalized = artist_dir.as_posix().lower()

            # Check if the track, album, or artist is "loved"
            is_loved_track = 'yes' if file_path in loved_tracks_set else 'no'
            is_loved_album = 'yes' if album_dir_normalized in loved_albums_set else 'no'
            is_loved_artist = 'yes' if artist_dir_normalized in loved_artists_set else 'no'

            # Add the loved metadata
            track_data['loved_tracks'] = is_loved_track
            track_data['loved_albums'] = is_loved_album
            track_data['loved_artists'] = is_loved_artist

            logger.debug(f"Updated loved metadata for '{track_data['artist']} - {track_data['track']}': "
                         f"loved_tracks={is_loved_track}, loved_albums={is_loved_album}, loved_artists={is_loved_artist}")

        # Now, for tracks with missing fields, fetch data and assign values
        for track_data in data:
            artist = track_data.get('artist', '').strip()
            track = track_data.get('track', '').strip()
            if not artist or not track:
                logger.warning(f"Missing artist or track name for row: {track_data}")
                continue

            # Process embedded genre and year if missing
            if not track_data.get('embedded_genre') or not track_data.get('year') or not track_data.get('file_duration_ms'):
                file_path = Path(track_data.get('file_path', '')).resolve()
                if file_path.is_file():
                    try:
                        audio = MP4(str(file_path))
                        if not track_data.get('embedded_genre'):
                            embedded_genre_list = audio.tags.get('\xa9gen', [''])
                            embedded_genre = embedded_genre_list[0].lower() if embedded_genre_list else ''
                            track_data['embedded_genre'] = embedded_genre
                        if not track_data.get('year'):
                            year = audio.tags.get('\xa9day', ['Unknown'])[0]
                            track_data['year'] = year
                        if not track_data.get('file_duration_ms'):
                            file_duration_ms = int(audio.info.length * 1000) if hasattr(audio, 'info') and audio.info.length else 0
                            track_data['file_duration_ms'] = file_duration_ms
                    except Exception as e:
                        logger.error(f"Error reading metadata from {file_path}: {e}")
                else:
                    logger.warning(f"File does not exist: {file_path}")

            # Fetch MusicBrainz IDs if missing
            if not track_data.get('musicbrainz_artist_ID') or not track_data.get('musicbrainz_track_ID') or not track_data.get('musicbrainz_release_group_ID'):
                file_path = Path(track_data.get('file_path', '')).resolve()
                if file_path.is_file():
                    try:
                        audio = MP4(str(file_path))
                        if not track_data.get('musicbrainz_artist_ID'):
                            mb_artistid = (
                                audio.tags.get('----:com.apple.iTunes:MusicBrainz Artist Id', [b''])[0].decode('utf-8')
                                if '----:com.apple.iTunes:MusicBrainz Artist Id' in audio.tags else ''
                            )
                            track_data['musicbrainz_artist_ID'] = mb_artistid
                        if not track_data.get('musicbrainz_release_group_ID'):
                            mb_releasegroupid = (
                                audio.tags.get('----:com.apple.iTunes:MusicBrainz Release Group Id', [b''])[0].decode('utf-8')
                                if '----:com.apple.iTunes:MusicBrainz Release Group Id' in audio.tags else ''
                            )
                            track_data['musicbrainz_release_group_ID'] = mb_releasegroupid
                        if not track_data.get('musicbrainz_track_ID'):
                            mb_trackid = (
                                audio.tags.get('----:com.apple.iTunes:MusicBrainz Track Id', [b''])[0].decode('utf-8')
                                if '----:com.apple.iTunes:MusicBrainz Track Id' in audio.tags else ''
                            )
                            track_data['musicbrainz_track_ID'] = mb_trackid
                    except Exception as e:
                        logger.error(f"Error reading embedded MusicBrainz IDs from {file_path}: {e}")
                else:
                    logger.warning(f"File does not exist: {file_path}")

                # After trying to read from embedded tags, if still missing, fetch from API
                if not track_data.get('musicbrainz_artist_ID') or not track_data.get('musicbrainz_track_ID') or not track_data.get('musicbrainz_release_group_ID'):
                    album = track_data.get('album', '').strip()
                    musicbrainz_data = fetch_musicbrainz_ids_from_api(artist, track, album)
                    track_data['musicbrainz_artist_ID'] = track_data.get('musicbrainz_artist_ID') or musicbrainz_data.get('artist_id', '')
                    track_data['musicbrainz_release_group_ID'] = track_data.get('musicbrainz_release_group_ID') or musicbrainz_data.get('release_group_id', '')
                    track_data['musicbrainz_track_ID'] = track_data.get('musicbrainz_track_ID') or musicbrainz_data.get('track_id', '')

            # Fetch Spotify IDs and genres if missing
            if not track_data.get('spotify_artist_ID') or not track_data.get('spotify_track_ID'):
                # Fetch and populate Spotify IDs and genres
                try:
                    query = f"track:{track} artist:{artist}"
                    logger.debug(f"Searching Spotify for '{artist} - {track}'")
                    result = sp.search(q=query, type='track', limit=1)
                    if result['tracks']['items']:
                        track_item = result['tracks']['items'][0]
                        spotify_track_id = track_item['id']
                        spotify_artist_id = track_item['artists'][0]['id']
                        spotify_duration_ms = track_item['duration_ms']
                        spotify_genres = get_spotify_genres(artist, sp)

                        track_data['spotify_track_ID'] = spotify_track_id
                        track_data['spotify_artist_ID'] = spotify_artist_id
                        track_data['spotify_duration_ms'] = spotify_duration_ms

                        # Populate up to 5 genres
                        for i in range(1, 6):
                            genre_key = f'spotify_genre_{i}'
                            track_data[genre_key] = spotify_genres[i-1] if i-1 < len(spotify_genres) else ''
                        logger.info(f"Populated Spotify data for '{artist} - {track}': Track ID = {spotify_track_id}, Artist ID = {spotify_artist_id}, Duration = {spotify_duration_ms} ms")
                    else:
                        logger.warning(f"No Spotify Track found for '{artist} - {track}'.")
                except Exception as e:
                    logger.error(f"Error fetching Spotify data for '{artist} - {track}': {e}")

            # Fetch Last.fm genres if missing
            if not track_data.get('last_FM_genre_1'):
                last_fm_genres = fetch_genre_lastfm(artist, track, lastfm_api_key)
                for i in range(1, 6):
                    genre_key = f'last_FM_genre_{i}'
                    track_data[genre_key] = last_fm_genres[i-1] if i-1 < len(last_fm_genres) else ''

            # Fetch MusicBrainz genres if missing
            if not track_data.get('musicbrainz_genre_1'):
                musicbrainz_genres = get_musicbrainz_genres(artist)
                for i in range(1, 6):
                    genre_key = f'musicbrainz_genre_{i}'
                    track_data[genre_key] = musicbrainz_genres[i-1] if i-1 < len(musicbrainz_genres) else ''

            # Fetch genres and assign 'spawnre' if missing
            if not track_data.get('spawnre'):
                embedded_genre = track_data.get('embedded_genre', '').lower()

                # Fetch genres from various sources
                last_fm_genres = [track_data.get(f'last_FM_genre_{i}', '') for i in range(1, 6) if track_data.get(f'last_FM_genre_{i}', '')]
                spotify_genres = [track_data.get(f'spotify_genre_{i}', '') for i in range(1, 6) if track_data.get(f'spotify_genre_{i}', '')]
                musicbrainz_genres = [track_data.get(f'musicbrainz_genre_{i}', '') for i in range(1, 6) if track_data.get(f'musicbrainz_genre_{i}', '')]

                # Combine and prioritize genres
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

                # Find closest genre matches
                closest_genres, spawnre_hex = find_closest_genre_matches(combined_genres, genre_mapping)

                logger.info(f"Final matched genres for '{artist} - {track}': {closest_genres}")
                logger.info(f"Spawnre Hex: {spawnre_hex}")

                # Update track_data
                track_data['spawnre'] = ', '.join(closest_genres)
                track_data['spawnre_hex'] = spawnre_hex

                # Update per-artist genre counts
                for genre in closest_genres:
                    genre_lower = genre.lower()
                    genre_counts[genre_lower] += 1
                    artist_lower = artist.lower()
                    artist_genre_count[artist_lower][genre_lower] += 1
                    logger.debug(f"Genre '{genre_lower}' count updated to {genre_counts[genre_lower]} for artist '{artist_lower}'")
            else:
                # Process existing 'spawnre' field
                spawnre_str = track_data['spawnre']
                if spawnre_str:
                    # Split the comma-separated string into a list
                    spawnre_list = [genre.strip() for genre in spawnre_str.split(',') if genre.strip()]
                    if spawnre_list:
                        stats['Tracks with Genres'] += 1
                        for genre in spawnre_list:
                            genre_lower = genre.lower()
                            genre_counts[genre_lower] += 1
                            artist_lower = artist.lower()
                            artist_genre_count[artist_lower][genre_lower] += 1
                            logger.debug(f"Genre '{genre_lower}' count updated to {genre_counts[genre_lower]} for artist '{artist_lower}'")
                else:
                    # Handle the case where 'spawnre_str' is empty
                    pass

        # Update stats
        stats['Total Tracks'] = len(data)

        # Assign spawnre_tag based on most frequent main genre per artist
        for artist, genres in artist_genre_count.items():
            if genres:
                most_frequent_genre = max(genres, key=genres.get)
                artist_spawnre_tags[artist] = most_frequent_genre
                logger.debug(f"Assigned spawnre_tag for artist '{artist}': {most_frequent_genre}")
            else:
                artist_spawnre_tags[artist] = ''
                logger.debug(f"No genres found for artist '{artist}'. spawnre_tag set to empty.")

        # Assign spawnre_tag to all tracks by the artist
        for track_data in data:
            artist_lower = track_data['artist'].lower()
            spawnre_tag = artist_spawnre_tags.get(artist_lower, '')
            track_data['spawnre_tag'] = spawnre_tag
            logger.debug(f"Assigned spawnre_tag for '{track_data['artist']} - {track_data['track']}': {spawnre_tag}")

        # Aggregate genre_counts from artist_genre_count
        genre_counts = defaultdict(int)
        for artist, genres in artist_genre_count.items():
            for genre, count in genres.items():
                genre_counts[genre] += count
                logger.debug(f"Aggregated genre '{genre}' count to {genre_counts[genre]}")

        logger.info(f"Genre Counts: {dict(genre_counts)}")

        # Sort genres by occurrence count, highest first
        sorted_genres = sorted(
            [
                (
                    genre,
                    genre_to_hex.get(genre.lower(), 'Unknown'),
                    count
                )
                for genre, count in genre_counts.items()
                if count > 0
            ],
            key=lambda x: x[2],  # Sort by count (occurrences)
            reverse=True
        )

        logger.info(f"Sorted Genres: {sorted_genres}")

        # Determine the output CSV path (overwrite the existing CSV)
        output_csv_path = csv_path

        # Determine the stats CSV path
        stats_csv_path = csv_path.with_stem(csv_path.stem + '_stats').with_suffix('.csv')

    else:
        # Non-post-processing mode: parse M3U and process tracks
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

                # Check if file exists
                if not file_path.is_file():
                    logger.warning(f"File path does not exist: {file_path}")
                    continue

                # Determine the format using metadata
                format_type = determine_format_using_metadata(track_info[1].strip(), track_info[0].strip(), file_path)

                if format_type == 'Track - Artist':
                    artist = track_info[1].strip()
                    track = track_info[0].strip()
                elif format_type == 'Artist - Track':
                    artist = track_info[0].strip()
                    track = track_info[1].strip()
                else:
                    # Default to 'Artist - Track' if unknown
                    artist = track_info[0].strip()
                    track = track_info[1].strip()

                # Initialize variables
                spotify_artist_id = ''
                spotify_track_id = ''
                spotify_duration_ms = ''
                file_duration_ms = ''

                # Fetch embedded metadata
                try:
                    audio = MP4(str(file_path))
                    album_tag = audio.tags.get('\xa9alb', ['Unknown Album'])[0]

                    # Extract embedded genre
                    embedded_genre_list = audio.tags.get('\xa9gen', [''])
                    embedded_genre = embedded_genre_list[0].lower() if embedded_genre_list else ''
                    logger.info(f"Extracted embedded genre: {embedded_genre}")

                    # Get file duration in ms
                    file_duration_ms = int(audio.info.length * 1000) if hasattr(audio, 'info') and audio.info.length else 0
                    logger.info(f"Extracted file duration (ms): {file_duration_ms}")

                    # Extract MusicBrainz IDs
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
                spotify_genres = get_spotify_genres(artist, sp)
                musicbrainz_genres = get_musicbrainz_genres(artist)

                # Combine and prioritize genres
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

                # Find closest genre matches
                closest_genres, spawnre_hex = find_closest_genre_matches(combined_genres, genre_mapping)

                logger.info(f"Final matched genres: {combined_genres}")
                logger.info(f"Spawnre Hex: {spawnre_hex}")
                logger.debug("-----------------------")

                # Update per-artist genre counts
                for genre in closest_genres:
                    genre_lower = genre.lower()
                    genre_counts[genre_lower] += 1
                    artist_lower = artist.lower()
                    artist_genre_count[artist_lower][genre_lower] += 1
                    logger.debug(f"Genre '{genre_lower}' count updated to {genre_counts[genre_lower]} for artist '{artist_lower}'")

                # Fetch Spotify Track ID and Audio Features
                try:
                    logger.debug(f"Fetching Spotify Track ID for '{artist} - {track}'")
                    result = sp.search(q=f'track:{track} artist:{artist}', type='track', limit=1)
                    if result['tracks']['items']:
                        track_item = result['tracks']['items'][0]
                        spotify_track_id = track_item['id']
                        spotify_artist_id = track_item['artists'][0]['id']
                        spotify_duration_ms = track_item['duration_ms']
                        logger.info(f"Spotify Artist ID for {artist}: {spotify_artist_id}")
                        logger.info(f"Spotify Track ID for {track}: {spotify_track_id}")
                        logger.info(f"Spotify Duration: {spotify_duration_ms} ms")
                    else:
                        logger.warning(f"No Spotify Track found for '{artist} - {track}'.")
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
                    'spawnre': ', '.join(closest_genres),
                    'spawnre_hex': spawnre_hex,
                    'spawnre_tag': '',  # Placeholder
                    'embedded_genre': embedded_genre,
                    'musicbrainz_artist_ID': mb_artistid,
                    'musicbrainz_release_group_ID': mb_releasegroupid,
                    'musicbrainz_track_ID': mb_trackid,
                    'spotify_artist_ID': spotify_artist_id,
                    'spotify_track_ID': spotify_track_id,
                    'file_duration_ms': file_duration_ms,
                    'spotify_duration_ms': spotify_duration_ms,
                    'file_path': file_path.as_posix(),
                    'loved_tracks': 'no',    # Initialize as 'no'; will update later
                    'loved_albums': 'no',
                    'loved_artists': 'no'
                }

                # Merge genre columns
                track_dict.update(spotify_genre_columns)
                track_dict.update(last_fm_genre_columns)
                track_dict.update(musicbrainz_genre_columns)

                # Initialize audio feature columns as empty; will populate after fetching
                audio_feature_columns = [
                    'danceability', 'energy', 'key', 'loudness',
                    'mode', 'speechiness', 'acousticness', 'instrumentalness',
                    'liveness', 'valence', 'tempo', 'time_signature'
                ]
                for feature in audio_feature_columns:
                    track_dict[feature] = ''

                logger.debug(f"Appended track data: {track_dict}")

                # After track_dict is fully constructed, but before appending to data:
                normalized_file_path = Path(track_dict['file_path']).as_posix().lower()

                # Derive album & artist directories in lowercase
                album_dir = Path(normalized_file_path).parent.as_posix().lower()
                artist_dir = Path(album_dir).parent.as_posix().lower()

                # Check membership in loved sets
                track_dict['loved_tracks'] = 'yes' if normalized_file_path in loved_tracks_set else 'no'
                track_dict['loved_albums'] = 'yes' if album_dir in loved_albums_set else 'no'
                track_dict['loved_artists'] = 'yes' if artist_dir in loved_artists_set else 'no'

                data.append(track_dict)

        # Update stats
        stats['Total Tracks'] = len(data)
        stats['Tracks with Genres'] = sum(1 for track in data if track.get('spawnre'))

        # Assign spawnre_tag based on most frequent main genre per artist
        for artist, genres in artist_genre_count.items():
            if genres:
                most_frequent_genre = max(genres, key=genres.get)
                artist_spawnre_tags[artist] = most_frequent_genre
                logger.debug(f"Assigned spawnre_tag for artist '{artist}': {most_frequent_genre}")
            else:
                artist_spawnre_tags[artist] = ''
                logger.debug(f"No genres found for artist '{artist}'. spawnre_tag set to empty.")

        # Assign spawnre_tag to all tracks by the artist
        for track_data in data:
            artist_lower = track_data['artist'].lower()
            spawnre_tag = artist_spawnre_tags.get(artist_lower, '')
            track_data['spawnre_tag'] = spawnre_tag
            logger.debug(f"Assigned spawnre_tag for '{track_data['artist']} - {track_data['track']}': {spawnre_tag}")

        # Aggregate genre_counts from artist_genre_count
        genre_counts = defaultdict(int)
        for artist, genres in artist_genre_count.items():
            for genre, count in genres.items():
                genre_counts[genre] += count
                logger.debug(f"Aggregated genre '{genre}' count to {genre_counts[genre]}")

        logger.info(f"Genre Counts: {dict(genre_counts)}")

        # Sort genres by occurrence count, highest first
        sorted_genres = sorted(
            [
                (
                    genre,
                    genre_to_hex.get(genre.lower(), 'Unknown'),
                    count
                )
                for genre, count in genre_counts.items()
                if count > 0
            ],
            key=lambda x: x[2],  # Sort by count (occurrences)
            reverse=True
        )

        logger.info(f"Sorted Genres: {sorted_genres}")

        # Determine the output CSV path
        output_csv_path = m3u_path.with_suffix('.csv')
        stats_csv_path = m3u_path.with_stem(m3u_path.stem + '_stats').with_suffix('.csv')

    # Fetch audio features if requested
    if fetch_features:
        logger.info("Fetching Spotify audio features...")
        track_ids = [track_data['spotify_track_ID'] for track_data in data if track_data.get('spotify_track_ID')]
        features_data = fetch_audio_features(sp, track_ids)
        for track_data in data:
            spotify_track_id = track_data.get('spotify_track_ID', '')
            if spotify_track_id in features_data:
                feature = features_data[spotify_track_id]
                # Update track_data with audio features
                track_data.update({
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
                })

        logger.info("Completed fetching Spotify audio features.")

    fieldnames = [
        'artist', 'album', 'track', 'year', 'spawnre', 'spawnre_hex', 'spawnre_tag', 'embedded_genre',
        'musicbrainz_artist_ID', 'musicbrainz_release_group_ID', 'musicbrainz_track_ID',
        'spotify_artist_ID', 'spotify_track_ID', 'file_duration_ms', 'spotify_duration_ms',
        'file_path',
        'spotify_genre_1', 'spotify_genre_2', 'spotify_genre_3', 'spotify_genre_4', 'spotify_genre_5',
        'last_FM_genre_1', 'last_FM_genre_2', 'last_FM_genre_3', 'last_FM_genre_4', 'last_FM_genre_5',
        'musicbrainz_genre_1', 'musicbrainz_genre_2', 'musicbrainz_genre_3', 'musicbrainz_genre_4', 'musicbrainz_genre_5',
        'danceability', 'energy', 'key', 'loudness', 'mode', 'speechiness', 'acousticness',
        'instrumentalness', 'liveness', 'valence', 'tempo', 'time_signature',
        'loved_tracks', 'loved_albums', 'loved_artists'
    ]

    try:
        with output_csv_path.open('w', newline='', encoding='utf-8') as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()

            for track_data in data:
                # Ensure all fields are present
                for field in fieldnames:
                    if field not in track_data:
                        track_data[field] = ''

                writer.writerow(track_data)
                logger.debug(f"Wrote track data to CSV: {track_data}")

        logger.info(f"\nMain CSV file created successfully: {output_csv_path}")
    except Exception as e:
        logger.error(f"Error writing main CSV file: {e}")

    # Writing stats CSV if requested
    if generate_stats:
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

                logger.debug(f"Sorted genres for stats: {sorted_genres}")

                # Write each genre's stats to the CSV
                for genre, hex_value, count in sorted_genres:
                    writer.writerow([genre, hex_value, count])
                    logger.debug(f"Wrote genre stat to CSV: Genre={genre}, Hex={hex_value}, Count={count}")

            logger.info(f"Stats CSV file created successfully: {stats_csv_path}\n")
        except Exception as e:
            logger.error(f"Error writing stats CSV file: {e}")

    return data  # Return data for further processing if needed

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

        analyze_m3u(
            m3u_file=args.m3u or '',
            music_directory=args.music_dir or '',
            lastfm_api_key=args.lastfm_api_key or '',
            spotify_client_id=args.spotify_client_id or '',
            spotify_client_secret=args.spotify_client_secret or '',
            generate_stats=args.generate_stats,
            fetch_features=args.fetch_features,
            post=args.post,
            csv_file=args.csv_file,
            loved_tracks=args.loved_tracks,
            loved_albums=args.loved_albums,
            loved_artists=args.loved_artists
        )

    main()
