#
"""
Sunnify (Spotify Downloader)
Copyright (C) 2024 Sunny Patel <sunnypatel124555@gmail.com>

EDUCATIONAL PROJECT DISCLAIMER:
This software is a student portfolio project developed for educational purposes only.
It is intended to demonstrate software engineering skills and is provided free of charge.
Users are solely responsible for ensuring compliance with applicable laws in their jurisdiction.
This software should only be used with content you own or have permission to download.
See DISCLAIMER.md for full terms.

For the program to work, the playlist URL pattern must follow the format of
/playlist/abcdefghijklmnopqrstuvwxyz... If the program stops working, email
<sunnypatel124555@gmail.com> or open an issue in the repository.
"""

__version__ = "2.0.1"

import os
import sys
import threading
import webbrowser

import requests
from mutagen.easyid3 import EasyID3
from mutagen.id3 import APIC, ID3
from PyQt5.QtCore import (
    QEasingCurve,
    QPropertyAnimation,
    QSize,
    Qt,
    QThread,
    pyqtSignal,
    pyqtSlot,
)
from PyQt5.QtGui import QCursor, QImage, QPixmap
from PyQt5.QtWidgets import (
    QApplication,
    QFileDialog,
    QGraphicsDropShadowEffect,
    QMainWindow,
    QMessageBox,
)
from yt_dlp import YoutubeDL

from spotifydown_api import (
    ExtractionError,
    NetworkError,
    PlaylistClient,
    PlaylistInfo,
    RateLimitError,
    SpotifyDownAPIError,
    detect_spotify_url_type,
    extract_playlist_id,
    sanitize_filename,
)
from Template import Ui_MainWindow



import sys

def get_cli_url():
    return sys.argv[1] if len(sys.argv) > 1 else ""



def get_ffmpeg_path():
    """Get path to FFmpeg - checks bundled first, then system paths."""
    # Check bundled FFmpeg first (for PyInstaller builds)
    if getattr(sys, "frozen", False):
        base_path = sys._MEIPASS
        if sys.platform == "win32":
            ffmpeg = os.path.join(base_path, "ffmpeg", "ffmpeg.exe")
        else:
            ffmpeg = os.path.join(base_path, "ffmpeg", "ffmpeg")
        if os.path.exists(ffmpeg):
            return os.path.join(base_path, "ffmpeg")

    # Check common system paths (for homebrew/system installs)
    ffmpeg_name = "ffmpeg.exe" if sys.platform == "win32" else "ffmpeg"
    common_paths = [
        "/opt/homebrew/bin",  # macOS ARM homebrew
        "/usr/local/bin",  # macOS Intel homebrew / Linux
        "/usr/bin",  # Linux system
    ]

    for path in common_paths:
        ffmpeg = os.path.join(path, ffmpeg_name)
        if os.path.exists(ffmpeg):
            return path

    # Check if ffmpeg is in PATH
    import shutil

    ffmpeg_in_path = shutil.which("ffmpeg")
    if ffmpeg_in_path:
        return os.path.dirname(ffmpeg_in_path)

    return None


