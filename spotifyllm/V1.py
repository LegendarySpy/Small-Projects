import json
import ollama
import spotipy
from spotipy.oauth2 import SpotifyOAuth
from colorama import Fore, init

init(autoreset=True)

# Add your ID and Secret here
SPOTIFY_CONFIG = {
    "SPOTIPY_CLIENT_ID": "",
    "SPOTIPY_CLIENT_SECRET": "",
    "SPOTIPY_REDIRECT_URI": "http://localhost:8888/callback",
    "SCOPE": "user-read-playback-state,user-modify-playback-state"
}

sp = spotipy.Spotify(auth_manager=SpotifyOAuth(
    scope=SPOTIFY_CONFIG["SCOPE"],
    client_id=SPOTIFY_CONFIG["SPOTIPY_CLIENT_ID"],
    client_secret=SPOTIFY_CONFIG["SPOTIPY_CLIENT_SECRET"],
    redirect_uri=SPOTIFY_CONFIG["SPOTIPY_REDIRECT_URI"]
))


def execute_spotify_command(command):
    try:
        response = ollama.chat(model='mistral-nemo', messages=[
            {
                'role': 'system',
                'content': "You are a Spotify DJ. Respond with JSON only containing: 'action' (play/set_volume), 'song', 'artist' (optional), 'volume' (0-100), 'notes'"
            },
            {'role': 'user', 'content': f'Parse Spotify command: {command}'}
        ])

        function_call = json.loads(response['message']['content'])
        print(Fore.GREEN + f"Parsed command: {json.dumps(function_call, indent=2)}")

        return (
            function_call.get("action", "").lower(),
            function_call.get("song"),
            function_call.get("artist"),
            function_call.get("volume")
        )
    except Exception as e:
        print(Fore.RED + f"Error parsing command: {e}")
        return "play", None, None, None


def play_song(sp, song, artist=None):
    if not song:
        print(Fore.RED + "Error: No song specified")
        return

    query = f"{song} {artist}" if artist else song
    try:
        results = sp.search(q=query, type="track", limit=5)
        tracks = results["tracks"]["items"]

        if not tracks:
            print(Fore.RED + f"No tracks found for '{query}'")
            return

        # Display and play first result
        selected_track = tracks[0]
        print(
            Fore.GREEN + f"\nPlaying: '{selected_track['name']}' by {', '.join(artist['name'] for artist in selected_track['artists'])}")
        sp.start_playback(uris=[selected_track["uri"]])

    except spotipy.exceptions.SpotifyException as e:
        error_msg = {
            'No active device found': "Please ensure Spotify is open and playing",
            'The access token expired': "Session expired. Please restart the application"
        }.get(str(e), f"Unexpected error: {e}")
        print(Fore.RED + error_msg)


def set_volume(sp, volume):
    try:
        volume = int(volume)
        if 0 <= volume <= 100:
            sp.volume(volume)
            print(Fore.GREEN + f"Volume set to {volume}")
        else:
            print(Fore.RED + "Volume must be between 0 and 100")
    except (ValueError, TypeError):
        print(Fore.RED + "Invalid volume value")


if __name__ == "__main__":
    print(Fore.CYAN + "Welcome to Spotify Controller!")
    print(Fore.YELLOW + "Enter your commands (or 'quit' to exit)")

    while True:
        try:
            command = input(Fore.WHITE + "\nSpotify Command > ").strip()

            if command.lower() == 'quit':
                print(Fore.GREEN + "Goodbye!")
                break

            if not command:
                continue

            action, song, artist, volume = execute_spotify_command(command)

            if action == "play":
                play_song(sp, song, artist)
            elif action == "set_volume":
                set_volume(sp, volume)
            else:
                print(Fore.RED + "Unknown command. Try something like:")
                print(Fore.YELLOW + "- Play Bohemian Rhapsody by Queen")
                print(Fore.YELLOW + "- Set volume to 50")

        except Exception as e:
            print(Fore.RED + f"Error: {e}")
            continue
