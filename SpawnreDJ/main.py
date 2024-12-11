# main.py

import logging  # Import logging first to configure it before other modules

import pandas as pd
import argparse
import os
import sys
import getpass
from types import SimpleNamespace
from dotenv import load_dotenv
from pathlib import Path

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,  # Set to INFO to suppress DEBUG messages
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler()  # Output logs to console
        # You can add FileHandler here if you want to log to a file
    ]
)

# Define logger here
logger = logging.getLogger(__name__)

# Now import other modules after configuring logging
from SpawnreDJ.M3U_from_folder import generate_m3u
from SpawnreDJ.folder_from_M3U import copy_tracks_with_sequence, copy_all_tracks_with_sequence, copy_all_tracks_without_sequence, sanitize_path, validate_path
from SpawnreDJ.anal_M3U import analyze_m3u
from SpawnreDJ.M3U_from_CSV import generate_curated_m3u
from SpawnreDJ.organ_music import organize_music

def load_api_credentials(env_path='APIds.env'):
    """
    Load API credentials from the specified .env file.
    Returns a dictionary with keys: lastfm_api_key, spotify_client_id, spotify_client_secret
    """
    if not os.path.exists(env_path):
        # Create the file with blank values if it doesn't exist
        with open(env_path, 'w') as f:
            f.write("LASTFM_API_KEY=\n")
            f.write("SPOTIFY_CLIENT_ID=\n")
            f.write("SPOTIFY_CLIENT_SECRET=\n")
        print(f"Created {env_path} with blank API credentials.")

    load_dotenv(dotenv_path=env_path)
    lastfm_api_key = os.getenv('LASTFM_API_KEY', '').strip()
    spotify_client_id = os.getenv('SPOTIFY_CLIENT_ID', '').strip()
    spotify_client_secret = os.getenv('SPOTIFY_CLIENT_SECRET', '').strip()
    return {
        'lastfm_api_key': lastfm_api_key,
        'spotify_client_id': spotify_client_id,
        'spotify_client_secret': spotify_client_secret
    }

def save_api_credentials(env_path='APIds.env', credentials=None):
    """
    Save API credentials to the specified .env file.
    """
    if credentials is None:
        credentials = {}
    with open(env_path, 'w') as env_file:
        env_file.write(f"LASTFM_API_KEY={credentials.get('lastfm_api_key', '')}\n")
        env_file.write(f"SPOTIFY_CLIENT_ID={credentials.get('spotify_client_id', '')}\n")
        env_file.write(f"SPOTIFY_CLIENT_SECRET={credentials.get('spotify_client_secret', '')}\n")
    print(f"API credentials saved to {env_path}.")

def prompt_for_credentials(credentials):
    """
    Prompt the user to input missing API credentials.
    Updates the credentials dictionary in-place.
    """
    if not credentials.get('lastfm_api_key'):
        credentials['lastfm_api_key'] = getpass.getpass("Enter your Last.fm API Key: ").strip()
    if not credentials.get('spotify_client_id'):
        credentials['spotify_client_id'] = getpass.getpass("Enter your Spotify Client ID: ").strip()
    if not credentials.get('spotify_client_secret'):
        credentials['spotify_client_secret'] = getpass.getpass("Enter your Spotify Client Secret: ").strip()

def run_m3u_from_folder(music_dir_str, flip, path_prefix, m3u_file_path_str):
    music_dir = Path(music_dir_str)
    m3u_file_path = Path(m3u_file_path_str)
    success = generate_m3u(music_dir, m3u_file_path, flip_order=flip, path_prefix=path_prefix)
    if success:
        print(f"Playlist generated at {m3u_file_path}")
    else:
        print("Failed to generate playlist.")

