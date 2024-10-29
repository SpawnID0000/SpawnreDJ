# SpawnreDJ

**SpawnreDJ** is a powerful and user-friendly tool designed to generate, analyze, and curate M3U playlists from a folder of audio files.  SpawnreDJ generates curated playlists based on detailed genre information and audio features, leveraging APIs from Last.fm, Spotify, & MusicBrainz.  In addition to outputting M3U playlist files, SpawnreDJ can also copy tracks listed in an M3U file and output them in sequence in a target directory (for example, to load onto a screen-free media player!)

## Table of Contents

- [Features](#features)
- [Prerequisites](#prerequisites)
- [Installation](#installation)
- [Configuration](#configuration)
- [Usage](#usage)
- [Generated Files](#generated-files)
- [Contributing](#contributing)
- [License](#license)
- [Contact](#contact)

## Features

- **Playlist Generation:** Create M3U playlists from a specified directory of audio files.
- **Genre Enrichment:** Fetch and integrate genre information from Last.fm, Spotify, and MusicBrainz APIs.
- **Audio Features:** Retrieve detailed audio features from Spotify, including danceability, energy, tempo, and more.
- **Statistical Analysis:** Generate statistics on genre distribution within your playlists.
- **Audio Analysis:** Perform in-depth audio analysis to understand track structures and dynamics.
- **CSV Reporting:** Export enriched playlist data and analysis results to CSV files for easy viewing and further processing.
- **Robust Error Handling:** Implements retries and exponential backoff to handle API rate limits and network issues gracefully.
- **Flexible Configuration:** Supports both initial playlist generation and post-processing of existing CSV files.

## Prerequisites

Before installing **SpawnreDJ**, ensure you have the following:

- **Python 3.6 or higher** installed on your system. You can download Python [here](https://www.python.org/downloads/).
- **API Keys:**
  - **Last.fm API Key:** Obtain one by creating an account at [Last.fm API](https://www.last.fm/api).
  - **Spotify API Credentials:** Obtain a Client ID and Client Secret by registering your application at [Spotify Developer Dashboard](https://developer.spotify.com/dashboard/applications).
- **MusicBrainz Account (Optional):** While not always necessary, having an account can help with rate limits and extended functionalities. Register [here](https://musicbrainz.org/doc/MusicBrainz_API).

## Installation

Clone the repository and install the package using `pip`.

```bash
# Clone the repository
git clone https://github.com/SpawnID0000/SpawnreDJ.git
cd SpawnreDJ

# (Optional) Create and activate a virtual environment
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install the package along with its dependencies
pip install .
```

Alternatively, if **SpawnreDJ** is available on PyPI, you can install it directly:

```bash
pip install SpawnreDJ
```

## Configuration

Before using **SpawnreDJ**, you need to set up your API keys and secrets.

### 1. **Environment Variables (Recommended)**

Set your API credentials as environment variables to enhance security and prevent exposing sensitive information in command-line history.

**On Unix/Linux/macOS:**

```bash
export LASTFM_API_KEY="your_lastfm_api_key"
export SPOTIFY_CLIENT_ID="your_spotify_client_id"
export SPOTIFY_CLIENT_SECRET="your_spotify_client_secret"
```

**On Windows (Command Prompt):**

```cmd
set LASTFM_API_KEY=your_lastfm_api_key
set SPOTIFY_CLIENT_ID=your_spotify_client_id
set SPOTIFY_CLIENT_SECRET=your_spotify_client_secret
```

**On Windows (PowerShell):**

```powershell
$env:LASTFM_API_KEY="your_lastfm_api_key"
$env:SPOTIFY_CLIENT_ID="your_spotify_client_id"
$env:SPOTIFY_CLIENT_SECRET="your_spotify_client_secret"
```

### 2. **Passing API Credentials via Command Line**

If you prefer not to use environment variables, you can pass the API credentials directly in the command:

```bash
SpawnreDJ analyze /path/to/playlist.m3u /path/to/music_directory   -last your_lastfm_api_key   -spot your_spotify_client_id your_spotify_client_secret   [options]
```

**Note:** Be cautious when passing sensitive information via command line as it may be stored in shell history.

## Usage

**SpawnreDJ** is primarily used through the command line. Below are the common commands and options:

### 1. **Analyzing a Playlist**

Generate a CSV report by analyzing an existing M3U playlist.

```bash
SpawnreDJ analyze <path_to_m3u_file> <music_directory>   -last <lastfm_api_key>   -spot <spotify_client_id> <spotify_client_secret>   [options]
```

**Example:**

```bash
SpawnreDJ analyze /Users/toddmarco/Documents/playlist.m3u /Users/toddmarco/Documents/test_Music   -last e0986a4b591667fb3a2b9797e8450a70   -spot 7dcdbc03580d4a83826e5c2a7ef92244 c44b733461874a628ba7d825954fb679   -stats -features
```

### 2. **Options**

- `-stats`: Generate a statistics CSV summarizing genre distributions.
- `-features`: Fetch and append Spotify audio features to the CSV.
- `-analysis`: Fetch and append Spotify audio analysis data.
- `-post`: Use an existing CSV file for post-processing without extracting genres anew.
- `-q` or `--quiet`: Suppress logging output.
- `-v` or `--verbose`: Enable verbose logging for debugging purposes.

### 3. **Help**

To view all available options and usage instructions, run:

```bash
SpawnreDJ --help
```

## Generated Files

After running **SpawnreDJ**, several CSV files will be generated in the directory of your M3U file:

1. **Main CSV (`playlist.csv`):**

   Contains enriched playlist data with additional genre information from various sources.

2. **Features CSV (`playlist_features.csv`):**

   Includes audio features fetched from Spotify, such as danceability, energy, tempo, etc.

3. **Analysis CSV (`playlist_analysis.csv`):**

   Contains detailed audio analysis data for each track, including loudness ranges, segment durations, and more.

4. **Stats CSV (`playlist_stats.csv`):**

   Provides statistical summaries of genre distributions and other relevant metrics.

**Note:** File names are based on the original M3U file name.

## Contributing

Contributions are welcome! If you'd like to contribute to **SpawnreDJ**, please follow these steps:

1. **Fork the Repository:**

   Click the "Fork" button on the [GitHub Repository](https://github.com/SpawnID0000/SpawnreDJ) page.

2. **Clone Your Fork:**

   ```bash
   git clone https://github.com/yourusername/SpawnreDJ.git
   cd SpawnreDJ
   ```

3. **Create a New Branch:**

   ```bash
   git checkout -b feature/YourFeatureName
   ```

4. **Make Your Changes:**

   Implement your feature or bug fix.

5. **Commit Your Changes:**

   ```bash
   git commit -m "Add feature: YourFeatureName"
   ```

6. **Push to Your Fork:**

   ```bash
   git push origin feature/YourFeatureName
   ```

7. **Create a Pull Request:**

   Navigate to the original repository and submit a pull request detailing your changes.

### **Code of Conduct**

Please adhere to the [Contributor Covenant](https://www.contributor-covenant.org/) code of conduct.

## License

This project is licensed under the [GNU General Public License v3.0](https://www.gnu.org/licenses/gpl-3.0.en.html). You are free to use, modify, and distribute this software under the terms of this license.

## Contact

For any questions, issues, or feature requests, please open an issue on the [GitHub Repository](https://github.com/SpawnID0000/SpawnreDJ) or contact me directly at [spawn.id.0000@gmail.com](mailto:spawn.id.0000@gmail.com).

---

*Happy DJing with SpawnreDJ! 🎶*
