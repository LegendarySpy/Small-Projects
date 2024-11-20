import json
import ollama
import spotipy
from spotipy.oauth2 import SpotifyOAuth
from colorama import Fore, init
from datetime import datetime

init(autoreset=True)

# Add your ID and Secret here
SPOTIFY_CONFIG = {
    "SPOTIPY_CLIENT_ID": "",
    "SPOTIPY_CLIENT_SECRET": "",
    "SPOTIPY_REDIRECT_URI": "http://localhost:8888/callback",
    "SCOPE": "user-read-playback-state user-modify-playback-state user-read-currently-playing "
             "user-read-recently-played playlist-read-private playlist-modify-public playlist-modify-private "
             "user-library-read user-library-modify user-read-private user-read-email"
}

sp = spotipy.Spotify(auth_manager=SpotifyOAuth(
    scope=SPOTIFY_CONFIG["SCOPE"],
    client_id=SPOTIFY_CONFIG["SPOTIPY_CLIENT_ID"],
    client_secret=SPOTIFY_CONFIG["SPOTIPY_CLIENT_SECRET"],
    redirect_uri=SPOTIFY_CONFIG["SPOTIPY_REDIRECT_URI"]
))


def format_track_info(track):
    """Format track information into a readable string."""
    if not track:
        return None

    artists = ', '.join(artist['name'] for artist in track['artists'])
    duration_ms = track['duration_ms']
    duration_min = duration_ms // 60000
    duration_sec = (duration_ms % 60000) // 1000

    return {
        'name': track['name'],
        'artists': artists,
        'album': track['album']['name'],
        'duration': f"{duration_min}:{duration_sec:02d}",
        'popularity': track.get('popularity', 'N/A'),
        'uri': track['uri']
    }


def get_playback_state():
    """Get comprehensive playback state including current track, queue, and device info."""
    try:
        current = sp.current_playback()
        if not current:
            return None

        current_track = format_track_info(current['item']) if current.get('item') else None
        queue = sp.queue()
        queue_tracks = [format_track_info(track) for track in queue.get('queue', [])][:5]
        recent = sp.current_user_recently_played(limit=5)
        recent_tracks = [format_track_info(item['track']) for item in recent['items']]
        device = current['device']

        return {
            'current_track': current_track,
            'is_playing': current['is_playing'],
            'device': {
                'name': device['name'],
                'type': device['type'],
                'volume': device['volume_percent']
            },
            'queue': queue_tracks,
            'recent_tracks': recent_tracks,
            'shuffle_state': current['shuffle_state'],
            'repeat_state': current['repeat_state'],
            'progress': current['progress_ms'] // 1000 if current.get('progress_ms') else 0
        }
    except Exception as e:
        print(Fore.RED + f"Error getting playback state: {e}")
        return None


def execute_spotify_command(command):
    """Execute Spotify command with enhanced context awareness."""
    try:
        state = get_playback_state()
        context = "No active playback session"

        if state:
            current = state['current_track']
            queue_info = "\n".join([f"Next up: {t['name']} by {t['artists']}" for t in state['queue'][:3]])
            recent_info = "\n".join(
                [f"Recently played: {t['name']} by {t['artists']}" for t in state['recent_tracks'][:3]])

            context = f"""
Current playback state:
- Now {'playing' if state['is_playing'] else 'paused'}: '{current['name']}' by {current['artists']}
- From album: {current['album']}
- Progress: {state['progress']}s / {current['duration']}
- Device: {state['device']['name']} ({state['device']['type']}) at {state['device']['volume']}% volume
- Shuffle: {'on' if state['shuffle_state'] else 'off'}
- Repeat: {state['repeat_state']}

Queue:
{queue_info}

Recent history:
{recent_info}
"""

        response = ollama.chat(model='mistral-nemo', messages=[
            {
                'role': 'system',
                'content': f"""You are a Spotify DJ with the following context:
{context}

Respond with JSON containing:
- 'action': play/set_volume/next/previous/shuffle/repeat/queue/pause/resume/add_to_queue
- 'song': song name (for play or add_to_queue action)
- 'artist': artist name (optional)
- 'volume': 0-100 (for set_volume)
- 'notes': explanation
- 'queue_position': position in queue (for queue action)
"""
            },
            {'role': 'user', 'content': f'Parse command: {command}'}
        ])

        function_call = json.loads(response['message']['content'])
        print(Fore.GREEN + f"Parsed command: {json.dumps(function_call, indent=2)}")

        return (
            function_call.get("action", "").lower(),
            function_call.get("song"),
            function_call.get("artist"),
            function_call.get("volume"),
            function_call.get("queue_position"),
            function_call.get("notes")
        )
    except Exception as e:
        print(Fore.RED + f"Error parsing command: {e}")
        return "play", None, None, None, None, None