class MusicScraper(QThread):
    PlaylistCompleted = pyqtSignal(str)
    PlaylistID = pyqtSignal(str)
    song_Album = pyqtSignal(str)
    song_meta = pyqtSignal(dict)
    add_song_meta = pyqtSignal(dict)
    count_updated = pyqtSignal(int)
    dlprogress_signal = pyqtSignal(int)
    Resetprogress_signal = pyqtSignal(int)
    error_signal = pyqtSignal(str)  # Signal for error messages to UI

    def __init__(self, cancel_event: threading.Event | None = None):
        super().__init__()
        self.counter = 0  # Initialize counter to zero
        self.session = requests.Session()
        self.spotifydown_api = None
        self._cancel_event = cancel_event or threading.Event()
        self._failed_tracks: list[str] = []  # Track failed downloads

    def is_cancelled(self) -> bool:
        """Check if cancellation has been requested."""
        return self._cancel_event.is_set()

    def _get_user_friendly_error(self, error: Exception, track_title: str = "") -> str:
        """Convert exception to user-friendly error message."""
        if isinstance(error, RateLimitError):
            return "Rate limited by Spotify - waiting..."
        if isinstance(error, NetworkError):
            return "Network error - retrying..."
        if isinstance(error, ExtractionError):
            return f"Could not access '{track_title}' - may be unavailable"
        if "HTTP Error 429" in str(error):
            return "YouTube rate limit - waiting..."
        if "No video formats" in str(error) or "unavailable" in str(error).lower():
            return f"'{track_title}' not found on YouTube"
        return f"Error: {str(error)[:50]}"

    # def ensure_spotifydown_api(self):
    #     if self.spotifydown_api is None:
    #         self.spotifydown_api = PlaylistClient(session=self.session)
    #     return self.spotifydown_api

    def ensure_spotifydown_api(self):
        if self.spotifydown_api is None:
            self.spotifydown_api = PlaylistClient(session=self.session)

            # debug info
            print("PlaylistClient created:", self.spotifydown_api)
            print("Attributes:", self.spotifydown_api.__dict__)
            print("base_url:", getattr(self.spotifydown_api, "base_url", None))

        return self.spotifydown_api




    # def sanitize_text(self, text):
    #     """Sanitize text for filename usage."""
    #     return sanitize_filename(text, allow_spaces=True)

    def sanitize_text(self, text):
        """Sanitize text for filename usage."""
        print("[sanitize_text] input :", text)

        cleaned = sanitize_filename(text, allow_spaces=True)

        print("[sanitize_text] output:", cleaned)
        return cleaned





    # def format_playlist_name(self, metadata: PlaylistInfo):
    #     owner = metadata.owner or "Spotify"
    #     return f"{metadata.name} - {owner}".strip(" -")


    def format_playlist_name(self, metadata: PlaylistInfo):
        print("[format_playlist_name] raw name :", metadata.name)
        print("[format_playlist_name] raw owner:", metadata.owner)

        owner = metadata.owner or "Spotify"
        result = f"{metadata.name} - {owner}".strip(" -")

        print("[format_playlist_name] result   :", result)
        return result






    # def prepare_playlist_folder(self, base_folder, playlist_name):
    #     if not os.path.exists(base_folder):
    #         os.makedirs(base_folder)
    #     safe_name = "".join(
    #         character
    #         for character in playlist_name
    #         if character.isalnum() or character in [" ", "_"]
    #     ).strip()
    #     if not safe_name:
    #         safe_name = "Sunnify Playlist"
    #     playlist_folder = os.path.join(base_folder, safe_name)
    #     os.makedirs(playlist_folder, exist_ok=True)
    #     return playlist_folder


    def prepare_playlist_folder(self, base_folder, playlist_name):
        print("[prepare_playlist_folder] base_folder :", base_folder)
        print("[prepare_playlist_folder] playlist_name:", playlist_name)

        if not os.path.exists(base_folder):
            print("[prepare_playlist_folder] creating base folder")
            os.makedirs(base_folder)

        safe_name = "".join(
            c for c in playlist_name
            if c.isalnum() or c in [" ", "_"]
        ).strip()

        if not safe_name:
            safe_name = "Sunnify Playlist"
            print("[prepare_playlist_folder] empty name → using default")

        playlist_folder = os.path.join(base_folder, safe_name)
        print("[prepare_playlist_folder] final folder:", playlist_folder)

        os.makedirs(playlist_folder, exist_ok=True)
        return playlist_folder




    # def download_track_audio(self, search_query, destination):
    #     # Check for FFmpeg first
    #     ffmpeg_path = get_ffmpeg_path()
    #     if not ffmpeg_path:
    #         raise RuntimeError(
    #             "FFmpeg not found! Install via: brew install ffmpeg (macOS) "
    #             "or apt install ffmpeg (Linux)"
    #         )

    #     base, _ = os.path.splitext(destination)
    #     output_template = base + ".%(ext)s"
    #     ydl_opts = {
    #         "format": "bestaudio/best",
    #         "noplaylist": True,
    #         "quiet": True,
    #         "outtmpl": output_template,
    #         "ffmpeg_location": ffmpeg_path,
    #         "postprocessors": [
    #             {
    #                 "key": "FFmpegExtractAudio",
    #                 "preferredcodec": "mp3",
    #                 "preferredquality": "192",
    #             }
    #         ],
    #     }
    #     with YoutubeDL(ydl_opts) as ydl:
    #         info = ydl.extract_info(search_query, download=True)
    #         if info.get("entries"):
    #             info = info["entries"][0]
    #         expected_path = base + ".mp3"
    #         if os.path.exists(expected_path):
    #             return expected_path
    #         fallback = ydl.prepare_filename(info)
    #         if os.path.exists(fallback):
    #             return fallback
    #     return base + ".mp3"


    def download_track_audio(self, search_query, destination):
        print("[download_track_audio] search_query :", search_query)
        print("[download_track_audio] destination  :", destination)

        # Check for FFmpeg first
        ffmpeg_path = get_ffmpeg_path()
        print("[download_track_audio] ffmpeg_path  :", ffmpeg_path)

        if not ffmpeg_path:
            raise RuntimeError(
                "FFmpeg not found! Install via: brew install ffmpeg (macOS) "
                "or apt install ffmpeg (Linux)"
            )

        base, _ = os.path.splitext(destination)
        output_template = base + ".%(ext)s"
        print("[download_track_audio] output tmpl  :", output_template)

        ydl_opts = {
            "format": "bestaudio/best",
            "noplaylist": True,
            "quiet": True,
            "outtmpl": output_template,
            "ffmpeg_location": ffmpeg_path,
            "postprocessors": [
                {
                    "key": "FFmpegExtractAudio",
                    "preferredcodec": "mp3",
                    "preferredquality": "192",
                }
            ],
        }

        print("[download_track_audio] ydl options set")

        with YoutubeDL(ydl_opts) as ydl:
            print("[download_track_audio] starting download...")
            info = ydl.extract_info(search_query, download=True)

            if info.get("entries"):
                info = info["entries"][0]
                print("[download_track_audio] playlist entry detected → first item")

            expected_path = base + ".mp3"
            print("[download_track_audio] expected path:", expected_path)

            if os.path.exists(expected_path):
                print("[download_track_audio] file found:", expected_path)
                return expected_path

            fallback = ydl.prepare_filename(info)
            print("[download_track_audio] fallback path:", fallback)

            if os.path.exists(fallback):
                print("[download_track_audio] file found:", fallback)
                return fallback

        print("[download_track_audio] fallback return:", base + ".mp3")
        return base + ".mp3"



    # def download_http_file(self, url, destination):
    #     response = self.session.get(url, stream=True, timeout=60)
    #     response.raise_for_status()
    #     total = int(response.headers.get("content-length", 0))
    #     downloaded = 0
    #     os.makedirs(os.path.dirname(destination), exist_ok=True)
    #     with open(destination, "wb") as handle:
    #         for chunk in response.iter_content(chunk_size=8192):
    #             if not chunk:
    #                 continue
    #             handle.write(chunk)
    #             downloaded += len(chunk)
    #             if total:
    #                 progress = int(downloaded / total * 100)
    #                 self.dlprogress_signal.emit(progress)
    #     return destination

    def download_http_file(self, url, destination):
        print("[download_http_file] URL        :", url)
        print("[download_http_file] Destination:", destination)

        response = self.session.get(url, stream=True, timeout=60)
        response.raise_for_status()

        total = int(response.headers.get("content-length", 0))
        print("[download_http_file] Total bytes:", total)

        downloaded = 0
        os.makedirs(os.path.dirname(destination), exist_ok=True)
        print("[download_http_file] Directory ensured")

        with open(destination, "wb") as handle:
            for chunk in response.iter_content(chunk_size=8192):
                if not chunk:
                    continue
                handle.write(chunk)
                downloaded += len(chunk)
                if total:
                    progress = int(downloaded / total * 100)
                    print(f"[download_http_file] Progress: {progress}% ({downloaded}/{total})")
                    self.dlprogress_signal.emit(progress)

        print("[download_http_file] Download complete:", destination)
        return destination



    # def scrape_playlist(self, spotify_playlist_link, music_folder):
    #     playlist_id = self.returnSPOT_ID(spotify_playlist_link)
    #     self.PlaylistID.emit(playlist_id)

    #     try:
    #         spotify_api = self.ensure_spotifydown_api()
    #     except SpotifyDownAPIError as exc:
    #         raise RuntimeError(str(exc)) from exc

    #     metadata = spotify_api.get_playlist_metadata(playlist_id)
    #     playlist_display_name = self.format_playlist_name(metadata)
    #     self.song_Album.emit(playlist_display_name)

    #     playlist_folder_path = self.prepare_playlist_folder(music_folder, playlist_display_name)

    #     for track in spotify_api.iter_playlist_tracks(playlist_id):
    #         # Check for cancellation before each track
    #         if self.is_cancelled():
    #             self.PlaylistCompleted.emit("Download cancelled")
    #             return

    #         self.Resetprogress_signal.emit(0)

    #         track_title = track.title
    #         artists = track.artists
    #         sanitized_title = self.sanitize_text(track_title)
    #         sanitized_artists = self.sanitize_text(artists)
    #         filename = f"{sanitized_title} - {sanitized_artists}.mp3"
    #         filepath = os.path.join(playlist_folder_path, filename)

    #         album_name = track.album or ""
    #         release_date = track.release_date or ""
    #         cover_url = track.cover_url or metadata.cover_url

    #         song_meta = {
    #             "title": track_title,
    #             "artists": artists,
    #             "album": album_name,
    #             "releaseDate": release_date,
    #             "cover": cover_url or "",
    #             "file": filepath,
    #         }

    #         self.song_meta.emit(dict(song_meta))

    #         if os.path.exists(filepath):
    #             self.add_song_meta.emit(song_meta)
    #             self.increment_counter()
    #             continue

    #         # Download via YouTube search (spotifydown mirrors are dead)
    #         search_query = f"ytsearch1:{track_title} {artists} audio"
    #         try:
    #             final_path = self.download_track_audio(search_query, filepath)
    #         except Exception as error_status:
    #             error_msg = self._get_user_friendly_error(error_status, track_title)
    #             self.error_signal.emit(error_msg)
    #             print(f"[*] Error downloading '{track_title}': {error_status}")
    #             self._failed_tracks.append(track_title)
    #             continue

    #         if not final_path or not os.path.exists(final_path):
    #             self.error_signal.emit(f"'{track_title}' - download failed")
    #             print(f"[*] Download did not produce an audio file for: {track_title}")
    #             self._failed_tracks.append(track_title)
    #             continue

    #         song_meta["file"] = final_path
    #         self.add_song_meta.emit(song_meta)
    #         self.increment_counter()
    #         self.dlprogress_signal.emit(100)

    #     # Report completion with failed track count
    #     if self._failed_tracks:
    #         self.PlaylistCompleted.emit(f"Done! {len(self._failed_tracks)} track(s) failed")
    #     else:
    #         self.PlaylistCompleted.emit("Download Complete!")



    def scrape_playlist(self, spotify_playlist_link, music_folder):
        print("[scrape_playlist] Spotify link:", spotify_playlist_link)
        print("[scrape_playlist] Music folder :", music_folder)

        playlist_id = self.returnSPOT_ID(spotify_playlist_link)
        print("[scrape_playlist] Playlist ID  :", playlist_id)
        self.PlaylistID.emit(playlist_id)

        try:
            spotify_api = self.ensure_spotifydown_api()
            print("[scrape_playlist] Spotify API initialized")
        except SpotifyDownAPIError as exc:
            print("[scrape_playlist] Spotify API error:", exc)
            raise RuntimeError(str(exc)) from exc

        metadata = spotify_api.get_playlist_metadata(playlist_id)
        playlist_display_name = self.format_playlist_name(metadata)
        print("[scrape_playlist] Playlist name:", playlist_display_name)
        self.song_Album.emit(playlist_display_name)

        playlist_folder_path = self.prepare_playlist_folder(music_folder, playlist_display_name)
        print("[scrape_playlist] Playlist folder path:", playlist_folder_path)

        for idx, track in enumerate(spotify_api.iter_playlist_tracks(playlist_id), start=1):
            print(f"[scrape_playlist] Track {idx}:", track.title, "-", track.artists)

            if self.is_cancelled():
                print("[scrape_playlist] Download cancelled by user")
                self.PlaylistCompleted.emit("Download cancelled")
                return

            self.Resetprogress_signal.emit(0)

            track_title = track.title
            artists = track.artists
            sanitized_title = self.sanitize_text(track_title)
            sanitized_artists = self.sanitize_text(artists)
            filename = f"{sanitized_title} - {sanitized_artists}.mp3"
            filepath = os.path.join(playlist_folder_path, filename)
            print("[scrape_playlist] Filepath:", filepath)

            album_name = track.album or ""
            release_date = track.release_date or ""
            cover_url = track.cover_url or metadata.cover_url

            song_meta = {
                "title": track_title,
                "artists": artists,
                "album": album_name,
                "releaseDate": release_date,
                "cover": cover_url or "",
                "file": filepath,
            }

            print("[scrape_playlist] Emitting song_meta for track")
            self.song_meta.emit(dict(song_meta))

            if os.path.exists(filepath):
                print("[scrape_playlist] Track already exists, skipping download")
                self.add_song_meta.emit(song_meta)
                self.increment_counter()
                continue

            search_query = f"ytsearch1:{track_title} {artists} audio"
            print("[scrape_playlist] Search query:", search_query)

            try:
                final_path = self.download_track_audio(search_query, filepath)
                print("[scrape_playlist] Download finished:", final_path)
            except Exception as error_status:
                error_msg = self._get_user_friendly_error(error_status, track_title)
                self.error_signal.emit(error_msg)
                print(f"[*] Error downloading '{track_title}': {error_status}")
                self._failed_tracks.append(track_title)
                continue

            if not final_path or not os.path.exists(final_path):
                self.error_signal.emit(f"'{track_title}' - download failed")
                print(f"[*] Download did not produce an audio file for: {track_title}")
                self._failed_tracks.append(track_title)
                continue

            song_meta["file"] = final_path
            self.add_song_meta.emit(song_meta)
            self.increment_counter()
            self.dlprogress_signal.emit(100)
            print(f"[scrape_playlist] Track processed: {track_title}")

        if self._failed_tracks:
            msg = f"Done! {len(self._failed_tracks)} track(s) failed"
            print("[scrape_playlist]", msg)
            self.PlaylistCompleted.emit(msg)
        else:
            print("[scrape_playlist] Download Complete!")
            self.PlaylistCompleted.emit("Download Complete!")








    # def returnSPOT_ID(self, link):
    #     """Extract playlist ID from Spotify URL."""
    #     return extract_playlist_id(link)



    def returnSPOT_ID(self, link):
        print("[returnSPOT_ID] Spotify link:", link)
        playlist_id = extract_playlist_id(link)
        print("[returnSPOT_ID] Extracted playlist ID:", playlist_id)
        return playlist_id








    # def scrape_track(self, spotify_track_link, music_folder):
    #     """Download a single track from Spotify."""
    #     url_type, track_id = detect_spotify_url_type(spotify_track_link)
    #     if url_type != "track":
    #         raise ValueError("Expected a track URL")

    #     try:
    #         spotify_api = self.ensure_spotifydown_api()
    #     except SpotifyDownAPIError as exc:
    #         raise RuntimeError(str(exc)) from exc

    #     track = spotify_api.get_track(track_id)
    #     self.song_Album.emit("Single Track Download")

    #     if not os.path.exists(music_folder):
    #         os.makedirs(music_folder)

    #     self.Resetprogress_signal.emit(0)

    #     track_title = track.title
    #     artists = track.artists
    #     sanitized_title = self.sanitize_text(track_title)
    #     sanitized_artists = self.sanitize_text(artists)
    #     filename = f"{sanitized_title} - {sanitized_artists}.mp3"
    #     filepath = os.path.join(music_folder, filename)

    #     album_name = track.album or ""
    #     release_date = track.release_date or ""
    #     cover_url = track.cover_url

    #     song_meta = {
    #         "title": track_title,
    #         "artists": artists,
    #         "album": album_name,
    #         "releaseDate": release_date,
    #         "cover": cover_url or "",
    #         "file": filepath,
    #     }

    #     self.song_meta.emit(dict(song_meta))

    #     if os.path.exists(filepath):
    #         self.add_song_meta.emit(song_meta)
    #         self.increment_counter()
    #         self.PlaylistCompleted.emit("Track already exists!")
    #         return

    #     # Download via YouTube search
    #     search_query = f"ytsearch1:{track_title} {artists} audio"
    #     try:
    #         final_path = self.download_track_audio(search_query, filepath)
    #     except Exception as error_status:
    #         error_msg = self._get_user_friendly_error(error_status, track_title)
    #         print(f"[*] Error downloading '{track_title}': {error_status}")
    #         self.PlaylistCompleted.emit(error_msg)
    #         return

    #     if not final_path or not os.path.exists(final_path):
    #         print(f"[*] Download did not produce an audio file for: {track_title}")
    #         self.PlaylistCompleted.emit("Download failed - no audio file produced")
    #         return

    #     song_meta["file"] = final_path
    #     self.add_song_meta.emit(song_meta)
    #     self.increment_counter()
    #     self.dlprogress_signal.emit(100)
    #     self.PlaylistCompleted.emit("Download Complete!")


    def scrape_track(self, spotify_track_link, music_folder):
        print("[scrape_track] Spotify track link:", spotify_track_link)
        print("[scrape_track] Music folder      :", music_folder)

        url_type, track_id = detect_spotify_url_type(spotify_track_link)
        print("[scrape_track] Detected URL type :", url_type)
        print("[scrape_track] Track ID          :", track_id)

        if url_type != "track":
            raise ValueError("Expected a track URL")

        try:
            spotify_api = self.ensure_spotifydown_api()
            print("[scrape_track] Spotify API initialized")
        except SpotifyDownAPIError as exc:
            print("[scrape_track] Spotify API error:", exc)
            raise RuntimeError(str(exc)) from exc

        track = spotify_api.get_track(track_id)
        print(f"[scrape_track] Track title: {track.title} | Artists: {track.artists}")
        self.song_Album.emit("Single Track Download")

        if not os.path.exists(music_folder):
            print("[scrape_track] Creating music folder")
            os.makedirs(music_folder)

        self.Resetprogress_signal.emit(0)

        track_title = track.title
        artists = track.artists
        sanitized_title = self.sanitize_text(track_title)
        sanitized_artists = self.sanitize_text(artists)
        filename = f"{sanitized_title} - {sanitized_artists}.mp3"
        filepath = os.path.join(music_folder, filename)
        print("[scrape_track] Filepath:", filepath)

        album_name = track.album or ""
        release_date = track.release_date or ""
        cover_url = track.cover_url

        song_meta = {
            "title": track_title,
            "artists": artists,
            "album": album_name,
            "releaseDate": release_date,
            "cover": cover_url or "",
            "file": filepath,
        }

        print("[scrape_track] Emitting song_meta")
        self.song_meta.emit(dict(song_meta))

        if os.path.exists(filepath):
            print("[scrape_track] Track already exists, skipping download")
            self.add_song_meta.emit(song_meta)
            self.increment_counter()
            self.PlaylistCompleted.emit("Track already exists!")
            return

        # Download via YouTube search
        search_query = f"ytsearch1:{track_title} {artists} audio"
        print("[scrape_track] Search query:", search_query)

        try:
            final_path = self.download_track_audio(search_query, filepath)
            print("[scrape_track] Download finished:", final_path)
        except Exception as error_status:
            error_msg = self._get_user_friendly_error(error_status, track_title)
            print(f"[*] Error downloading '{track_title}': {error_status}")
            self.PlaylistCompleted.emit(error_msg)
            return

        if not final_path or not os.path.exists(final_path):
            print(f"[*] Download did not produce an audio file for: {track_title}")
            self.PlaylistCompleted.emit("Download failed - no audio file produced")
            return

        song_meta["file"] = final_path
        self.add_song_meta.emit(song_meta)
        self.increment_counter()
        self.dlprogress_signal.emit(100)
        print("[scrape_track] Download Complete!")
        self.PlaylistCompleted.emit("Download Complete!")




    # def increment_counter(self):
    #     self.counter += 1
    #     self.count_updated.emit(self.counter)  # Emit the signal with the updated count


    def increment_counter(self):
        self.counter += 1
        print(f"[increment_counter] Counter updated: {self.counter}")
        self.count_updated.emit(self.counter)  # Emit the signal with the updated count



