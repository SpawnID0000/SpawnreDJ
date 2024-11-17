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
    level=logging.INFO,  # Set to INFO to suppress DEBUG messages
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler()  # Output logs to console
        # You can add FileHandler here if you want to log to a file
    ]
)

# Now import other modules AFTER configuring logging
from SpawnreDJ.M3U_from_folder import generate_m3u
from SpawnreDJ.folder_from_M3U import copy_tracks_with_sequence
from SpawnreDJ.anal_M3U import analyze_m3u
from SpawnreDJ.M3U_from_CSV import generate_curated_m3u


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


def run_folder_from_m3u(m3u_file, music_dir, output_folder, max_size_gb=None):
    """
    Wrapper function to copy tracks from an M3U playlist to a new folder.
    """
    if not os.path.isfile(m3u_file):
        print(f"Error: The M3U file '{m3u_file}' does not exist.")
        return

    if not os.path.isdir(music_dir):
        print(f"Error: The music directory '{music_dir}' does not exist or is not a directory.")
        return

    if not os.path.isdir(output_folder):
        try:
            os.makedirs(output_folder, exist_ok=True)
            print(f"Created output folder: {output_folder}")
        except Exception as e:
            print(f"Error creating output folder '{output_folder}': {e}")
            return

    success_count, failure_count = copy_tracks_with_sequence(m3u_file, music_dir, output_folder, max_size_gb)
    print(f"Successfully copied {success_count} tracks.")
    print(f"{failure_count} tracks failed to copy.")


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
        fetch_features=args.features,
        #fetch_analysis=args.analysis,
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
    print("4. Copy files from an M3U playlist to a new folder, using filename prefix to order tracks")

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
        generate_stats = input("Generate stats CSV? (y/n): ").strip().lower() == 'y'
        fetch_features = input("Fetch Spotify audio features data? (y/n): ").strip().lower() == 'y'
        #fetch_analysis = input("Fetch Spotify audio analysis data? (y/n): ").strip().lower() == 'y'
        post = input("Skip genre extraction and use an existing CSV file? (y/n): ").strip().lower() == 'y'
        
        csv_file = None
        if post:
            csv_file = input("Enter the path to the existing CSV file: ").strip()
            if not os.path.isfile(csv_file):
                print(f"Error: The CSV file '{csv_file}' does not exist.")
                return
        
        loved_tracks = input("Enter the path to the loved tracks M3U file (or leave blank to skip): ").strip() or None
        loved_albums = input("Enter the path to the loved albums M3U file (or leave blank to skip): ").strip() or None
        loved_artists = input("Enter the path to the loved artists M3U file (or leave blank to skip): ").strip() or None
        
        # Create a SimpleNamespace object to hold the arguments
        args = SimpleNamespace(
            m3u_file=m3u_file,
            music_directory=music_directory,
            stats=generate_stats,
            features=fetch_features,
            #analysis=fetch_analysis,
            post=post,
            csv_file=csv_file,  # Add the CSV file path here
            loved_tracks=loved_tracks,
            loved_albums=loved_albums,
            loved_artists=loved_artists
        )
        run_analyze_m3u(credentials, args)
    elif choice == "3":
        csv_file = input("Enter the path to the CSV file (required): ").strip()
        shuffle = input("Curate the tracks within each cluster? (y/n): ").strip().lower() == 'y'
        loved_input = input("Filter by loved tracks, albums, or artists (e.g., 'tracks albums') or leave blank: ").strip()
        loved = loved_input.split() if loved_input else None
        run_spawnre_csv(csv_file=csv_file, shuffle=shuffle, loved=loved)
    elif choice == "4":
        m3u_file = input("Enter the path to the M3U playlist file: ").strip()
        music_dir = input("Enter the path to the source music directory: ").strip()
        output_folder = input("Enter the path to the destination folder: ").strip()
        max_size_input = input("Enter the maximum cumulative size in GB (or leave blank for no limit): ").strip()
        
        # Normalize and Resolve Paths
        m3u_file_path = Path(m3u_file).expanduser().resolve()
        music_dir_path = Path(music_dir).expanduser().resolve()
        output_folder_path = Path(output_folder).expanduser().resolve()
        
        # Validate Paths
        if not m3u_file_path.is_file():
            print(f"Error: The M3U file '{m3u_file_path}' does not exist.")
            return

        if not music_dir_path.is_dir():
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

        run_folder_from_m3u(
            m3u_file=str(m3u_file_path),
            music_dir=str(music_dir_path),
            output_folder=str(output_folder_path),
            max_size_gb=max_size_gb
        )
    else:
        print("Invalid choice. Please select a valid option.")


if __name__ == "__main__":
    main()
