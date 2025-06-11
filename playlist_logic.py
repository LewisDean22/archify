import spotipy
from spotipy.oauth2 import SpotifyOAuth
import os
from dotenv import load_dotenv # needed so environment variables work from Windows command prompt
import unicodedata
from thefuzz import process
from typing import List, Dict
import tqdm

from rich.console import Console
from rich.columns import Columns
from rich.markdown import Markdown


class PlaylistArchiverError(Exception):
    """Custom exception for playlist archiver errors"""
    pass

def start_spotify_auth() -> spotipy.Spotify:
    """
    Starts the Spotify authentication process.
    """
    load_dotenv()
    client_id = os.getenv("SPOTIPY_CLIENT_ID")
    client_secret = os.getenv("SPOTIPY_CLIENT_SECRET")
    redirect_uri = os.getenv("SPOTIPY_REDIRECT_URI")

    sp = spotipy.Spotify(auth_manager=SpotifyOAuth(
        client_id=client_id,
        client_secret=client_secret,
        redirect_uri=redirect_uri,
        scope="playlist-read-private"
    ))
    return sp


def get_all_playlists(sp) -> List[Dict]:
    """
    Keeping track of offset and limit is necessary to implement pagination (to view all user playlists).
    """
    playlists = []
    offset = 0
    limit = 50
    while True:
        batch = sp.current_user_playlists(limit=limit, offset=offset)
        playlists.extend(batch['items'])
        if batch['next']:
            offset += limit
        else:
            break
    return playlists

def get_playlist_id_by_name(sp: spotipy.Spotify, inputted_playlist_name: str,
                            fuzzy_threshold: int = 80) -> None:
    playlists = get_all_playlists(sp)
    for playlist in playlists:
        read_playlist_name = unicodedata.normalize('NFKC', playlist['name'].strip()) 
        if read_playlist_name.lower() == inputted_playlist_name.lower():
            return playlist['id']
    
    # Fuzzy search attempt
    playlist_names = {unicodedata.normalize('NFKC', p['name'].strip()): p['id'] for p in playlists}
    matches = process.extractBests(
        inputted_playlist_name, 
        list(playlist_names.keys()),
        score_cutoff=fuzzy_threshold,
        limit=3
    )
    
    if not matches:
        return None
    
    print(f"Exact playlist match not found for '{inputted_playlist_name}'.\nDid you mean:")
    for i, (name, score) in enumerate(matches, 1):
        print(f"- {name}?")
    print("\n")
    return None

def get_playlist_tracks(sp: spotipy.Spotify, playlist_id: str) -> list:
    """
    Keeping track of offset and limit is necessary to implement pagination (to view all tracks in a playlist).
    """
    track_entries = []
    offset = 0
    limit = 100
    idx = 0
    while True:
        results = sp.playlist_tracks(playlist_id, offset=offset, limit=limit)
        items = results['items']
        if not items:
            break
        for item in items:
            track = item['track']
            if track is None:
                continue # Skip unavailable or missing tracks
            idx += 1
            
            artists = track['artists']
            if artists:
                artist_names = artist_names = ', '.join(artist["name"] or 'Unknown Artist' for artist in artists)
            else:
                artist_names = "Unknown Artist"
            track_entries.append(f"{idx}. _{track['name']}_ by {artist_names}")
        
        if results['next']:
            offset += limit
        else:
            break
    return track_entries

def save_playlist_to_markdown(playlist_name: str, tracks: list) -> str:
    directory = "archive"
    if not os.path.exists(directory):
        os.makedirs(directory)
    
    # NOTE - could use regex to clean filename if, e.g., emojis end up being problematic
    output_filename = f"{directory}/{playlist_name.replace(' ', '_').lower()}_playlist_archive.md"
    
    with open(output_filename, "w", encoding="utf-8") as md_file:
        md_file.write(f"# {playlist_name} Song Archive\n\n")
        for line in tracks:
            md_file.write(line + "\n")
    return output_filename
    
def handle_show_playlists(console: Console, sp, user_input) -> None:
    playlists = get_all_playlists(sp)
    playlist_names = [playlist['name'] for playlist in playlists]
    console.print(Markdown("# Available Playlists", style="white"))
    columns = Columns(playlist_names, equal=True, expand=True)
    console.print(columns)
    return None

def handle_archive_playlist(console: Console, sp: spotipy.Spotify, user_input: str) -> None:
    if not (isinstance(user_input, str) and user_input):
        raise PlaylistArchiverError("Please enter a valid playlist name after archive-playlist.")
    
    playlist_name = user_input
    playlist_id = get_playlist_id_by_name(sp, playlist_name)
    if not playlist_id:
         raise PlaylistArchiverError(f"Playlist '{playlist_name}' not found. Please try again.")
    tracks = get_playlist_tracks(sp, playlist_id)
    playlist_filepath = save_playlist_to_markdown(playlist_name, tracks)
    print(f"Playlist '{playlist_name}' has been archived successfully to {playlist_filepath}")
    
def handle_archive_batch(console: Console, sp: spotipy.Spotify, user_input: str) -> None:
    """
    Expects files with the .batch file extension (semantic label).
    """
    if not (isinstance(user_input, str) and user_input and user_input.endswith(".batch")):
        print("Please enter a valid playlist batch filepath after archive-batch.")
        raise PlaylistArchiverError("Invalid batch file. Please try again.")
    
    batch_filepath = user_input
    if not os.path.exists(batch_filepath):
        raise PlaylistArchiverError(f"Batch file '{batch_filepath}' does not exist. Please try again.")

    with open(batch_filepath, 'r', encoding='utf-8') as f:
        playlist_names = [line.strip() for line in f if line.strip()]

    if not playlist_names:
        raise PlaylistArchiverError("No playlist names found in the batch file.")

    for playlist_name in playlist_names:
        print(f"Archiving: {playlist_name} ...")
        playlist_id = get_playlist_id_by_name(sp, playlist_name)
        if not playlist_id:
            print(f"Playlist '{playlist_name}' not found. Skipping ...\n")
            continue

        tracks = get_playlist_tracks(sp, playlist_id)
        save_playlist_to_markdown(playlist_name, tracks)
        print(f"Successfully archived '{playlist_name}'\n")
    return None

def handle_view_archive(console: Console, sp: spotipy.Spotify, user_input: str) -> None:
    
    if not os.path.exists("archive"):
        print("No archived playlists found")
    else:
        archived_playlists = [filename for filename in os.listdir("archive") if filename.endswith("playlist_archive.md")]
        display_names = [name.replace("_playlist_archive.md", "").replace("_", " ").title() for name in archived_playlists]
        columns = Columns(display_names, equal=True, expand=True)
        console.print(Markdown("# Archived Playlists", style="white"))
        console.print(columns)
    return None

def handle_archive_all(console: Console, sp: spotipy.Spotify, user_input: str) -> None:
    """
    Archives all playlists with a tqdm loading bar.
    """
    playlists = get_all_playlists(sp)
    if not playlists:
        print("No playlists found.")
        return None

    for playlist in tqdm.tqdm(playlists, desc="Archiving Playlists", unit="playlist",
                              bar_format="{l_bar}{bar}| {n_fmt}/{total_fmt}", colour="green"):
        playlist_name = playlist['name']
        playlist_id = playlist['id']
        tracks = get_playlist_tracks(sp, playlist_id)
        save_playlist_to_markdown(playlist_name, tracks)
    print(f"Successfully archived {len(playlists)} playlists.\n")
    return None