# # Scraper Thread
# class ScraperThread(QThread):
#     progress_update = pyqtSignal(str)

#     def __init__(
#         self, spotify_link, music_folder=None, cancel_event: threading.Event | None = None
#     ):
#         super().__init__()
#         self.spotify_link = spotify_link
#         self.music_folder = music_folder or os.path.join(os.getcwd(), "music")
#         self._cancel_event = cancel_event or threading.Event()
#         self.scraper = MusicScraper(cancel_event=self._cancel_event)

#     def request_cancel(self):
#         """Request cancellation of the download."""
#         self._cancel_event.set()

#     def run(self):
#         self.progress_update.emit("Scraping started...")
#         try:
#             # Detect URL type and handle accordingly
#             url_type, _ = detect_spotify_url_type(self.spotify_link)
#             if url_type == "track":
#                 self.scraper.scrape_track(self.spotify_link, self.music_folder)
#             else:
#                 self.scraper.scrape_playlist(self.spotify_link, self.music_folder)
#                 self.progress_update.emit("Scraping completed.")
#         except Exception as e:
#             self.progress_update.emit(f"{e}")


# Scraper Thread
class ScraperThread(QThread):
    progress_update = pyqtSignal(str)

    def __init__(
        self, spotify_link, music_folder=None, cancel_event: threading.Event | None = None
    ):
        super().__init__()
        print("[ScraperThread] Initializing...")
        self.spotify_link = spotify_link
        print(f"[ScraperThread] Spotify link: {spotify_link}")

        self.music_folder = music_folder or os.path.join(os.getcwd(), "music")
        print(f"[ScraperThread] Music folder: {self.music_folder}")

        self._cancel_event = cancel_event or threading.Event()
        self.scraper = MusicScraper(cancel_event=self._cancel_event)
        print("[ScraperThread] Initialized successfully")

    def request_cancel(self):
        """Request cancellation of the download."""
        print("[ScraperThread] Cancel requested")
        self._cancel_event.set()

    def run(self):
        print("[ScraperThread] Thread started")
        self.progress_update.emit("Scraping started...")

        try:
            print("[ScraperThread] Detecting Spotify URL type...")
            url_type, _ = detect_spotify_url_type(self.spotify_link)
            print(f"[ScraperThread] URL type detected: {url_type}")

            if url_type == "track":
                print("[ScraperThread] Starting track scrape")
                self.scraper.scrape_track(self.spotify_link, self.music_folder)
            else:
                print("[ScraperThread] Starting playlist scrape")
                self.scraper.scrape_playlist(self.spotify_link, self.music_folder)
                self.progress_update.emit("Scraping completed.")
                print("[ScraperThread] Scraping completed")

        except Exception as e:
            print(f"[ScraperThread] Error: {e}")
            self.progress_update.emit(f"{e}")