def run_folder_from_m3u():
    """
    Handle Option 4: Organize files & folders for your music collection.
    """
    try:
        # Prompt the user to decide whether to copy tracks instead of changing files & folders directly
        copy_choice = input("\nWould you like to copy tracks instead of changing files & folders directly? (y/n) [y]: ").strip().lower()
        if not copy_choice:
            copy_choice = 'y'  # Default to 'y'

        if copy_choice == 'y':
            # Prompt if the user wants to use filename prefix from an M3U playlist order
            prefix_choice = input("Would you like to use filename prefix from an M3U playlist order? (y/n) [n]: ").strip().lower()
            if not prefix_choice:
                prefix_choice = 'n'  # Default to 'n'

            if prefix_choice == 'y':
                # Prompt for M3U playlist path
                m3u_file = input("Enter the path to the M3U playlist file: ").strip()
                # Prompt for source music directory
                music_dir = input("Enter the path to the source music directory: ").strip()
                # Prompt for destination folder
                output_folder = input("Enter the path to the destination folder: ").strip()
                # Prompt for maximum cumulative size
                max_size_input = input("Enter the maximum cumulative size in GB (or leave blank for no limit): ").strip()

                # Sanitize and Resolve Paths
                m3u_file_path = sanitize_path(m3u_file)
                music_dir_path = sanitize_path(music_dir)
                output_folder_path = sanitize_path(output_folder)

                # Validate Paths
                if not validate_path(m3u_file_path, "M3U playlist file"):
                    print(f"Error: The M3U file '{m3u_file_path}' does not exist.")
                    return

                if not validate_path(music_dir_path, "music directory"):
                    print(f"Error: The music directory '{music_dir_path}' does not exist or is not a directory.")
                    return

                if not output_folder_path.exists():
                    try:
                        output_folder_path.mkdir(parents=True, exist_ok=True)
                        print(f"Created destination folder: {output_folder_path}")
                    except Exception as e:
                        print(f"Error creating destination folder '{output_folder_path}': {e}")
                        return

                # Parse Maximum Size Input
                try:
                    max_size_gb = float(max_size_input) if max_size_input else None
                except ValueError:
                    print("Invalid input for maximum size. Please enter a numerical value.")
                    return

                # Proceed with copying and organizing
                success_count, failure_count = copy_tracks_with_sequence(
                    m3u_file=str(m3u_file_path),
                    music_dir=str(music_dir_path),
                    output_folder=str(output_folder_path),
                    max_size_gb=max_size_gb,
                    base_path=str(music_dir_path)
                )
                print(f"Successfully copied {success_count} tracks.")
                print(f"{failure_count} tracks failed to copy.")

                # Do NOT prompt for organizing since prefixing was applied
                print("\nSkipping music organization as prefixing from M3U was applied.")
                logger.info("Skipping music organization as prefixing from M3U was applied.")

            else:
                # User chose not to use filename prefix from M3U; copy all tracks without M3U
                # Prompt for source music directory
                music_dir = input("Enter the path to the source music directory: ").strip()
                # Prompt for destination folder
                output_folder = input("Enter the path to the destination folder: ").strip()
                # Prompt for maximum cumulative size
                max_size_input = input("Enter the maximum cumulative size in GB (or leave blank for no limit): ").strip()

                # Sanitize and Resolve Paths
                music_dir_path = sanitize_path(music_dir)
                output_folder_path = sanitize_path(output_folder)

                # Validate Paths
                if not validate_path(music_dir_path, "music directory"):
                    print(f"Error: The music directory '{music_dir_path}' does not exist or is not a directory.")
                    return

                if not validate_path(output_folder_path, "output directory"):
                    print(f"Error: The output directory '{output_folder_path}' does not exist.")
                    return

                # Create destination folder if it doesn't exist
                if not output_folder_path.exists():
                    try:
                        output_folder_path.mkdir(parents=True, exist_ok=True)
                        print(f"Created destination folder: {output_folder_path}")
                    except Exception as e:
                        print(f"Error creating destination folder '{output_folder_path}': {e}")
                        return

                # Parse Maximum Size Input
                try:
                    max_size_gb = float(max_size_input) if max_size_input else None
                except ValueError:
                    print("Invalid input for maximum size. Please enter a numerical value.")
                    return

                # Proceed with copying all tracks without using M3U
                success_count, failure_count = copy_all_tracks_without_sequence(
                    music_dir=str(music_dir_path),
                    output_folder=str(output_folder_path),
                    max_size_gb=max_size_gb,
                    dry_run=False
                )
                print(f"Successfully copied {success_count} tracks.")
                print(f"{failure_count} tracks failed to copy.")

                # Ask if the user wants to organize the copied files
                organize_choice = input("\nWould you like to organize the copied music files? (y/n) [n]: ").strip().lower()
                if not organize_choice:
                    organize_choice = 'n'  # Default to 'n'

                if organize_choice == 'y':
                    # Prompt for format strings
                    print("\nEnter the format string for filenames (use placeholders like {title}, {D}, {TR}, etc.).")
                    print("Default format: {title}")
                    filename_format = input("Filename format: ").strip() or "{title}"

                    print("\nEnter the format string for artist folders (use placeholders like {artist}, {MB_artistID}, etc.).")
                    print("Leave blank to skip artist folder organization.")
                    artist_folder_format = input("Artist folder format: ").strip() or None

                    print("\nEnter the format string for album folders (use placeholders like {album}, {MB_albumID}, etc.).")
                    print("Leave blank to skip album folder organization.")
                    album_folder_format = input("Album folder format: ").strip() or None

                    # Call the organize_music function from organ_music.py
                    print("\nOrganizing music files...")
                    organize_music(
                        input_dir=os.path.join(output_folder_path, 'Music'),
                        filename_format=filename_format,
                        album_folder_format=album_folder_format,
                        artist_folder_format=artist_folder_format
                    )
                    print("Music organization complete.")
                else:
                    print("Skipping music organization.")
                    logger.info("Skipping music organization as per user choice.")
        else:
            # User chose not to copy tracks; proceed to organize existing files directly
            print("\nProceeding to organize files & folders directly.")

            # Prompt for music directory to organize
            music_dir = input("Enter the path to the music directory to organize: ").strip()

            # Sanitize and Resolve Paths
            music_dir_path = sanitize_path(music_dir)

            # Validate music directory
            if not validate_path(music_dir_path, "music directory"):
                print(f"Error: The music directory '{music_dir_path}' does not exist or is not a directory.")
                return

            # Prompt for format strings
            print("\nEnter the format string for filenames (use placeholders like {title}, {D}, {TR}, etc.).")
            print("Default format: {title}")
            filename_format = input("Filename format: ").strip() or "{title}"

            print("\nEnter the format string for artist folders (use placeholders like {artist}, {MB_artistID}, etc.).")
            print("Leave blank to skip artist folder organization.")
            artist_folder_format = input("Artist folder format: ").strip() or None

            print("\nEnter the format string for album folders (use placeholders like {album}, {MB_albumID}, etc.).")
            print("Leave blank to skip album folder organization.")
            album_folder_format = input("Album folder format: ").strip() or None

            # Call the organize_music function from organ_music.py
            print("\nOrganizing music files...")
            organize_music(
                input_dir=str(music_dir_path),
                filename_format=filename_format,
                album_folder_format=album_folder_format,
                artist_folder_format=artist_folder_format
            )
            print("Music organization complete.")
    except Exception as e:
        logger.error(f"An unexpected error occurred in run_folder_from_m3u: {e}")
        print(f"An unexpected error occurred: {e}")

