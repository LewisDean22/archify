"""
TODO - NICE DOCSTRING

"""
from rich.console import Console
from rich.panel import Panel
from rich.text import Text
from rich.theme import Theme
from rich.rule import Rule
from rich.markdown import Markdown

import spotipy
import traceback

from playlist_logic import *


COMMAND_DESCRIPTIONS = """
- `show-playlists` — Displays your Spotify playlists
- `archive <playlist_name>` — Save a playlist as Markdown to archive/ (enter playlist name as plain text)
- `archive-batch <batch_filepath>` — Archive multiple playlists from a .batch file (each line is a playlist name in plain text)
- `archive-all` — Archive all your playlists
- `view-archive` — View already archived playlists
- `help` — Offers a reminder of the available commands
- `q` — Quit the playlist archiver
"""

COMMANDS = {
    "q": lambda *_: exit(0),
    "show-playlists": handle_show_playlists,
    "archive": handle_archive_playlist,
    "archive-batch": handle_archive_batch,
    "view-archive": handle_view_archive,
    "archive-all": handle_archive_all,
    "help": lambda console, *_: (console.print(Markdown(COMMAND_DESCRIPTIONS)), console.print())
}

def get_user_input(console: Console, sp: spotipy.Spotify,
                   commands=COMMANDS):
    """
    Makes use of a dispatcher pattern to handle user input.
    
    NOTE: Could replace with match-case in the future? - 
    benefit would be that uncessary arguments are not passed to handlers
    """
    while True:
        user_input = console.input("[bold green]INPUT:[/bold green] ").strip()
        if not user_input:
            print("Please enter a command")
            continue
        
        parts = user_input.split()
        command = parts[0]
        if len(parts) == 1:
            argument = ""
        else:   
            argument = ' '.join(parts[1:])
        
        if command in commands:
            try:
                commands[command](console, sp, argument)
            except PlaylistArchiverError as e:
                console.print(f"[bold yellow]Warning:[/bold yellow] {str(e)}")
            except Exception as e:
                console.print(f"[bold red]Unexpected error:[/bold red] {str(e)}")
                console.print(f"[dim]{traceback.format_exc()}[/dim]")
        else:
            console.print(f"Unknown command: {command}. Please try again.", style="bold red")
        continue
    
def create_archiver_console(command_descriptions=COMMAND_DESCRIPTIONS) -> Console:
    
    theme = Theme({
    "markdown.code": "green on black",
    "markdown.item.bullet": "white",
    "markdown.code": "green underline" # "green underline"
    })
    
    console = Console(theme=theme)
    title = Text("🎵 Archify 🎵", style="bold green")
    subtitle = Text("Archive your Spotify playlists into local Markdown files.\n", style="italic")
    command_list = Markdown(command_descriptions)
    
    console.print(Panel(title, expand=False, style="bold green"), justify="center")
    console.print(subtitle, justify="center")
    console.print(Rule("Archify Commands", style="green"))
    console.print(command_list)
    console.print(Rule(style="green"))
    return console

def main():
    console = create_archiver_console()
    sp = start_spotify_auth()
    while True:
        get_user_input(console, sp)

if __name__ == "__main__":
    main()