# # Download Song Cover Thread
# class DownloadCover(QThread):
#     albumCover = pyqtSignal(object)

#     def __init__(self, url):
#         super().__init__()
#         self.url = url

#     def run(self):
#         response = requests.get(self.url, stream=True)
#         if response.status_code == 200:
#             self.albumCover.emit(response.content)




# Download Song Cover Thread
class DownloadCover(QThread):
    albumCover = pyqtSignal(object)

    def __init__(self, url):
        super().__init__()
        self.url = url
        print(f"[DownloadCover] Initialized with URL: {url}")

    def run(self):
        print("[DownloadCover] Download started")
        response = requests.get(self.url, stream=True)
        print(f"[DownloadCover] HTTP Status: {response.status_code}")

        if response.status_code == 200:
            print("[DownloadCover] Cover downloaded successfully")
            self.albumCover.emit(response.content)
        else:
            print("[DownloadCover] Failed to download cover")






# # Scraper Thread
# class WritingMetaTagsThread(QThread):
#     tags_success = pyqtSignal(str)

#     def __init__(self, tags, filename):
#         super().__init__()
#         self.tags = tags
#         self.filename = filename
#         self._cover_thread = None  # Keep reference to prevent GC

#     def run(self):
#         try:
#             print("[*] FileName : ", self.filename)
#             audio = EasyID3(self.filename)
#             audio["title"] = self.tags.get("title", "")
#             audio["artist"] = self.tags.get("artists", "")
#             audio["album"] = self.tags.get("album", "")
#             audio["date"] = self.tags.get("releaseDate", "")
#             audio.save()

#             # Only download cover if URL exists
#             cover_url = self.tags.get("cover", "")
#             if cover_url:
#                 self._cover_thread = DownloadCover(cover_url)
#                 self._cover_thread.albumCover.connect(self.setPIC)
#                 self._cover_thread.start()
#         except Exception as e:
#             print(f"[*] Error writing meta tags: {e}")

#     def setPIC(self, data):
#         if data is None:
#             self.tags_success.emit("Cover Not Added..!")
#         else:
#             try:
#                 audio = ID3(self.filename)
#                 audio["APIC"] = APIC(encoding=3, mime="image/jpeg", type=3, desc="Cover", data=data)
#                 audio.save()
#                 self.tags_success.emit("Tags added successfully")
#             except Exception as e:
#                 self.tags_success.emit(f"Error adding cover: {e}")


# Scraper Thread
class WritingMetaTagsThread(QThread):
    tags_success = pyqtSignal(str)

    def __init__(self, tags, filename):
        super().__init__()
        self.tags = tags
        self.filename = filename
        self._cover_thread = None  # Keep reference to prevent GC
        print("[MetaTags] Thread initialized")
        print("[MetaTags] Target file:", filename)

    def run(self):
        try:
            print("[MetaTags] Writing ID3 tags...")
            audio = EasyID3(self.filename)

            audio["title"] = self.tags.get("title", "")
            audio["artist"] = self.tags.get("artists", "")
            audio["album"] = self.tags.get("album", "")
            audio["date"] = self.tags.get("releaseDate", "")
            audio.save()

            print("[MetaTags] Text tags saved")

            # Only download cover if URL exists
            cover_url = self.tags.get("cover", "")
            if cover_url:
                print("[MetaTags] Cover URL found, downloading...")
                self._cover_thread = DownloadCover(cover_url)
                self._cover_thread.albumCover.connect(self.setPIC)
                self._cover_thread.start()
            else:
                print("[MetaTags] No cover URL found")

        except Exception as e:
            print(f"[MetaTags] Error writing meta tags: {e}")

    def setPIC(self, data):
        if data is None:
            print("[MetaTags] Cover data is empty")
            self.tags_success.emit("Cover Not Added..!")
            import sys
            sys.exit(1)
        else:
            try:
                print("[MetaTags] Adding cover image...")
                audio = ID3(self.filename)
                audio["APIC"] = APIC(
                    encoding=3,
                    mime="image/jpeg",
                    type=3,
                    desc="Cover",
                    data=data,
                )
                audio.save()
                print("[MetaTags] Cover added successfully")
                self.tags_success.emit("Tags added successfully")

                # import sys
                sys.exit(0)  # exit with success code

            except Exception as e:
                print(f"[MetaTags] Error adding cover: {e}")
                self.tags_success.emit(f"Error adding cover: {e}")
                import sys
                sys.exit(1)