def run_analyze_m3u(credentials, args):
    """
    Wrapper function to analyze an M3U playlist for genres and audio features.
    """
    analyze_m3u(
        m3u_file=args.m3u_file,
        music_directory=args.music_directory,
        lastfm_api_key=credentials['lastfm_api_key'],
        spotify_client_id=credentials['spotify_client_id'],
        spotify_client_secret=credentials['spotify_client_secret'],
        generate_stats=args.stats,
        fetch_features=args.fetch_features,  # Updated to args.fetch_features
        audio_features_source=args.audio_features_source,
        post=args.post,
        csv_file=args.csv_file,
        loved_tracks=args.loved_tracks,
        loved_albums=args.loved_albums,
        loved_artists=args.loved_artists
    )

def run_spawnre_csv(csv_file, shuffle=False, loved=None):
    csv_dir = os.path.dirname(os.path.abspath(csv_file))
    
    args = SimpleNamespace(
        csv_file=csv_file,
        shuffle=shuffle,
        loved=loved  # Ensure 'loved' is added to args here
    )
    
    generate_curated_m3u(args)

def main():
    try:
        # Load API credentials
        credentials = load_api_credentials()

        # Check for missing credentials
        missing_credentials = [key for key, value in credentials.items() if not value]
        if missing_credentials:
            print("Some API credentials are missing. Please enter the required values.")
            prompt_for_credentials(credentials)
            save_api_credentials(credentials=credentials)
        else:
            print("API credentials loaded from APIds.env.")

        print("\nWelcome to SpawnreDJ!")
        print("\nOptions:")
        print("1. Generate an M3U playlist from a folder")
        print("2. Analyze an M3U playlist and save musical characteristics in a CSV file")
        print("3. Generate a curated M3U playlist from a pre-generated analysis CSV file")
        print("4. Organize files & folders for your music collection")

        choice = input("\nEnter your choice (or leave blank to exit): ").strip()

        if not choice:
            print("Exiting SpawnreDJ.")
            return

        if choice == "1":
            music_dir = input("Enter the path to the music directory: ").strip()
            flip_input = input("Enter 'y' to flip or leave blank for default (Track - Artist): ").strip().lower()
            flip = flip_input == 'y'
            path_prefix_input = input("Enter the path prefix to add or leave blank for default ('../'): ").strip() or '../'
            m3u_file_path = input("Enter the path for the output M3U playlist or leave blank for default (same location as music directory): ").strip()
            
            if not m3u_file_path:
                m3u_file_path = Path(music_dir).parent / "playlist.m3u"
                print(f"No output path provided. Using default path: {m3u_file_path}")
            else:
                m3u_path = Path(m3u_file_path)
                if m3u_path.is_dir() or m3u_path.suffix.lower() != '.m3u':
                    print("Error: Please provide a full file path including the filename with a '.m3u' extension.")
                    return

            run_m3u_from_folder(music_dir, flip, path_prefix=path_prefix_input, m3u_file_path_str=m3u_file_path)
        elif choice == "2":
            m3u_file = input("Enter the path to the M3U playlist file: ").strip()
            music_directory = input("Enter the root directory of the music files: ").strip()
            generate_stats = input("\nGenerate stats CSV? (y/n) [n]: ").strip().lower() == 'y'

            # Updated prompt for audio features
            print("\nHow would you like to extract audio features?")
            print("1. Extract from embedded tags (local metadata).")
            print("2. Fetch from Spotify API.")
            print("3. Skip audio features.")
            audio_features_choice = input("Enter your choice (1, 2, or 3) [1]: ").strip()

            # Assign default value if input is empty
            if not audio_features_choice:
                audio_features_choice = "1"

            if audio_features_choice == "1":
                audio_features_source = "embedded"
            elif audio_features_choice == "2":
                audio_features_source = "spotify"
            elif audio_features_choice == "3":
                audio_features_source = "none"
            else:
                print("Invalid choice. Defaulting to skipping audio features.")
                audio_features_source = "none"

            post = input("\nUse an existing CSV file? (y/n) [n]: ").strip().lower() == 'y'
            
            csv_file = None
            if post:
                csv_file = input("Enter the path to the existing CSV file: ").strip()
                if not os.path.isfile(csv_file):
                    print(f"Error: The CSV file '{csv_file}' does not exist.")
                    return

            loved_tracks = input("\nEnter the path to the loved tracks M3U file (or leave blank to skip): ").strip() or None
            loved_albums = input("Enter the path to the loved albums M3U file (or leave blank to skip): ").strip() or None
            loved_artists = input("Enter the path to the loved artists M3U file (or leave blank to skip): ").strip() or None

            # Updated 'features' mapping
            features = audio_features_source in ["spotify", "embedded"]

            # Create a SimpleNamespace object to hold the arguments
            args = SimpleNamespace(
                m3u_file=m3u_file,
                music_directory=music_directory,
                stats=generate_stats,
                fetch_features=features,  # Renamed for clarity
                audio_features_source=audio_features_source,  # Pass the source choice
                post=post,
                csv_file=csv_file,
                loved_tracks=loved_tracks,
                loved_albums=loved_albums,
                loved_artists=loved_artists
            )
            run_analyze_m3u(credentials, args)
        elif choice == "3":
            csv_file = input("Enter the path to the CSV file: ").strip()
            shuffle = input("Curate the tracks within each cluster? (y/n) [n]: ").strip().lower() == 'y'
            loved_input = input("Filter by loved tracks, albums, or artists (e.g., 'tracks albums') or leave blank: ").strip()
            loved = loved_input.split() if loved_input else None
            run_spawnre_csv(csv_file=csv_file, shuffle=shuffle, loved=loved)
        elif choice == "4":
            run_folder_from_m3u()
        else:
            print("Invalid choice. Please select a valid option.")
    except Exception as e:
        logger.error(f"An unexpected error occurred in main: {e}")
        print(f"An unexpected error occurred: {e}")

if __name__ == "__main__":
    main()