def play_song(sp, song, artist=None, queue_position=None):
    """Enhanced play function with queue support."""
    if not song and not queue_position:
        print(Fore.RED + "Error: No song specified")
        return

    try:
        if queue_position is not None:
            for _ in range(int(queue_position)):
                sp.next_track()
            return

        query = f"{song} {artist}" if artist else song
        results = sp.search(q=query, type="track", limit=5)
        tracks = results["tracks"]["items"]

        if not tracks:
            print(Fore.RED + f"No tracks found for '{query}'")
            return

        selected_track = tracks[0]
        track_info = format_track_info(selected_track)

        if queue_position:
            sp.add_to_queue(uri=selected_track["uri"])
            print(Fore.GREEN + f"\nAdded to queue: '{track_info['name']}' by {track_info['artists']}")
        else:
            sp.start_playback(uris=[selected_track["uri"]])
            print(Fore.GREEN + f"\nPlaying: '{track_info['name']}' by {track_info['artists']}")

    except spotipy.exceptions.SpotifyException as e:
        error_msg = {
            'No active device found': "Please ensure Spotify is open and playing",
            'The access token expired': "Session expired. Please restart the application"
        }.get(str(e), f"Unexpected error: {e}")
        print(Fore.RED + error_msg)


def control_playback(sp, action):
    """Handle various playback control actions."""
    try:
        if action == "next":
            sp.next_track()
            print(Fore.GREEN + "Skipped to next track")
        elif action == "previous":
            sp.previous_track()
            print(Fore.GREEN + "Returned to previous track")
        elif action == "shuffle":
            current = sp.current_playback()
            new_state = not current['shuffle_state']
            sp.shuffle(new_state)
            print(Fore.GREEN + f"Shuffle {'enabled' if new_state else 'disabled'}")
        elif action == "repeat":
            current = sp.current_playback()
            states = {'off': 'context', 'context': 'track', 'track': 'off'}
            new_state = states[current['repeat_state']]
            sp.repeat(new_state)
            print(Fore.GREEN + f"Repeat mode: {new_state}")
        elif action == "pause":
            sp.pause_playback()
            print(Fore.GREEN + "Playback paused")
        elif action == "resume":
            sp.start_playback()
            print(Fore.GREEN + "Playback resumed")
    except Exception as e:
        print(Fore.RED + f"Error controlling playback: {e}")


def set_volume(sp, volume):
    """Set playback volume."""
    try:
        volume = int(volume)
        if 0 <= volume <= 100:
            sp.volume(volume)
            print(Fore.GREEN + f"Volume set to {volume}")
        else:
            print(Fore.RED + "Volume must be between 0 and 100")
    except (ValueError, TypeError):
        print(Fore.RED + "Invalid volume value")


def add_to_queue(sp, song, artist=None):
    """Add a song to the queue."""
    try:
        query = f"{song} {artist}" if artist else song
        results = sp.search(q=query, type="track", limit=1)
        tracks = results["tracks"]["items"]

        if not tracks:
            print(Fore.RED + f"No tracks found for '{query}'")
            return

        selected_track = tracks[0]
        sp.add_to_queue(uri=selected_track["uri"])
        track_info = format_track_info(selected_track)
        print(Fore.GREEN + f"\nAdded to queue: '{track_info['name']}' by {track_info['artists']}")
    except Exception as e:
        print(Fore.RED + f"Error adding to queue: {e}")


if __name__ == "__main__":
    print(Fore.CYAN + "Welcome to Enhanced Spotify Controller!")
    print(Fore.YELLOW + """Available commands:
- Play [song] by [artist]
- Queue [song] by [artist]
- Next/Previous track
- Pause/Resume
- Set volume to [0-100]
- Shuffle on/off
- Toggle repeat
- Show queue
- Type 'quit' to exit
""")

    while True:
        try:
            state = get_playback_state()
            if state and state['current_track']:
                current = state['current_track']
                progress = state['progress']
                duration = current['duration']
                print(Fore.CYAN + f"\nNow {'playing' if state['is_playing'] else 'paused'}: "
                                  f"'{current['name']}' by {current['artists']} ({progress}s / {duration})")
                if state['queue']:
                    next_track = state['queue'][0]
                    print(Fore.CYAN + f"Next up: '{next_track['name']}' by {next_track['artists']}")

            command = input(Fore.WHITE + "\nSpotify Command > ").strip()
            if command.lower() == 'quit':
                print(Fore.GREEN + "Goodbye!")
                break
            if not command:
                continue

            action, song, artist, volume, queue_position, notes = execute_spotify_command(command)

            if action == "play":
                play_song(sp, song, artist)
            elif action == "set_volume":
                set_volume(sp, volume)
            elif action == "queue":
                play_song(sp, song, artist, queue_position=True)
            elif action == "add_to_queue":
                add_to_queue(sp, song, artist)
            elif action in ["next", "previous", "shuffle", "repeat", "pause", "resume"]:
                control_playback(sp, action)
            else:
                print(Fore.RED + "Unknown command. Check available commands above.")

            if notes:
                print(Fore.YELLOW + f"Note: {notes}")

        except Exception as e:
            print(Fore.RED + f"Error: {e}")
            continue