# class DownloadThumbnail(QThread):
#     thumbnail_ready = pyqtSignal(bytes)  # Signal to safely update UI from main thread

#     def __init__(self, url, main_UI):
#         super().__init__()
#         self.url = url
#         self.main_UI = main_UI
#         self.thumbnail_ready.connect(self._update_ui)

#     def run(self):
#         if not self.url:
#             return
#         try:
#             response = requests.get(self.url, stream=True, timeout=10)
#             if response.status_code == 200:
#                 self.thumbnail_ready.emit(response.content)
#         except Exception:
#             pass  # Silently fail for thumbnails

#     def _update_ui(self, data):
#         """Update UI from main thread via signal."""
#         pic = QImage()
#         pic.loadFromData(data)
#         self.main_UI.CoverImg.setPixmap(QPixmap(pic))
#         self.main_UI.CoverImg.show()





class DownloadThumbnail(QThread):
    thumbnail_ready = pyqtSignal(bytes)  # Signal to safely update UI from main thread

    def __init__(self, url, main_UI):
        super().__init__()
        self.url = url
        self.main_UI = main_UI
        self.thumbnail_ready.connect(self._update_ui)
        print("[Thumbnail] Thread initialized")
        print("[Thumbnail] URL:", url)

    def run(self):
        if not self.url:
            print("[Thumbnail] No URL provided, skipping")
            return

        try:
            print("[Thumbnail] Download started")
            response = requests.get(self.url, stream=True, timeout=10)
            print(f"[Thumbnail] HTTP Status: {response.status_code}")

            if response.status_code == 200:
                print("[Thumbnail] Thumbnail downloaded")
                self.thumbnail_ready.emit(response.content)
        except Exception as e:
            print(f"[Thumbnail] Error: {e}")  # Previously silent

    def _update_ui(self, data):
        """Update UI from main thread via signal."""
        print("[Thumbnail] Updating UI")
        pic = QImage()
        pic.loadFromData(data)
        self.main_UI.CoverImg.setPixmap(QPixmap(pic))
        self.main_UI.CoverImg.show()
        print("[Thumbnail] UI updated")








# # Main Window
# class MainWindow(QMainWindow, Ui_MainWindow):
#     def __init__(self):
#         """MainWindow constructor"""
#         super().__init__()
#         self.setupUi(self)

#         if len(sys.argv) > 1:
#             self.PlaylistLink.setText(sys.argv[1])

#         # Default download path - use user's Music folder, not cwd (which is / on macOS bundles)
#         self.download_path = self._get_default_download_path()
#         self._download_path_set = False  # Track if user has explicitly chosen a path
#         self._active_threads = []  # Keep references to running threads to prevent GC crashes
#         self._is_downloading = False  # Track download state for stop button
#         self._cancel_event = threading.Event()  # Event for cooperative thread cancellation

#         self.SONGINFORMATION.setGraphicsEffect(
#             QGraphicsDropShadowEffect(blurRadius=25, xOffset=2, yOffset=2)
#         )
#         self.PlaylistLink.returnPressed.connect(self.on_returnButton)
#         self.DownloadBtn.clicked.connect(self.on_returnButton)

#         self.showPreviewCheck.stateChanged.connect(self.show_preview)

#         self.Closed.clicked.connect(self.exitprogram)
#         self.Select_Home.clicked.connect(self.Linkedin)
#         self.SettingsBtn.clicked.connect(self.open_settings)


# Main Window
class MainWindow(QMainWindow, Ui_MainWindow):
    def __init__(self):
        """MainWindow constructor"""
        super().__init__()
        print("[MainWindow] Initializing...")
        self.setupUi(self)

        # if len(sys.argv) > 1:
        #     self.PlaylistLink.setText(sys.argv[1])
        #     print("[MainWindow] CLI link detected:", sys.argv[1])

# set the checkboxes to checked by default
        self.showPreviewCheck.setChecked(True)    # enable preview by default
        self.AddMetaDataCheck.setChecked(True)    # enable metadata writing by default


        # Default download path
        self.download_path = self._get_default_download_path()
        print("[MainWindow] Default download path:", self.download_path)

        self._download_path_set = False
        self._active_threads = []
        self._is_downloading = False
        self._cancel_event = threading.Event()

        self.SONGINFORMATION.setGraphicsEffect(
            QGraphicsDropShadowEffect(blurRadius=25, xOffset=2, yOffset=2)
        )
        print("[MainWindow] UI effects applied")

        self.PlaylistLink.returnPressed.connect(self.on_returnButton)
        self.DownloadBtn.clicked.connect(self.on_returnButton)

