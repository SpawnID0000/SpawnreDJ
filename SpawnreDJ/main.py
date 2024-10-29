# main.py

import os
import sys
import getpass
from types import SimpleNamespace
from dotenv import load_dotenv, set_key
import logging

# Import your module functions
from SpawnreDJ.M3U_from_folder import generate_m3u
from SpawnreDJ.folder_from_M3U import copy_tracks_with_sequence
from SpawnreDJ.anal_M3U import analyze_m3u
from SpawnreDJ.M3U_from_CSV import create_clusters, order_clusters, write_m3u, print_summary

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

# Path to the environment file
ENV_FILE = 'APIds.env'

def load_credentials() -> dict:
    """
    Load API credentials from the environment file.
    Returns a dictionary with credentials or empty strings if not found.
    """
    load_dotenv(ENV_FILE)
    credentials = {
        'lastfm_api_key': os.getenv('LASTFM_API_KEY', '').strip(),
        'spotify_client_id': os.getenv('SPOTIPY_CLIENT_ID', '').strip(),
        'spotify_client_secret': os.getenv('SPOTIPY_CLIENT_SECRET', '').strip()
    }
    return credentials

def prompt_credentials() -> dict:
    """
    Prompt the user to enter API credentials.
    Saves them to the environment file.
    Returns a dictionary with the entered credentials.
    """
    print("\nSome API credentials are missing. Please enter the required values.")
    lastfm_api_key = getpass.getpass("Enter your Last.fm API Key: ").strip()
    spotify_client_id = getpass.getpass("Enter your Spotify Client ID: ").strip()
    spotify_client_secret = getpass.getpass("Enter your Spotify Client Secret: ").strip()

    # Save to .env file
    with open(ENV_FILE, 'a') as env_file:
        if lastfm_api_key:
            env_file.write(f'\nLASTFM_API_KEY={lastfm_api_key}')
        if spotify_client_id:
            env_file.write(f'\nSPOTIPY_CLIENT_ID={spotify_client_id}')
        if spotify_client_secret:
            env_file.write(f'\nSPOTIPY_CLIENT_SECRET={spotify_client_secret}')

    credentials = {
        'lastfm_api_key': lastfm_api_key,
        'spotify_client_id': spotify_client_id,
        'spotify_client_secret': spotify_client_secret
    }

    logging.info("API credentials saved to APIds.env.\n")
    return credentials

def get_or_prompt_credentials() -> dict:
    """
    Load credentials; if missing, prompt the user to enter them.
    Returns a dictionary with credentials.
    """
    credentials = load_credentials()
    if not all(credentials.values()):
        credentials = prompt_credentials()
    return credentials

def interactive_menu(credentials):
    """
    Interactive menu for SpawnreDJ.
    """
    print("\nWelcome to SpawnreDJ!")
    while True:
        print("\nOptions:")
        print("1. Generate an M3U playlist from a folder")
        print("2. Copy files from an M3U playlist to a new folder")
        print("3. Analyze M3U for genre & audio features")
        print("4. Generate a genre-clustered M3U playlist from a CSV file")
        print()

        choice = input("Enter your choice (or leave blank to exit): ").strip()
        if choice == '1':
            music_dir = input("Enter the path to the music directory: ").strip()
            flip_input = input("Enter 'y' to flip or leave blank for default (Track - Artist): ").strip().lower()
            flip = flip_input == 'y'
            path_prefix_input = input("Enter the path prefix to add or leave blank for default ('../'): ").strip() or '../'
            
            # New addition: Ask for M3U filename, defaulting to 'playlist.m3u'
            m3u_file_name = input("Enter the name for the playlist file (e.g., 'playlist.m3u') or leave blank for default: ").strip() or 'playlist.m3u'
            
            # Pass the correct file path to generate_m3u
            m3u_file_path = os.path.abspath(os.path.join(music_dir, '..', m3u_file_name))
            
            generate_m3u(
                music_dir=music_dir,
                m3u_file_path=m3u_file_path,
                flip_order=flip,
                path_prefix=path_prefix_input
            )
        elif choice == '2':
            m3u_file = input("Enter the path to the M3U playlist file: ").strip()
            music_dir = input("Enter the path to the source music directory: ").strip()
            output_folder = input("Enter the path to the destination folder: ").strip()
            max_size_input = input("Enter the maximum cumulative size in GB (or leave blank for no limit): ").strip()
            try:
                max_size_gb = float(max_size_input) if max_size_input else None
            except ValueError:
                print("Invalid input for maximum size. Please enter a number.")
                max_size_gb = None
            copy_tracks_with_sequence(m3u_file, music_dir, output_folder, max_size_gb)
        elif choice == '3':
            # Ensure credentials are loaded
            if not all(credentials.values()):
                print("\nAPI credentials are required for this option.")
                credentials = get_or_prompt_credentials()

            m3u_file = input("Enter the path to the M3U playlist file: ").strip()
            music_directory = input("Enter the root directory of the music files: ").strip()
            generate_stats = input("Generate stats CSV? (y/n): ").strip().lower() == 'y'
            fetch_features = input("Fetch Spotify audio features? (y/n): ").strip().lower() == 'y'
            fetch_analysis = input("Fetch Spotify audio analysis data? (y/n): ").strip().lower() == 'y'
            post = input("Skip genre extraction and use an existing CSV file? (y/n): ").strip().lower() == 'y'
            loved_tracks = input("Enter the path to the loved tracks M3U file (or leave blank to skip): ").strip() or None
            loved_albums = input("Enter the path to the loved albums M3U file (or leave blank to skip): ").strip() or None
            loved_artists = input("Enter the path to the loved artists M3U file (or leave blank to skip): ").strip() or None

            run_analyze_m3u(credentials, SimpleNamespace(
                m3u_file=m3u_file,
                music_directory=music_directory,
                stats=generate_stats,
                features=fetch_features,
                analysis=fetch_analysis,
                post=post,
                loved_tracks=loved_tracks,
                loved_albums=loved_albums,
                loved_artists=loved_artists
            ))
        elif choice == '4':
            # Option 4 might require API credentials as well, depending on implementation
            # Adjust accordingly if needed
            pass
        elif choice == '':
            print("Exiting SpawnreDJ.")
            break
        else:
            print("Invalid choice. Please try again.")

def run_analyze_m3u(credentials, args):
    """
    Wrapper function to analyze an M3U playlist for genres and audio features.
    """
    # Check if API credentials are needed
    if any([args.stats, args.features, args.analysis, args.loved_tracks, args.loved_albums, args.loved_artists]):
        if not all(credentials.values()):
            print("\nAPI credentials are required for analyzing M3U playlists.")
            credentials = get_or_prompt_credentials()

    analyze_m3u(
        m3u_file=args.m3u_file,
        music_directory=args.music_directory,
        lastfm_api_key=credentials['lastfm_api_key'],
        spotify_client_id=credentials['spotify_client_id'],
        spotify_client_secret=credentials['spotify_client_secret'],
        generate_stats=args.stats,
        fetch_features=args.features,
        fetch_analysis=args.analysis,
        post=args.post,
        loved_tracks=args.loved_tracks,
        loved_albums=args.loved_albums,
        loved_artists=args.loved_artists
    )

def main():
    """
    Main entry point for SpawnreDJ.
    """
    # Initially load credentials, but do not prompt
    credentials = load_credentials()
    interactive_menu(credentials)

if __name__ == "__main__":
    main()