# It will now work both for GUI button clicks and automatic CLI URL input.
# The download will start automatically.
# 
        if len(sys.argv) > 1:
            url = sys.argv[1].strip()
            if url.startswith("https://open.spotify.com/"):
                # Set the URL in the input field
                self.PlaylistLink.setText(url)
                # Call the download function directly
                self.on_returnButton()


        
        print("[MainWindow] Download triggers connected")

        self.showPreviewCheck.stateChanged.connect(self.show_preview)
        print("[MainWindow] Preview checkbox connected")

        self.Closed.clicked.connect(self.exitprogram)
        self.Select_Home.clicked.connect(self.Linkedin)
        self.SettingsBtn.clicked.connect(self.open_settings)
        print("[MainWindow] Control buttons connected")


    # def _get_default_download_path(self):
    #     """Get a sensible default download path that's writable."""
    #     # Try user's Music folder first
    #     home = os.path.expanduser("~")
    #     music_folder = os.path.join(home, "Music", "Sunnify")

    #     # On Windows, Music might be in a different location
    #     if sys.platform == "win32":
    #         try:
    #             import winreg

    #             key = winreg.OpenKey(
    #                 winreg.HKEY_CURRENT_USER,
    #                 r"Software\Microsoft\Windows\CurrentVersion\Explorer\Shell Folders",
    #             )
    #             music_folder = os.path.join(winreg.QueryValueEx(key, "My Music")[0], "Sunnify")
    #             winreg.CloseKey(key)
    #         except Exception:
    #             music_folder = os.path.join(home, "Music", "Sunnify")

    #     return music_folder

    def _get_default_download_path(self):
        """Get a sensible default download path that's writable."""
        print("[Path] Resolving default download path")

        # Try user's Music folder first
        home = os.path.expanduser("~")
        music_folder = os.path.join(home, "Music", "Sunnify")
        print("[Path] Base path:", music_folder)

        # On Windows, Music might be in a different location
        if sys.platform == "win32":
            print("[Path] Windows platform detected")
            try:
                import winreg

                key = winreg.OpenKey(
                    winreg.HKEY_CURRENT_USER,
                    r"Software\Microsoft\Windows\CurrentVersion\Explorer\Shell Folders",
                )
                music_folder = os.path.join(
                    winreg.QueryValueEx(key, "My Music")[0], "Sunnify"
                )
                winreg.CloseKey(key)
                print("[Path] Windows Music path resolved:", music_folder)

            except Exception as e:
                print("[Path] Failed to read registry, using fallback:", e)
                music_folder = os.path.join(home, "Music", "Sunnify")

        print("[Path] Final download path:", music_folder)
        return music_folder



    # def _ensure_download_path(self):
    #     """Ensure download path exists and is writable. Returns True if valid."""
    #     try:
    #         os.makedirs(self.download_path, exist_ok=True)
    #         # Test write access
    #         test_file = os.path.join(self.download_path, ".sunnify_test")
    #         with open(test_file, "w") as f:
    #             f.write("test")
    #         os.remove(test_file)
    #         return True
    #     except OSError:
    #         return False

    def _ensure_download_path(self):
        """Ensure download path exists and is writable. Returns True if valid."""
        print("[Path] Checking download path:", self.download_path)

        try:
            os.makedirs(self.download_path, exist_ok=True)
            print("[Path] Directory exists or created")

            # Test write access
            test_file = os.path.join(self.download_path, ".sunnify_test")
            with open(test_file, "w") as f:
                f.write("test")

            os.remove(test_file)
            print("[Path] Write permission confirmed")

            return True

        except OSError as e:
            print("[Path] Path validation failed:", e)
            return False







    # def _prompt_download_location(self):
    #     """Prompt user to select download location. Returns True if selected."""
    #     folder = QFileDialog.getExistingDirectory(
    #         self,
    #         "Select Download Folder",
    #         os.path.expanduser("~"),
    #         QFileDialog.ShowDirsOnly | QFileDialog.DontResolveSymlinks,
    #     )
    #     if folder:
    #         # Create Sunnify subfolder so downloads don't splatter everywhere
    #         self.download_path = os.path.join(folder, "Sunnify")
    #         self._download_path_set = True
    #         return True
    #     return False


    def _prompt_download_location(self):
        """Prompt user to select download location. Returns True if selected."""
        print("[Path] Prompting user to select download folder")

        folder = QFileDialog.getExistingDirectory(
            self,
            "Select Download Folder",
            os.path.expanduser("~"),
            QFileDialog.ShowDirsOnly | QFileDialog.DontResolveSymlinks,
        )

        if folder:
            print("[Path] User selected folder:", folder)

            # Create Sunnify subfolder so downloads don't splatter everywhere
            self.download_path = os.path.join(folder, "Sunnify")
            self._download_path_set = True
            print("[Path] Download path set to:", self.download_path)

            return True

        print("[Path] User cancelled folder selection")
        return False




    # def open_settings(self):
    #     """Open settings dialog to choose download location."""
    #     folder = QFileDialog.getExistingDirectory(
    #         self,
    #         "Select Download Folder",
    #         self.download_path if os.path.exists(self.download_path) else os.path.expanduser("~"),
    #         QFileDialog.ShowDirsOnly | QFileDialog.DontResolveSymlinks,
    #     )
    #     if folder:
    #         self.download_path = os.path.join(folder, "Sunnify")
    #         self._download_path_set = True
    #         QMessageBox.information(
    #             self,
    #             "Settings Updated",
    #             f"Download location set to:\n{self.download_path}",
    #         )

    def open_settings(self):
        """Open settings dialog to choose download location."""
        print("[Settings] Opening download location dialog")

        folder = QFileDialog.getExistingDirectory(
            self,
            "Select Download Folder",
            self.download_path if os.path.exists(self.download_path) else os.path.expanduser("~"),
            QFileDialog.ShowDirsOnly | QFileDialog.DontResolveSymlinks,
        )

        if folder:
            print("[Settings] User selected folder:", folder)

            self.download_path = os.path.join(folder, "Sunnify")
            self._download_path_set = True
            print("[Settings] Download path updated to:", self.download_path)

            QMessageBox.information(
                self,
                "Settings Updated",
                f"Download location set to:\n{self.download_path}",
            )
        else:
            print("[Settings] No folder selected")




    # @pyqtSlot()
    # def on_returnButton(self):
    #     # If already downloading, stop the download
    #     if self._is_downloading:
    #         self._stop_download()
    #         return

    #     spotify_url = self.PlaylistLink.text().strip()
    #     if not spotify_url:
    #         self.statusMsg.setText("Please enter a Spotify URL")
    #         return

    #     # ALWAYS prompt for download location on first download
    #     if not self._download_path_set:
    #         self.statusMsg.setText("Select download location...")
    #         if not self._prompt_download_location():
    #             self.statusMsg.setText("Download cancelled - no folder selected")
    #             return

    #     # Verify the selected path is still writable
    #     if not self._ensure_download_path():
    #         self.statusMsg.setText("Cannot write to download folder")
    #         QMessageBox.warning(
    #             self,
    #             "Invalid Download Location",
    #             f"Cannot write to:\n{self.download_path}\n\nPlease select a different folder.",
    #         )
    #         if not self._prompt_download_location():
    #             return

    #     try:
    #         # Validate URL type
    #         url_type, _ = detect_spotify_url_type(spotify_url)
    #         self.statusMsg.setText(f"Detected: {url_type}")

    #         # Reset cancel event and set downloading state
    #         self._cancel_event = threading.Event()
    #         self._is_downloading = True
    #         self.DownloadBtn.setText("Stop")

    #         self.scraper_thread = ScraperThread(
    #             spotify_url, self.download_path, cancel_event=self._cancel_event
    #         )
    #         self.scraper_thread.progress_update.connect(self.update_progress)
    #         self.scraper_thread.finished.connect(self.thread_finished)
    #         self.scraper_thread.scraper.song_Album.connect(self.update_AlbumName)
    #         self.scraper_thread.scraper.song_meta.connect(self.update_song_META)
    #         self.scraper_thread.scraper.add_song_meta.connect(self.add_song_META)
    #         self.scraper_thread.scraper.dlprogress_signal.connect(self.update_song_progress)
    #         self.scraper_thread.scraper.Resetprogress_signal.connect(self.Reset_song_progress)
    #         self.scraper_thread.scraper.PlaylistCompleted.connect(
    #             lambda x: self.statusMsg.setText(x)
    #         )
    #         self.scraper_thread.scraper.error_signal.connect(lambda x: self.statusMsg.setText(x))

    #         # Connect the count_updated signal to the update_counter slot
    #         self.scraper_thread.scraper.count_updated.connect(self.update_counter)

    #         self.scraper_thread.start()

    #     except ValueError as e:
    #         self.statusMsg.setText(str(e))
    #         self._is_downloading = False
    #         self.DownloadBtn.setText("Download")


### EDITV2

    # @pyqtSlot()
    # def on_returnButton(self):
    #     print("[Main] Download button pressed")

    #     # If already downloading, stop the download
    #     if self._is_downloading:
    #         print("[Main] Download in progress → stopping")
    #         self._stop_download()
    #         return

    #     spotify_url = self.PlaylistLink.text().strip()
    #     print("[Main] Spotify URL:", spotify_url)

    #     if not spotify_url:
    #         print("[Main] No URL entered")
    #         self.statusMsg.setText("Please enter a Spotify URL")
    #         return

    #     # ALWAYS prompt for download location on first download
    #     if not self._download_path_set:
    #         print("[Main] Download path not set, prompting user")
    #         self.statusMsg.setText("Select download location...")
    #         if not self._prompt_download_location():
    #             print("[Main] User cancelled download location selection")
    #             self.statusMsg.setText("Download cancelled - no folder selected")
    #             return

    #     # Verify the selected path is still writable
    #     print("[Main] Validating download path")
    #     if not self._ensure_download_path():
    #         print("[Main] Download path not writable")
    #         self.statusMsg.setText("Cannot write to download folder")

    #         QMessageBox.warning(
    #             self,
    #             "Invalid Download Location",
    #             f"Cannot write to:\n{self.download_path}\n\nPlease select a different folder.",
    #         )

    #         if not self._prompt_download_location():
    #             print("[Main] User cancelled re-selection")
    #             return

    #     try:
    #         print("[Main] Detecting Spotify URL type")
    #         url_type, _ = detect_spotify_url_type(spotify_url)
    #         print("[Main] URL type:", url_type)
    #         self.statusMsg.setText(f"Detected: {url_type}")

    #         # Reset cancel event and set downloading state
    #         self._cancel_event = threading.Event()
    #         self._is_downloading = True
    #         self.DownloadBtn.setText("Stop")
    #         print("[Main] Download started")

    #         self.scraper_thread = ScraperThread(
    #             spotify_url, self.download_path, cancel_event=self._cancel_event
    #         )

    #         self.scraper_thread.progress_update.connect(self.update_progress)
    #         self.scraper_thread.finished.connect(self.thread_finished)
    #         self.scraper_thread.scraper.song_Album.connect(self.update_AlbumName)
    #         self.scraper_thread.scraper.song_meta.connect(self.update_song_META)
    #         self.scraper_thread.scraper.add_song_meta.connect(self.add_song_META)
    #         self.scraper_thread.scraper.dlprogress_signal.connect(self.update_song_progress)
    #         self.scraper_thread.scraper.Resetprogress_signal.connect(self.Reset_song_progress)
    #         self.scraper_thread.scraper.PlaylistCompleted.connect(
    #             lambda x: self.statusMsg.setText(x)
    #         )
    #         self.scraper_thread.scraper.error_signal.connect(
    #             lambda x: self.statusMsg.setText(x)
    #         )

    #         # Connect the count_updated signal to the update_counter slot
    #         self.scraper_thread.scraper.count_updated.connect(self.update_counter)

    #         print("[Main] Starting scraper thread")
    #         self.scraper_thread.start()

    #     except ValueError as e:
    #         print("[Main] Error:", e)
    #         self.statusMsg.setText(str(e))
    #         self._is_downloading = False
    #         self.DownloadBtn.setText("Download")




    @pyqtSlot()
    def on_returnButton(self):
        print("[Main] Download button pressed")

        # Stop download if already running
        if self._is_downloading:
            print("[Main] Download in progress → stopping")
            self._stop_download()
            return

        # Get URL from text input
        spotify_url = self.PlaylistLink.text().strip()
        print("[Main] Spotify URL:", spotify_url)

        if not spotify_url:
            print("[Main] No URL entered")
            self.statusMsg.setText("Please enter a Spotify URL")
            return

        # Set default download folder if not set
        default_path = "/home/where/Downloads/SONG/MYSONG"
        if not self._download_path_set:
            print("[Main] Setting default download folder")
            if not os.path.exists(default_path):
                print(f"[Main] Folder does not exist → creating: {default_path}")
                try:
                    os.makedirs(default_path)
                except Exception as e:
                    print("[Main] Failed to create default folder:", e)
                    self.statusMsg.setText("Failed to create default download folder")
                    return
            self.download_path = default_path
            self._download_path_set = True

        # Validate folder
        print("[Main] Validating download path")
        if not self._ensure_download_path():
            print("[Main] Download path not writable")
            self.statusMsg.setText("Cannot write to download folder")
            QMessageBox.warning(
                self,
                "Invalid Download Location",
                f"Cannot write to:\n{self.download_path}\n\nPlease select a different folder.",
            )
            if not self._prompt_download_location():
                print("[Main] User cancelled re-selection")
                return

        try:
            # Detect URL type
            print("[Main] Detecting Spotify URL type")
            url_type, _ = detect_spotify_url_type(spotify_url)
            print("[Main] URL type:", url_type)
            self.statusMsg.setText(f"Detected: {url_type}")

            # Prepare threading for download
            self._cancel_event = threading.Event()
            self._is_downloading = True
            self.DownloadBtn.setText("Stop")
            print("[Main] Download started")

            self.scraper_thread = ScraperThread(
                spotify_url, self.download_path, cancel_event=self._cancel_event
            )

            # Connect signals
            self.scraper_thread.progress_update.connect(self.update_progress)
            self.scraper_thread.finished.connect(self.thread_finished)
            self.scraper_thread.scraper.song_Album.connect(self.update_AlbumName)
            self.scraper_thread.scraper.song_meta.connect(self.update_song_META)
            self.scraper_thread.scraper.add_song_meta.connect(self.add_song_META)
            self.scraper_thread.scraper.dlprogress_signal.connect(self.update_song_progress)
            self.scraper_thread.scraper.Resetprogress_signal.connect(self.Reset_song_progress)
            self.scraper_thread.scraper.PlaylistCompleted.connect(
                lambda x: self.statusMsg.setText(x)
            )
            self.scraper_thread.scraper.error_signal.connect(
                lambda x: self.statusMsg.setText(x)
            )
            self.scraper_thread.scraper.count_updated.connect(self.update_counter)

            # Start thread
            print("[Main] Starting scraper thread")
            self.scraper_thread.start()

        except ValueError as e:
            print("[Main] Error:", e)
            self.statusMsg.setText(str(e))
            self._is_downloading = False
            self.DownloadBtn.setText("Download")











    # def _stop_download(self):
    #     """Stop the current download gracefully using cooperative cancellation."""
    #     self.statusMsg.setText("Stopping download...")

    #     # Signal cancellation via event (thread checks this periodically)
    #     self._cancel_event.set()

    #     # Wait for thread to finish gracefully
    #     if hasattr(self, "scraper_thread") and self.scraper_thread.isRunning():
    #         self.scraper_thread.request_cancel()
    #         # Give thread time to finish current operation and exit cleanly
    #         if not self.scraper_thread.wait(3000):  # Wait up to 3 seconds
    #             # Only terminate as last resort if thread doesn't respond
    #             self.scraper_thread.terminate()
    #             self.scraper_thread.wait(1000)

    #     self._is_downloading = False
    #     self.DownloadBtn.setText("Download")
    #     self.statusMsg.setText("Download stopped")


    def _stop_download(self):
        """Stop the current download gracefully using cooperative cancellation."""
        print("[Main] Stop download requested")
        self.statusMsg.setText("Stopping download...")

        # Signal cancellation via event (thread checks this periodically)
        print("[Main] Setting cancel event")
        self._cancel_event.set()

        # Wait for thread to finish gracefully
        if hasattr(self, "scraper_thread") and self.scraper_thread.isRunning():
            print("[Main] Requesting scraper thread cancel")
            self.scraper_thread.request_cancel()

            # Give thread time to finish current operation and exit cleanly
            if not self.scraper_thread.wait(3000):  # Wait up to 3 seconds
                print("[Main] Thread not responding, terminating")
                # Only terminate as last resort if thread doesn't respond
                self.scraper_thread.terminate()
                self.scraper_thread.wait(1000)
            else:
                print("[Main] Scraper thread stopped cleanly")

        self._is_downloading = False
        self.DownloadBtn.setText("Download")
        self.statusMsg.setText("Download stopped")
        print("[Main] Download stopped")





    # def thread_finished(self):
    #     """Reset UI state when download thread finishes."""
    #     self._is_downloading = False
    #     self.DownloadBtn.setText("Download")
    #     if hasattr(self, "scraper_thread"):
    #         self.scraper_thread.deleteLater()  # Clean up the thread properly

    # def update_progress(self, message):
    #     self.statusMsg.setText(message)


    def thread_finished(self):
        """Reset UI state when download thread finishes."""
        print("[Main] Scraper thread finished")

        self._is_downloading = False
        self.DownloadBtn.setText("Download")

        if hasattr(self, "scraper_thread"):
            print("[Main] Cleaning up scraper thread")
            self.scraper_thread.deleteLater()  # Clean up the thread properly

    def update_progress(self, message):
        print("[Main] Progress update:", message)
        self.statusMsg.setText(message)







    # @pyqtSlot(dict)
    # def update_song_META(self, song_meta):
    #     """Update UI with current track info (called BEFORE download starts)."""
    #     if self.showPreviewCheck.isChecked():
    #         cover_url = song_meta.get("cover", "")
    #         if cover_url:
    #             thumb_thread = DownloadThumbnail(cover_url, self)
    #             self._active_threads.append(thumb_thread)
    #             thumb_thread.finished.connect(lambda: self._cleanup_thread(thumb_thread))
    #             thumb_thread.start()
    #         self.ArtistNameText.setText(song_meta.get("artists", ""))
    #         self.AlbumText.setText(song_meta.get("album", ""))
    #         self.SongName.setText(song_meta.get("title", ""))
    #         self.YearText.setText(song_meta.get("releaseDate", ""))

    #     self.MainSongName.setText(song_meta.get("title", "") + " - " + song_meta.get("artists", ""))
    #     # NOTE: Meta tags are written in add_song_META (after file exists), not here

    # @pyqtSlot(dict)
    # def add_song_META(self, song_meta):
    #     if self.AddMetaDataCheck.isChecked():
    #         meta_thread = WritingMetaTagsThread(song_meta, song_meta["file"])
    #         meta_thread.tags_success.connect(lambda x: self.statusMsg.setText(f"{x}"))
    #         self._active_threads.append(meta_thread)
    #         meta_thread.finished.connect(lambda: self._cleanup_thread(meta_thread))
    #         meta_thread.start()

    @pyqtSlot(dict)
    def update_song_META(self, song_meta):
        """Update UI with current track info (called BEFORE download starts)."""
        print("[UI] update_song_META called")
        print("[UI] Song meta:", song_meta)

        if self.showPreviewCheck.isChecked():
            print("[UI] Preview enabled")

            cover_url = song_meta.get("cover", "")
            if cover_url:
                print("[UI] Cover URL found, downloading thumbnail")
                thumb_thread = DownloadThumbnail(cover_url, self)
                self._active_threads.append(thumb_thread)
                thumb_thread.finished.connect(lambda: self._cleanup_thread(thumb_thread))
                thumb_thread.start()

            self.ArtistNameText.setText(song_meta.get("artists", ""))
            self.AlbumText.setText(song_meta.get("album", ""))
            self.SongName.setText(song_meta.get("title", ""))
            self.YearText.setText(song_meta.get("releaseDate", ""))
        else:
            print("[UI] Preview disabled")

        self.MainSongName.setText(
            song_meta.get("title", "") + " - " + song_meta.get("artists", "")
        )
        print("[UI] Main song title updated")

        # NOTE: Meta tags are written in add_song_META (after file exists), not here

    @pyqtSlot(dict)
    def add_song_META(self, song_meta):
        print("[UI] add_song_META called")

        if self.AddMetaDataCheck.isChecked():
            print("[UI] Metadata writing enabled")

            meta_thread = WritingMetaTagsThread(song_meta, song_meta["file"])
            meta_thread.tags_success.connect(lambda x: self.statusMsg.setText(f"{x}"))

            self._active_threads.append(meta_thread)
            meta_thread.finished.connect(lambda: self._cleanup_thread(meta_thread))
            meta_thread.start()
        else:
            print("[UI] Metadata writing disabled")




    # def _cleanup_thread(self, thread):
    #     """Remove finished thread from active list."""
    #     if thread in self._active_threads:
    #         self._active_threads.remove(thread)

    # @pyqtSlot(str)
    # def update_AlbumName(self, AlbumName):
    #     self.AlbumName.setText("Playlist Name : " + AlbumName)

    # @pyqtSlot(int)
    # def update_counter(self, count):
    #     self.CounterLabel.setText("Songs downloaded " + str(count))

    # @pyqtSlot(int)
    # def update_song_progress(self, progress):
    #     self.SongDownloadprogressBar.setValue(progress)
    #     self.SongDownloadprogress.setValue(progress)

    # @pyqtSlot(int)
    # def Reset_song_progress(self, progress):
    #     self.SongDownloadprogressBar.setValue(0)
    #     self.SongDownloadprogress.setValue(0)


    def _cleanup_thread(self, thread):
        """Remove finished thread from active list."""
        print("[Thread] Cleaning up thread:", thread)

        if thread in self._active_threads:
            self._active_threads.remove(thread)
            print("[Thread] Thread removed from active list")

    @pyqtSlot(str)
    def update_AlbumName(self, AlbumName):
        print("[UI] Album name updated:", AlbumName)
        self.AlbumName.setText("Playlist Name : " + AlbumName)

    @pyqtSlot(int)
    def update_counter(self, count):
        print("[UI] Download count:", count)
        self.CounterLabel.setText("Songs downloaded " + str(count))

    @pyqtSlot(int)
    def update_song_progress(self, progress):
        print("[UI] Song progress:", progress)
        self.SongDownloadprogressBar.setValue(progress)
        self.SongDownloadprogress.setValue(progress)

    @pyqtSlot(int)
    def Reset_song_progress(self, progress):
        print("[UI] Song progress reset")
        self.SongDownloadprogressBar.setValue(0)
        self.SongDownloadprogress.setValue(0)









    # # DRAGGLESS INTERFACE
    # def mousePressEvent(self, event):
    #     if event.button() == Qt.LeftButton:
    #         self.m_drag = True
    #         self.m_DragPosition = event.globalPos() - self.pos()
    #         event.accept()
    #         self.setCursor(QCursor(Qt.ClosedHandCursor))

    # def mouseMoveEvent(self, QMouseEvent):
    #     try:
    #         if Qt.LeftButton and self.m_drag:
    #             self.move(QMouseEvent.globalPos() - self.m_DragPosition)
    #             QMouseEvent.accept()
    #     except AttributeError:
    #         pass

    # def mouseReleaseEvent(self, QMouseEvent):
    #     self.m_drag = False
    #     self.setCursor(QCursor(Qt.ArrowCursor))

    # def CloseSongInformation(self):
    #     self.animation = QPropertyAnimation(self.SONGINFORMATION, b"size")
    #     self.animation.setDuration(250)
    #     self.animation.setEndValue(QSize(0, 440))
    #     self.animation.setEasingCurve(QEasingCurve.InOutQuad)
    #     self.animation.start()

    # def OpenSongInformation(self):
    #     self.animation = QPropertyAnimation(self.SONGINFORMATION, b"size")
    #     self.animation.setDuration(1000)
    #     self.animation.setEndValue(QSize(350, 440))
    #     self.animation.setEasingCurve(QEasingCurve.InOutQuad)
    #     self.animation.start()

    # def show_preview(self, state):
    #     if state == 2:  # 2 corresponds to checked state
    #         self.preview_window = self.OpenSongInformation()
    #     else:
    #         self.CloseSongInformation()

    # def exitprogram(self):
    #     sys.exit()

    # def Linkedin(self):
    #     webbrowser.open("https://www.linkedin.com/in/sunny-patel-30b460204/")


    # DRAGGLESS INTERFACE
    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            print("[UI] Mouse press - drag start")
            self.m_drag = True
            self.m_DragPosition = event.globalPos() - self.pos()
            event.accept()
            self.setCursor(QCursor(Qt.ClosedHandCursor))

    def mouseMoveEvent(self, QMouseEvent):
        try:
            if Qt.LeftButton and self.m_drag:
                print("[UI] Mouse move - dragging window")
                self.move(QMouseEvent.globalPos() - self.m_DragPosition)
                QMouseEvent.accept()
        except AttributeError:
            print("[UI] Mouse move - drag state missing")

    def mouseReleaseEvent(self, QMouseEvent):
        print("[UI] Mouse release - drag stop")
        self.m_drag = False
        self.setCursor(QCursor(Qt.ArrowCursor))

    def CloseSongInformation(self):
        print("[UI] Closing song information panel")
        self.animation = QPropertyAnimation(self.SONGINFORMATION, b"size")
        self.animation.setDuration(250)
        self.animation.setEndValue(QSize(0, 440))
        self.animation.setEasingCurve(QEasingCurve.InOutQuad)
        self.animation.start()

    def OpenSongInformation(self):
        print("[UI] Opening song information panel")
        self.animation = QPropertyAnimation(self.SONGINFORMATION, b"size")
        self.animation.setDuration(1000)
        self.animation.setEndValue(QSize(350, 440))
        self.animation.setEasingCurve(QEasingCurve.InOutQuad)
        self.animation.start()

    def show_preview(self, state):
        print("[UI] Preview toggle state:", state)
        if state == 2:  # Checked
            self.preview_window = self.OpenSongInformation()
        else:
            self.CloseSongInformation()

    def exitprogram(self):
        print("[App] Exiting application")
        sys.exit()

    def Linkedin(self):
        print("[UI] Opening LinkedIn profile")
        webbrowser.open("https://www.linkedin.com/in/sunny-patel-30b460204/")


# Main
if __name__ == "__main__":
    app = QApplication(sys.argv)
    Screen = MainWindow()
    Screen.setFixedHeight(500)
    Screen.setFixedWidth(750)
    Screen.setWindowFlags(Qt.FramelessWindowHint)
    Screen.setAttribute(Qt.WA_TranslucentBackground)
    Screen.show()
    sys.exit(app.exec())
