"""Spotify playlist data fetcher with multiple fallback endpoints.

Primary: Embed page (/embed/playlist/{id}) - returns up to 100 tracks
Fallback: spclient API - returns full track URIs for large playlists
Individual: Track embed pages - for metadata on tracks beyond 100

All methods work without authentication by extracting anonymous tokens
from Spotify's embed pages.
"""

from __future__ import annotations

import functools
import json
import re
import time
from collections.abc import Iterator, Sequence
from dataclasses import dataclass
from typing import Callable, TypeVar

import requests

T = TypeVar("T")

_DEFAULT_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/120.0.0.0 Safari/537.36"
)


class SpotifyDownAPIError(RuntimeError):
    """Raised when Spotify data cannot be fetched."""


class NetworkError(SpotifyDownAPIError):
    """Network/connectivity issues - typically retryable."""


class ExtractionError(SpotifyDownAPIError):
    """Failed to extract data from response - usually not retryable."""


class RateLimitError(SpotifyDownAPIError):
    """Rate limited by Spotify - should back off before retrying."""


# def retry_on_network_error(
#     max_attempts: int = 3,
#     backoff_factor: float = 1.0,
#     exceptions: tuple = (NetworkError, requests.Timeout, requests.ConnectionError),
# ) -> Callable[[Callable[..., T]], Callable[..., T]]:
#     """Decorator to retry a function on network errors with exponential backoff.

#     Args:
#         max_attempts: Maximum number of attempts before giving up
#         backoff_factor: Multiplier for wait time between attempts (wait = backoff_factor * 2^attempt)
#         exceptions: Tuple of exception types to catch and retry
#     """

#     def decorator(func: Callable[..., T]) -> Callable[..., T]:
#         @functools.wraps(func)
#         def wrapper(*args, **kwargs) -> T:
#             last_exception = None
#             for attempt in range(max_attempts):
#                 try:
#                     return func(*args, **kwargs)
#                 except exceptions as e:
#                     last_exception = e
#                     if attempt < max_attempts - 1:
#                         wait_time = backoff_factor * (2**attempt)
#                         time.sleep(wait_time)
#             raise last_exception  # type: ignore

#         return wrapper

#     return decorator


def retry_on_network_error(
    max_attempts: int = 3,
    backoff_factor: float = 1.0,
    exceptions: tuple = (NetworkError, requests.Timeout, requests.ConnectionError),
) -> Callable[[Callable[..., T]], Callable[..., T]]:
    """
    Decorator to retry a function on network errors with exponential backoff.

    Short notes:
    - Retries only for given network-related exceptions
    - Uses exponential backoff: wait = backoff_factor * (2 ** attempt)
    - Raises last exception after all attempts fail
    """

    print("[Retry_API] Initialized decorator")
    print("[Retry_API] max_attempts :", max_attempts)
    print("[Retry_API] backoff_factor :", backoff_factor)
    print("[Retry_API] exceptions :", exceptions)
    print("-" * 50)

    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        print(f"[Retry_API] Decorating function : {func.__name__}")

        @functools.wraps(func)
        def wrapper(*args, **kwargs) -> T:
            print("\n[Retry_API] Function call started")
            print("[Retry_API] Function name :", func.__name__)
            print("[Retry_API] Raw args :", args)
            print("[Retry_API] Raw kwargs :", kwargs)

            last_exception = None

            for attempt in range(max_attempts):
                print("\n[Retry_API] Attempt :", attempt + 1, "/", max_attempts)

                try:
                    print("[Retry_API] Calling target function...")
                    result = func(*args, **kwargs)
                    print("[Retry_API] Function executed successfully")
                    print("[Retry_API] Result :", result)
                    return result

                except exceptions as e:
                    last_exception = e
                    print("[Retry_API] Caught exception :", type(e).__name__)
                    print("[Retry_API] Exception message :", e)

                    if attempt < max_attempts - 1:
                        wait_time = backoff_factor * (2 ** attempt)
                        print("[Retry_API] Will retry after", wait_time, "seconds")
                        time.sleep(wait_time)
                    else:
                        print("[Retry_API] Max attempts reached. No more retries.")

            print("[Retry_API] Raising last exception")
            raise last_exception  # type: ignore

        return wrapper

    return decorator




# @dataclass
# class PlaylistInfo:
#     name: str
#     owner: str | None
#     description: str | None
#     cover_url: str | None
#     track_count: int | None = None


# @dataclass
# class TrackInfo:
#     id: str
#     title: str
#     artists: str
#     album: str | None
#     release_date: str | None
#     cover_url: str | None
#     duration_ms: int | None
#     preview_url: str | None
#     raw: dict[str, object]

#     @property
#     def spotify_id(self) -> str:
#         """Alias for id field for compatibility."""
#         return self.id


# =========================
# [Spotify_API] PlaylistInfo
# =========================
@dataclass
class PlaylistInfo:
    name: str
    owner: str | None
    description: str | None
    cover_url: str | None
    track_count: int | None = None

    def __post_init__(self):
        print("\n[Spotify_API][PlaylistInfo] Object created")
        print("[Spotify_API] name        :", self.name)
        print("[Spotify_API] owner       :", self.owner)
        print("[Spotify_API] description :", self.description)
        print("[Spotify_API] cover_url   :", self.cover_url)
        print("[Spotify_API] track_count :", self.track_count)


# =========================
# [Spotify_API] TrackInfo
# =========================
@dataclass
class TrackInfo:
    id: str
    title: str
    artists: str
    album: str | None
    release_date: str | None
    cover_url: str | None
    duration_ms: int | None
    preview_url: str | None
    raw: dict[str, object]

    def __post_init__(self):
        print("\n[Spotify_API][TrackInfo] Object created")
        print("[Spotify_API] id           :", self.id)
        print("[Spotify_API] title        :", self.title)
        print("[Spotify_API] artists      :", self.artists)
        print("[Spotify_API] album        :", self.album)
        print("[Spotify_API] release_date :", self.release_date)
        print("[Spotify_API] cover_url    :", self.cover_url)
        print("[Spotify_API] duration_ms  :", self.duration_ms)
        print("[Spotify_API] preview_url  :", self.preview_url)
        print("[Spotify_API] raw keys     :", list(self.raw.keys()))

    @property
    def spotify_id(self) -> str:
        """
        Short notes:
        - Compatibility alias
        - Returns same value as `id`
        """
        print("[Spotify_API] Accessed spotify_id property →", self.id)
        return self.id











# class SpotifyEmbedAPI:
#     """Fetch playlist data from Spotify's embed page.

#     The embed page (https://open.spotify.com/embed/playlist/{id}) contains
#     full track data in a __NEXT_DATA__ JSON blob, including:
#     - Track titles, artists, durations
#     - Track URIs/IDs
#     - 96kbps audio preview URLs
#     - Anonymous access tokens (can be used with spclient API)

#     This works without any authentication.
#     Limitation: Returns max ~100 tracks per playlist.
#     """

#     _EMBED_PLAYLIST_URL = "https://open.spotify.com/embed/playlist/{playlist_id}"
#     _EMBED_TRACK_URL = "https://open.spotify.com/embed/track/{track_id}"
#     _OEMBED_URL = "https://open.spotify.com/oembed"
#     _SPCLIENT_URL = "https://spclient.wg.spotify.com/playlist/v2/playlist/{playlist_id}"
#     _NEXT_DATA_PATTERN = re.compile(r'<script id="__NEXT_DATA__"[^>]*>([^<]+)</script>')

#     def __init__(self, *, session: requests.Session | None = None) -> None:
#         self._session = session or requests.Session()
#         self._cached_token: str | None = None
#         self._token_expiry: float = 0

#     def _headers(self) -> dict[str, str]:
#         return {
#             "accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
#             "accept-language": "en-US,en;q=0.9",
#             "user-agent": _DEFAULT_USER_AGENT,
#         }

#     @retry_on_network_error(max_attempts=3, backoff_factor=1.0)
#     def _fetch_embed_data(self, url: str) -> dict:
#         """Fetch and parse __NEXT_DATA__ from any embed page.

#         Raises:
#             NetworkError: For connection issues (retryable)
#             RateLimitError: When rate limited by Spotify (retryable with backoff)
#             ExtractionError: When page structure is unexpected (not retryable)
#         """
#         try:
#             response = self._session.get(url, headers=self._headers(), timeout=30)
#         except (requests.Timeout, requests.ConnectionError) as exc:
#             raise NetworkError(f"Network error fetching embed page: {exc}") from exc
#         except requests.RequestException as exc:
#             raise SpotifyDownAPIError(f"Failed to fetch embed page: {exc}") from exc

#         if response.status_code == 429:
#             raise RateLimitError("Rate limited by Spotify - please wait before retrying")
#         if response.status_code in (401, 403):
#             raise ExtractionError(
#                 f"Access denied (HTTP {response.status_code}) - playlist may be private"
#             )
#         if response.status_code != 200:
#             raise NetworkError(f"Embed page returned HTTP {response.status_code}")

#         match = self._NEXT_DATA_PATTERN.search(response.text)
#         if not match:
#             raise ExtractionError("Could not find __NEXT_DATA__ in embed page")

#         try:
#             data = json.loads(match.group(1))
#         except json.JSONDecodeError as exc:
#             raise ExtractionError(f"Invalid JSON in __NEXT_DATA__: {exc}") from exc

#         # Cache the access token if present
#         try:
#             session_data = data["props"]["pageProps"]["state"]["settings"]["session"]
#             self._cached_token = session_data.get("accessToken")
#             expiry_ms = session_data.get("accessTokenExpirationTimestampMs", 0)
#             self._token_expiry = expiry_ms / 1000 if expiry_ms else 0
#         except (KeyError, TypeError):
#             pass

#         return data

class SpotifyEmbedAPI:
    """Fetch playlist data from Spotify's embed page.

    Short notes:
    - Uses Spotify embed pages (no auth needed)
    - Extracts __NEXT_DATA__ JSON
    - Caches anonymous access token if available
    """

    _EMBED_PLAYLIST_URL = "https://open.spotify.com/embed/playlist/{playlist_id}"
    _EMBED_TRACK_URL = "https://open.spotify.com/embed/track/{track_id}"
    _OEMBED_URL = "https://open.spotify.com/oembed"
    _SPCLIENT_URL = "https://spclient.wg.spotify.com/playlist/v2/playlist/{playlist_id}"
    _NEXT_DATA_PATTERN = re.compile(r'<script id="__NEXT_DATA__"[^>]*>([^<]+)</script>')

    def __init__(self, *, session: requests.Session | None = None) -> None:
        print("[Spotify_API] Initializing SpotifyEmbedAPI")
        self._session = session or requests.Session()
        self._cached_token: str | None = None
        self._token_expiry: float = 0
        print("[Spotify_API] Session ready")

    def _headers(self) -> dict[str, str]:
        headers = {
            "accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "accept-language": "en-US,en;q=0.9",
            "user-agent": _DEFAULT_USER_AGENT,
        }
        print("[Spotify_API] Request headers :", headers)
        return headers

    @retry_on_network_error(max_attempts=3, backoff_factor=1.0)
    def _fetch_embed_data(self, url: str) -> dict:
        """Fetch and parse __NEXT_DATA__ from embed page."""
        print("\n[Spotify_API] Fetching embed URL :", url)

        try:
            response = self._session.get(url, headers=self._headers(), timeout=30)
            print("[Spotify_API] HTTP status :", response.status_code)
        except (requests.Timeout, requests.ConnectionError) as exc:
            print("[Spotify_API] Network exception :", exc)
            raise NetworkError(f"Network error fetching embed page: {exc}") from exc
        except requests.RequestException as exc:
            print("[Spotify_API] Request exception :", exc)
            raise SpotifyDownAPIError(f"Failed to fetch embed page: {exc}") from exc

        if response.status_code == 429:
            print("[Spotify_API] Rate limited (429)")
            raise RateLimitError("Rate limited by Spotify - please wait before retrying")
        if response.status_code in (401, 403):
            print("[Spotify_API] Access denied :", response.status_code)
            raise ExtractionError(
                f"Access denied (HTTP {response.status_code}) - playlist may be private"
            )
        if response.status_code != 200:
            print("[Spotify_API] Unexpected HTTP status")
            raise NetworkError(f"Embed page returned HTTP {response.status_code}")

        print("[Spotify_API] Searching for __NEXT_DATA__")
        match = self._NEXT_DATA_PATTERN.search(response.text)
        if not match:
            print("[Spotify_API] __NEXT_DATA__ not found")
            raise ExtractionError("Could not find __NEXT_DATA__ in embed page")

        print("[Spotify_API] __NEXT_DATA__ found, parsing JSON")
        try:
            data = json.loads(match.group(1))
            print("[Spotify_API] JSON parsed successfully")
        except json.JSONDecodeError as exc:
            print("[Spotify_API] JSON decode error :", exc)
            raise ExtractionError(f"Invalid JSON in __NEXT_DATA__: {exc}") from exc

        # Cache the access token if present
        try:
            session_data = data["props"]["pageProps"]["state"]["settings"]["session"]
            self._cached_token = session_data.get("accessToken")
            expiry_ms = session_data.get("accessTokenExpirationTimestampMs", 0)
            self._token_expiry = expiry_ms / 1000 if expiry_ms else 0

            print("[Spotify_API] Cached token :", bool(self._cached_token))
            print("[Spotify_API] Token expiry (s) :", self._token_expiry)
        except (KeyError, TypeError):
            print("[Spotify_API] No session token found")

        print("[Spotify_API] Embed data ready")
        return data



    # def _extract_entity(self, data: dict) -> dict:
    #     """Extract the entity data from __NEXT_DATA__."""
    #     try:
    #         return data["props"]["pageProps"]["state"]["data"]["entity"]
    #     except (KeyError, TypeError) as exc:
    #         raise ExtractionError(f"Unexpected embed page structure: {exc}") from exc


    # def _get_access_token(self, playlist_id: str) -> str | None:
    #     """Get a valid access token, refreshing if needed."""
    #     if self._cached_token and time.time() < self._token_expiry - 60:
    #         return self._cached_token

    #     # Fetch embed page to get fresh token
    #     url = self._EMBED_PLAYLIST_URL.format(playlist_id=playlist_id)
    #     self._fetch_embed_data(url)
    #     return self._cached_token


    def _extract_entity(self, data: dict) -> dict:
        """Extract the entity data from __NEXT_DATA__."""
        print("[Spotify_api] Starting _extract_entity with data keys:", list(data.keys()))
        try:
            entity = data["props"]["pageProps"]["state"]["data"]["entity"]
            print("[Spotify_api] Extracted entity:", entity)
            return entity
        except (KeyError, TypeError) as exc:
            print("[Spotify_api] Extraction failed:", exc)
            raise ExtractionError(f"Unexpected embed page structure: {exc}") from exc


    def _get_access_token(self, playlist_id: str) -> str | None:
        """Get a valid access token, refreshing if needed."""
        print(f"[Spotify_api] Requested access token for playlist_id: {playlist_id}")
        current_time = time.time()
        print("[Spotify_api] Current time:", current_time)
        if self._cached_token and current_time < self._token_expiry - 60:
            print("[Spotify_api] Using cached token:", self._cached_token)
            return self._cached_token

        # Fetch embed page to get fresh token
        url = self._EMBED_PLAYLIST_URL.format(playlist_id=playlist_id)
        print("[Spotify_api] Fetching embed data from URL:", url)
        self._fetch_embed_data(url)
        print("[Spotify_api] New cached token after fetch:", self._cached_token)
        return self._cached_token





    # def get_playlist_metadata(self, playlist_id: str) -> PlaylistInfo:
    #     """Get playlist metadata from the embed page."""
    #     url = self._EMBED_PLAYLIST_URL.format(playlist_id=playlist_id)
    #     data = self._fetch_embed_data(url)
    #     entity = self._extract_entity(data)

    #     name = entity.get("name") or entity.get("title") or "Unknown Playlist"
    #     subtitle = entity.get("subtitle")

    #     # Get cover URL from coverArt sources
    #     cover_url = None
    #     cover_art = entity.get("coverArt", {})
    #     sources = cover_art.get("sources", [])
    #     if sources:
    #         cover_url = sources[-1].get("url") if sources else None

    #     # Get track count - try spclient for accurate count
    #     track_list = entity.get("trackList", [])
    #     track_count = len(track_list)

    #     # Try to get true count from spclient
    #     try:
    #         token = self._cached_token
    #         if token:
    #             spclient_url = self._SPCLIENT_URL.format(playlist_id=playlist_id)
    #             headers = {"Authorization": f"Bearer {token}", "Accept": "application/json"}
    #             resp = self._session.get(spclient_url, headers=headers, timeout=10)
    #             if resp.status_code == 200:
    #                 spc_data = resp.json()
    #                 track_count = spc_data.get("length", track_count)
    #     except Exception:
    #         pass  # Fall back to embed count

    #     return PlaylistInfo(
    #         name=str(name),
    #         owner=str(subtitle) if subtitle else None,
    #         description=entity.get("description"),
    #         cover_url=cover_url,
    #         track_count=track_count,
    #     )



    def get_playlist_metadata(self, playlist_id: str) -> PlaylistInfo:
        """Get playlist metadata from the embed page."""
        print(f"[Spotify_api] Fetching playlist metadata for ID: {playlist_id}")

        url = self._EMBED_PLAYLIST_URL.format(playlist_id=playlist_id)
        print("[Spotify_api] Embed URL:", url)

        data = self._fetch_embed_data(url)
        print("[Spotify_api] Raw embed data keys:", list(data.keys()) if isinstance(data, dict) else data)

        entity = self._extract_entity(data)
        print("[Spotify_api] Entity extracted:", entity)

        # Name and subtitle
        name = entity.get("name") or entity.get("title") or "Unknown Playlist"
        subtitle = entity.get("subtitle")
        print("[Spotify_api] Playlist name:", name)
        print("[Spotify_api] Playlist subtitle/owner:", subtitle)

        # Cover URL
        cover_url = None
        cover_art = entity.get("coverArt", {})
        sources = cover_art.get("sources", [])
        if sources:
            cover_url = sources[-1].get("url") if sources else None
        print("[Spotify_api] Cover URL:", cover_url)

        # Track count from embed
        track_list = entity.get("trackList", [])
        track_count = len(track_list)
        print("[Spotify_api] Track count from embed:", track_count)

        # Try true count from spclient
        try:
            token = self._cached_token
            print("[Spotify_api] Using cached token for spclient request:", token)
            if token:
                spclient_url = self._SPCLIENT_URL.format(playlist_id=playlist_id)
                headers = {"Authorization": f"Bearer {token}", "Accept": "application/json"}
                print("[Spotify_api] SPClient URL:", spclient_url)
                resp = self._session.get(spclient_url, headers=headers, timeout=10)
                print("[Spotify_api] SPClient response status:", resp.status_code)
                if resp.status_code == 200:
                    spc_data = resp.json()
                    track_count = spc_data.get("length", track_count)
                    print("[Spotify_api] Track count from SPClient:", track_count)
        except Exception as e:
            print("[Spotify_api] SPClient fetch failed, falling back to embed count:", e)

        playlist_info = PlaylistInfo(
            name=str(name),
            owner=str(subtitle) if subtitle else None,
            description=entity.get("description"),
            cover_url=cover_url,
            track_count=track_count,
        )
        print("[Spotify_api] Final PlaylistInfo object:", playlist_info)
        return playlist_info


    # def iter_playlist_tracks(self, playlist_id: str) -> Iterator[TrackInfo]:
    #     """Iterate over playlist tracks with fallback for large playlists.

    #     For playlists with <=100 tracks: Uses embed page (fast).
    #     For playlists with >100 tracks: Uses spclient for URIs + individual
    #     track embeds for metadata on remaining tracks.
    #     """
    #     url = self._EMBED_PLAYLIST_URL.format(playlist_id=playlist_id)
    #     data = self._fetch_embed_data(url)
    #     entity = self._extract_entity(data)

    #     track_list = entity.get("trackList", [])
    #     embed_track_ids: set[str] = set()

    #     # Yield tracks from embed page (up to ~100)
    #     for track in track_list:
    #         if not isinstance(track, dict):
    #             continue

    #         uri = track.get("uri", "")
    #         track_id = uri.split(":")[-1] if uri.startswith("spotify:track:") else ""
    #         if not track_id:
    #             continue

    #         embed_track_ids.add(track_id)
    #         yield self._parse_track(track, track_id)

    #     # Check if there are more tracks via spclient
    #     token = self._cached_token
    #     if not token:
    #         return

    #     try:
    #         spclient_url = self._SPCLIENT_URL.format(playlist_id=playlist_id)
    #         headers = {"Authorization": f"Bearer {token}", "Accept": "application/json"}
    #         resp = self._session.get(spclient_url, headers=headers, timeout=30)

    #         if resp.status_code != 200:
    #             return

    #         spc_data = resp.json()
    #         total_tracks = spc_data.get("length", 0)

    #         if total_tracks <= len(embed_track_ids):
    #             return  # All tracks already yielded

    #         # Get remaining track URIs from spclient
    #         contents = spc_data.get("contents", {})
    #         items = contents.get("items", [])

    #         for item in items:
    #             uri = item.get("uri", "")
    #             if not uri.startswith("spotify:track:"):
    #                 continue

    #             track_id = uri.split(":")[-1]
    #             if track_id in embed_track_ids:
    #                 continue  # Already yielded

    #             # Fetch individual track metadata
    #             try:
    #                 track_info = self._fetch_track_metadata(track_id)
    #                 if track_info:
    #                     yield track_info
    #             except Exception:
    #                 # If individual fetch fails, yield minimal info
    #                 yield TrackInfo(
    #                     id=track_id,
    #                     title=f"Track {track_id}",
    #                     artists="Unknown Artist",
    #                     album=None,
    #                     release_date=None,
    #                     cover_url=None,
    #                     duration_ms=None,
    #                     preview_url=None,
    #                     raw={"uri": uri},
    #                 )

    #     except Exception:
    #         pass  # spclient fallback failed, just return what we have





    def iter_playlist_tracks(self, playlist_id: str) -> Iterator[TrackInfo]:
        """Iterate over playlist tracks with fallback for large playlists."""
        print(f"[Spotify_api] Iterating tracks for playlist ID: {playlist_id}")

        url = self._EMBED_PLAYLIST_URL.format(playlist_id=playlist_id)
        print("[Spotify_api] Embed URL:", url)

        data = self._fetch_embed_data(url)
        print("[Spotify_api] Raw embed data keys:", list(data.keys()) if isinstance(data, dict) else data)

        entity = self._extract_entity(data)
        print("[Spotify_api] Entity extracted:", entity)

        track_list = entity.get("trackList", [])
        print(f"[Spotify_api] Number of tracks from embed: {len(track_list)}")

        embed_track_ids: set[str] = set()

        # Yield tracks from embed page (up to ~100)
        for track in track_list:
            if not isinstance(track, dict):
                continue

            uri = track.get("uri", "")
            track_id = uri.split(":")[-1] if uri.startswith("spotify:track:") else ""
            if not track_id:
                continue

            embed_track_ids.add(track_id)
            parsed_track = self._parse_track(track, track_id)
            print(f"[Spotify_api] Yielding embed track: {track_id} - {parsed_track.title}")
            yield parsed_track

        # Check if there are more tracks via spclient
        token = self._cached_token
        print("[Spotify_api] Cached token for spclient:", token)
        if not token:
            print("[Spotify_api] No token available, stopping iteration.")
            return

        try:
            spclient_url = self._SPCLIENT_URL.format(playlist_id=playlist_id)
            headers = {"Authorization": f"Bearer {token}", "Accept": "application/json"}
            print("[Spotify_api] SPClient URL:", spclient_url)
            resp = self._session.get(spclient_url, headers=headers, timeout=30)
            print("[Spotify_api] SPClient response status:", resp.status_code)

            if resp.status_code != 200:
                print("[Spotify_api] SPClient fetch failed, stopping iteration.")
                return

            spc_data = resp.json()
            total_tracks = spc_data.get("length", 0)
            print(f"[Spotify_api] Total tracks according to SPClient: {total_tracks}")

            if total_tracks <= len(embed_track_ids):
                print("[Spotify_api] All tracks already yielded from embed, stopping iteration.")
                return

            # Get remaining track URIs from spclient
            contents = spc_data.get("contents", {})
            items = contents.get("items", [])
            print(f"[Spotify_api] Remaining tracks from SPClient: {len(items)}")

            for item in items:
                uri = item.get("uri", "")
                if not uri.startswith("spotify:track:"):
                    continue

                track_id = uri.split(":")[-1]
                if track_id in embed_track_ids:
                    continue  # Already yielded

                # Fetch individual track metadata
                try:
                    track_info = self._fetch_track_metadata(track_id)
                    if track_info:
                        print(f"[Spotify_api] Yielding SPClient track: {track_id} - {track_info.title}")
                        yield track_info
                except Exception as e:
                    print(f"[Spotify_api] Failed to fetch track {track_id}, yielding minimal info. Error: {e}")
                    yield TrackInfo(
                        id=track_id,
                        title=f"Track {track_id}",
                        artists="Unknown Artist",
                        album=None,
                        release_date=None,
                        cover_url=None,
                        duration_ms=None,
                        preview_url=None,
                        raw={"uri": uri},
                    )

        except Exception as e:
            print("[Spotify_api] SPClient fallback failed:", e)
            pass  # spclient fallback failed, just return what we have







    # def _parse_track(self, track: dict, track_id: str) -> TrackInfo:
    #     """Parse a track dict from embed trackList."""
    #     title = track.get("title") or track.get("name") or "Unknown Track"
    #     artists = track.get("subtitle") or track.get("artists") or ""

    #     if isinstance(artists, list):
    #         artists = ", ".join(a.get("name", "") for a in artists if isinstance(a, dict))

    #     preview_url = None
    #     audio_preview = track.get("audioPreview", {})
    #     if isinstance(audio_preview, dict):
    #         preview_url = audio_preview.get("url")

    #     duration_ms = track.get("duration")

    #     return TrackInfo(
    #         id=track_id,
    #         title=str(title),
    #         artists=str(artists),
    #         album=track.get("album", {}).get("name")
    #         if isinstance(track.get("album"), dict)
    #         else None,
    #         release_date=track.get("releaseDate"),
    #         cover_url=None,
    #         duration_ms=int(duration_ms) if duration_ms else None,
    #         preview_url=preview_url,
    #         raw=dict(track),
    #     )




    def _parse_track(self, track: dict, track_id: str) -> TrackInfo:
        """Parse a track dict from embed trackList."""
        print(f"[Spotify_api] Parsing track ID: {track_id}")
        print("[Spotify_api] Raw track dict keys:", list(track.keys()) if isinstance(track, dict) else track)

        title = track.get("title") or track.get("name") or "Unknown Track"
        artists = track.get("subtitle") or track.get("artists") or ""

        if isinstance(artists, list):
            artists = ", ".join(a.get("name", "") for a in artists if isinstance(a, dict))

        print(f"[Spotify_api] Track title: {title}")
        print(f"[Spotify_api] Track artists: {artists}")

        preview_url = None
        audio_preview = track.get("audioPreview", {})
        if isinstance(audio_preview, dict):
            preview_url = audio_preview.get("url")
        print(f"[Spotify_api] Track preview URL: {preview_url}")

        duration_ms = track.get("duration")
        print(f"[Spotify_api] Track duration (ms): {duration_ms}")

        album_name = track.get("album", {}).get("name") if isinstance(track.get("album"), dict) else None
        release_date = track.get("releaseDate")
        print(f"[Spotify_api] Track album: {album_name}, release date: {release_date}")

        track_info = TrackInfo(
            id=track_id,
            title=str(title),
            artists=str(artists),
            album=album_name,
            release_date=release_date,
            cover_url=None,
            duration_ms=int(duration_ms) if duration_ms else None,
            preview_url=preview_url,
            raw=dict(track),
        )
        print("[Spotify_api] Parsed TrackInfo object:", track_info)
        return track_info







    # def _fetch_track_metadata(self, track_id: str) -> TrackInfo | None:
    #     """Fetch metadata for a single track from its embed page."""
    #     url = self._EMBED_TRACK_URL.format(track_id=track_id)

    #     try:
    #         data = self._fetch_embed_data(url)
    #         entity = self._extract_entity(data)
    #     except SpotifyDownAPIError:
    #         return None

    #     title = entity.get("name") or entity.get("title") or "Unknown Track"

    #     # Artists can be in different formats
    #     artists_data = entity.get("artists", [])
    #     if isinstance(artists_data, list):
    #         artists = ", ".join(a.get("name", "") for a in artists_data if isinstance(a, dict))
    #     else:
    #         artists = entity.get("subtitle", "")

    #     preview_url = None
    #     audio_preview = entity.get("audioPreview", {})
    #     if isinstance(audio_preview, dict):
    #         preview_url = audio_preview.get("url")

    #     # Extract cover URL from visualIdentity.image
    #     cover_url = None
    #     visual_identity = entity.get("visualIdentity", {})
    #     images = visual_identity.get("image", [])
    #     if images:
    #         # Get the largest image (usually last or highest resolution)
    #         for img in images:
    #             if isinstance(img, dict) and img.get("url"):
    #                 cover_url = img.get("url")
    #                 if img.get("maxWidth", 0) >= 300:
    #                     break  # Use 300px+ image

    #     # Extract release date properly
    #     release_date = None
    #     rd = entity.get("releaseDate")
    #     if isinstance(rd, dict):
    #         release_date = rd.get("isoString", "")[:10]  # YYYY-MM-DD
    #     elif isinstance(rd, str):
    #         release_date = rd

    #     # Try to get album name
    #     album = None
    #     # Album info might be in relatedEntityUri or other fields
    #     # For now, we'll leave it None as individual track embeds don't include album

    #     return TrackInfo(
    #         id=track_id,
    #         title=str(title),
    #         artists=str(artists),
    #         album=album,
    #         release_date=release_date,
    #         cover_url=cover_url,
    #         duration_ms=entity.get("duration"),
    #         preview_url=preview_url,
    #         raw=dict(entity),
    #     )



    def _fetch_track_metadata(self, track_id: str) -> TrackInfo | None:
        """Fetch metadata for a single track from its embed page."""
        print(f"[Spotify_api] Fetching metadata for track ID: {track_id}")

        url = self._EMBED_TRACK_URL.format(track_id=track_id)
        print("[Spotify_api] Embed track URL:", url)

        try:
            data = self._fetch_embed_data(url)
            print("[Spotify_api] Raw embed data keys:", list(data.keys()) if isinstance(data, dict) else data)

            entity = self._extract_entity(data)
            print("[Spotify_api] Entity extracted:", entity)

        except SpotifyDownAPIError as e:
            print("[Spotify_api] Spotify embed page unavailable for track:", track_id, e)
            return None

        # Track title
        title = entity.get("name") or entity.get("title") or "Unknown Track"
        print("[Spotify_api] Track title:", title)

        # Artists
        artists_data = entity.get("artists", [])
        if isinstance(artists_data, list):
            artists = ", ".join(a.get("name", "") for a in artists_data if isinstance(a, dict))
        else:
            artists = entity.get("subtitle", "")
        print("[Spotify_api] Track artists:", artists)

        # Preview URL
        preview_url = None
        audio_preview = entity.get("audioPreview", {})
        if isinstance(audio_preview, dict):
            preview_url = audio_preview.get("url")
        print("[Spotify_api] Track preview URL:", preview_url)

        # Cover URL
        cover_url = None
        visual_identity = entity.get("visualIdentity", {})
        images = visual_identity.get("image", [])
        if images:
            for img in images:
                if isinstance(img, dict) and img.get("url"):
                    cover_url = img.get("url")
                    if img.get("maxWidth", 0) >= 300:
                        break
        print("[Spotify_api] Track cover URL:", cover_url)

        # Release date
        release_date = None
        rd = entity.get("releaseDate")
        if isinstance(rd, dict):
            release_date = rd.get("isoString", "")[:10]
        elif isinstance(rd, str):
            release_date = rd
        print("[Spotify_api] Track release date:", release_date)

        # Album name (may not be available)
        album = None
        print("[Spotify_api] Track album:", album)

        duration_ms = entity.get("duration")
        print("[Spotify_api] Track duration (ms):", duration_ms)

        track_info = TrackInfo(
            id=track_id,
            title=str(title),
            artists=str(artists),
            album=album,
            release_date=release_date,
            cover_url=cover_url,
            duration_ms=duration_ms,
            preview_url=preview_url,
            raw=dict(entity),
        )
        print("[Spotify_api] Final TrackInfo object:", track_info)

        return track_info






    # def validate_playlist(self, playlist_id: str) -> bool:
    #     """Quick validation using oEmbed API (no full data fetch)."""
    #     try:
    #         params = {"url": f"https://open.spotify.com/playlist/{playlist_id}"}
    #         resp = self._session.get(self._OEMBED_URL, params=params, timeout=10)
    #         return resp.status_code == 200
    #     except Exception:
    #         return False


    def validate_playlist(self, playlist_id: str) -> bool:
        """Quick validation using oEmbed API (no full data fetch)."""
        print(f"[Spotify_api] Validating playlist ID: {playlist_id}")

        try:
            params = {"url": f"https://open.spotify.com/playlist/{playlist_id}"}
            print("[Spotify_api] oEmbed API request params:", params)

            resp = self._session.get(self._OEMBED_URL, params=params, timeout=10)
            print("[Spotify_api] oEmbed API response status code:", resp.status_code)

            valid = resp.status_code == 200
            print(f"[Spotify_api] Playlist validation result: {valid}")
            return valid

        except Exception as e:
            print("[Spotify_api] Playlist validation failed with exception:", e)
            return False




    # def get_track(self, track_id: str) -> TrackInfo:
    #     """Get metadata for a single track.

    #     Args:
    #         track_id: Spotify track ID

    #     Returns:
    #         TrackInfo with track metadata

    #     Raises:
    #         SpotifyDownAPIError: If track cannot be fetched
    #     """
    #     track_info = self._fetch_track_metadata(track_id)
    #     if track_info is None:
    #         raise SpotifyDownAPIError(f"Could not fetch track {track_id}")
    #     return track_info



    def get_track(self, track_id: str) -> TrackInfo:
        """Get metadata for a single track."""
        print(f"[Spotify_api] Getting track metadata for track ID: {track_id}")

        track_info = self._fetch_track_metadata(track_id)
        if track_info is None:
            print(f"[Spotify_api] Failed to fetch track {track_id}, raising SpotifyDownAPIError")
            raise SpotifyDownAPIError(f"Could not fetch track {track_id}")

        print("[Spotify_api] Successfully fetched TrackInfo:", track_info)
        return track_info



# # Legacy class kept for compatibility - redirects to embed API
# class SpotifyDownAPI:
#     """Legacy wrapper - spotifydown mirrors are dead.

#     This class is kept for API compatibility but now raises errors
#     since all spotifydown endpoints are non-functional.
#     """

#     def __init__(self, **kwargs) -> None:
#         pass

#     def get_playlist_metadata(self, playlist_id: str) -> PlaylistInfo:
#         raise SpotifyDownAPIError(
#             "spotifydown mirrors are no longer functional. Use SpotifyEmbedAPI instead."
#         )

#     def iter_playlist_tracks(self, playlist_id: str) -> Iterator[TrackInfo]:
#         raise SpotifyDownAPIError(
#             "spotifydown mirrors are no longer functional. Use SpotifyEmbedAPI instead."
#         )

#     def get_track_download_link(self, track_id: str) -> str | None:
#         raise SpotifyDownAPIError(
#             "spotifydown mirrors are no longer functional. "
#             "Use yt-dlp YouTube search for audio downloads."
#         )

#     def get_track_youtube_id(self, track_id: str) -> str | None:
#         raise SpotifyDownAPIError(
#             "spotifydown mirrors are no longer functional. "
#             "Use yt-dlp YouTube search for audio downloads."
#         )


# Legacy class kept for compatibility - redirects to embed API
class SpotifyDownAPI:
    """Legacy wrapper - spotifydown mirrors are dead."""

    def __init__(self, **kwargs) -> None:
        print("[Spotify_api] Initialized legacy SpotifyDownAPI (non-functional)")

    def get_playlist_metadata(self, playlist_id: str) -> PlaylistInfo:
        print(f"[Spotify_api] Attempted to fetch playlist metadata for {playlist_id} (legacy)")
        raise SpotifyDownAPIError(
            "spotifydown mirrors are no longer functional. Use SpotifyEmbedAPI instead."
        )

    def iter_playlist_tracks(self, playlist_id: str) -> Iterator[TrackInfo]:
        print(f"[Spotify_api] Attempted to iterate tracks for {playlist_id} (legacy)")
        raise SpotifyDownAPIError(
            "spotifydown mirrors are no longer functional. Use SpotifyEmbedAPI instead."
        )

    def get_track_download_link(self, track_id: str) -> str | None:
        print(f"[Spotify_api] Attempted to get download link for track {track_id} (legacy)")
        raise SpotifyDownAPIError(
            "spotifydown mirrors are no longer functional. "
            "Use yt-dlp YouTube search for audio downloads."
        )

    def get_track_youtube_id(self, track_id: str) -> str | None:
        print(f"[Spotify_api] Attempted to get YouTube ID for track {track_id} (legacy)")
        raise SpotifyDownAPIError(
            "spotifydown mirrors are no longer functional. "
            "Use yt-dlp YouTube search for audio downloads."
        )





# # Legacy class kept for compatibility - token endpoint is blocked
# class SpotifyPublicAPI:
#     """Legacy wrapper - Spotify's anonymous token endpoint is blocked.

#     This class is kept for API compatibility but now raises errors
#     since the /get_access_token endpoint returns 403.
#     """

#     def __init__(self, **kwargs) -> None:
#         pass

#     def get_playlist_metadata(self, playlist_id: str) -> PlaylistInfo:
#         raise SpotifyDownAPIError(
#             "Spotify's anonymous token endpoint is blocked. Use SpotifyEmbedAPI instead."
#         )

#     def iter_playlist_tracks(self, playlist_id: str) -> Iterator[TrackInfo]:
#         raise SpotifyDownAPIError(
#             "Spotify's anonymous token endpoint is blocked. Use SpotifyEmbedAPI instead."
#         )


# Legacy class kept for compatibility - token endpoint is blocked
class SpotifyPublicAPI:
    """Legacy wrapper - Spotify's anonymous token endpoint is blocked."""

    def __init__(self, **kwargs) -> None:
        print("[Spotify_api] Initialized legacy SpotifyPublicAPI (non-functional)")

    def get_playlist_metadata(self, playlist_id: str) -> PlaylistInfo:
        print(f"[Spotify_api] Attempted to fetch playlist metadata for {playlist_id} (legacy)")
        raise SpotifyDownAPIError(
            "Spotify's anonymous token endpoint is blocked. Use SpotifyEmbedAPI instead."
        )

    def iter_playlist_tracks(self, playlist_id: str) -> Iterator[TrackInfo]:
        print(f"[Spotify_api] Attempted to iterate tracks for {playlist_id} (legacy)")
        raise SpotifyDownAPIError(
            "Spotify's anonymous token endpoint is blocked. Use SpotifyEmbedAPI instead."
        )






# class PlaylistClient:
#     """High-level client for fetching Spotify playlist data.

#     Uses multiple fallback methods:
#     1. Embed page API (primary) - fast, up to 100 tracks
#     2. spclient API - for full track list on large playlists
#     3. Individual track embeds - for metadata on tracks beyond 100
#     """

#     def __init__(
#         self,
#         *,
#         session: requests.Session | None = None,
#         base_urls: Sequence[str] | None = None,  # Ignored - kept for compatibility
#     ) -> None:
#         self._session = session or requests.Session()
#         self._embed_api = SpotifyEmbedAPI(session=self._session)

#     def get_playlist_metadata(self, playlist_id: str) -> PlaylistInfo:
#         """Get playlist metadata."""
#         return self._embed_api.get_playlist_metadata(playlist_id)

#     def iter_playlist_tracks(self, playlist_id: str) -> Iterator[TrackInfo]:
#         """Iterate over all playlist tracks.

#         For large playlists (>100 tracks), automatically uses fallback
#         methods to retrieve complete track list.
#         """
#         yield from self._embed_api.iter_playlist_tracks(playlist_id)

#     def validate_playlist(self, playlist_id: str) -> bool:
#         """Quick validation that a playlist exists."""
#         return self._embed_api.validate_playlist(playlist_id)

#     def get_track_download_link(self, track_id: str) -> str | None:
#         """No longer available - spotifydown is dead.

#         Use yt-dlp YouTube search instead.
#         """
#         return None

#     def get_track_youtube_id(self, track_id: str) -> str | None:
#         """No longer available - spotifydown is dead.

#         Use yt-dlp YouTube search instead.
#         """
#         return None

#     def get_track(self, track_id: str) -> TrackInfo:
#         """Get metadata for a single track.

#         Args:
#             track_id: Spotify track ID

#         Returns:
#             TrackInfo with track metadata
#         """
#         return self._embed_api.get_track(track_id)



class PlaylistClient:
    """High-level client for fetching Spotify playlist data with debug logs."""

    def __init__(
        self,
        *,
        session: requests.Session | None = None,
        base_urls: Sequence[str] | None = None,  # Ignored - kept for compatibility
    ) -> None:
        self._session = session or requests.Session()
        print("[Spotify_api] Initialized PlaylistClient with session:", self._session)
        self._embed_api = SpotifyEmbedAPI(session=self._session)

    def get_playlist_metadata(self, playlist_id: str) -> PlaylistInfo:
        """Get playlist metadata."""
        print(f"[Spotify_api] PlaylistClient: Fetching metadata for playlist {playlist_id}")
        metadata = self._embed_api.get_playlist_metadata(playlist_id)
        print("[Spotify_api] PlaylistClient: Retrieved metadata:", metadata)
        return metadata

    def iter_playlist_tracks(self, playlist_id: str) -> Iterator[TrackInfo]:
        """Iterate over all playlist tracks."""
        print(f"[Spotify_api] PlaylistClient: Iterating tracks for playlist {playlist_id}")
        for track in self._embed_api.iter_playlist_tracks(playlist_id):
            print(f"[Spotify_api] PlaylistClient: Yielding track {track.id} - {track.title}")
            yield track

    def validate_playlist(self, playlist_id: str) -> bool:
        """Quick validation that a playlist exists."""
        print(f"[Spotify_api] PlaylistClient: Validating playlist {playlist_id}")
        valid = self._embed_api.validate_playlist(playlist_id)
        print(f"[Spotify_api] PlaylistClient: Playlist validation result: {valid}")
        return valid

    def get_track_download_link(self, track_id: str) -> str | None:
        """No longer available - spotifydown is dead."""
        print(f"[Spotify_api] PlaylistClient: get_track_download_link called for {track_id}, returning None")
        return None

    def get_track_youtube_id(self, track_id: str) -> str | None:
        """No longer available - spotifydown is dead."""
        print(f"[Spotify_api] PlaylistClient: get_track_youtube_id called for {track_id}, returning None")
        return None

    def get_track(self, track_id: str) -> TrackInfo:
        """Get metadata for a single track."""
        print(f"[Spotify_api] PlaylistClient: Fetching track {track_id}")
        track_info = self._embed_api.get_track(track_id)
        print("[Spotify_api] PlaylistClient: Retrieved TrackInfo:", track_info)
        return track_info




# Utility functions shared across desktop app and web backend


# def extract_playlist_id(url: str) -> str:
#     """Extract playlist ID from a Spotify URL.

#     Args:
#         url: Spotify playlist URL like https://open.spotify.com/playlist/ABC123

#     Returns:
#         The playlist ID (e.g., "ABC123")

#     Raises:
#         ValueError: If the URL is not a valid Spotify playlist URL
#     """
#     pattern = r"https://open\.spotify\.com/playlist/([a-zA-Z0-9]+)"
#     match = re.match(pattern, url)
#     if not match:
#         raise ValueError("Invalid Spotify playlist URL.")
#     return match.group(1)


def extract_playlist_id(url: str) -> str:
    """Extract playlist ID from a Spotify URL."""
    print(f"[Spotify_api] Extracting playlist ID from URL: {url}")

    pattern = r"https://open\.spotify\.com/playlist/([a-zA-Z0-9]+)"
    match = re.match(pattern, url)
    if not match:
        print("[Spotify_api] URL did not match Spotify playlist pattern, raising ValueError")
        raise ValueError("Invalid Spotify playlist URL.")

    playlist_id = match.group(1)
    print(f"[Spotify_api] Extracted playlist ID: {playlist_id}")
    return playlist_id







# def extract_track_id(url: str) -> str:
#     """Extract track ID from a Spotify URL.

#     Args:
#         url: Spotify track URL like https://open.spotify.com/track/ABC123

#     Returns:
#         The track ID (e.g., "ABC123")

#     Raises:
#         ValueError: If the URL is not a valid Spotify track URL
#     """
#     pattern = r"https://open\.spotify\.com/track/([a-zA-Z0-9]+)"
#     match = re.match(pattern, url)
#     if not match:
#         raise ValueError("Invalid Spotify track URL.")
#     return match.group(1)


def extract_track_id(url: str) -> str:
    """Extract track ID from a Spotify URL."""
    print(f"[Spotify_api] Extracting track ID from URL: {url}")

    pattern = r"https://open\.spotify\.com/track/([a-zA-Z0-9]+)"
    match = re.match(pattern, url)
    if not match:
        print("[Spotify_api] URL did not match Spotify track pattern, raising ValueError")
        raise ValueError("Invalid Spotify track URL.")

    track_id = match.group(1)
    print(f"[Spotify_api] Extracted track ID: {track_id}")
    return track_id




# def detect_spotify_url_type(url: str) -> tuple[str, str]:
#     """Detect the type of Spotify URL and extract the ID.

#     Args:
#         url: Spotify URL (track or playlist)

#     Returns:
#         Tuple of (type, id) where type is 'track' or 'playlist'

#     Raises:
#         ValueError: If the URL is not a valid Spotify URL
#     """
#     # Try playlist first
#     playlist_pattern = r"https://open\.spotify\.com/playlist/([a-zA-Z0-9]+)"
#     match = re.match(playlist_pattern, url)
#     if match:
#         return ("playlist", match.group(1))

#     # Try track
#     track_pattern = r"https://open\.spotify\.com/track/([a-zA-Z0-9]+)"
#     match = re.match(track_pattern, url)
#     if match:
#         return ("track", match.group(1))

#     raise ValueError("Invalid Spotify URL. Must be a track or playlist URL.")



def detect_spotify_url_type(url: str) -> tuple[str, str]:
    """Detect the type of Spotify URL and extract the ID."""
    print(f"[Spotify_api] Detecting Spotify URL type for: {url}")

    # Try playlist first
    playlist_pattern = r"https://open\.spotify\.com/playlist/([a-zA-Z0-9]+)"
    match = re.match(playlist_pattern, url)
    if match:
        playlist_id = match.group(1)
        print(f"[Spotify_api] Detected playlist URL, ID: {playlist_id}")
        return ("playlist", playlist_id)

    # Try track
    track_pattern = r"https://open\.spotify\.com/track/([a-zA-Z0-9]+)"
    match = re.match(track_pattern, url)
    if match:
        track_id = match.group(1)
        print(f"[Spotify_api] Detected track URL, ID: {track_id}")
        return ("track", track_id)

    print("[Spotify_api] URL did not match track or playlist patterns, raising ValueError")
    raise ValueError("Invalid Spotify URL. Must be a track or playlist URL.")





# def sanitize_filename(name: str, allow_spaces: bool = True) -> str:
#     """Sanitize a string for use as a filename.

#     Args:
#         name: The string to sanitize
#         allow_spaces: Whether to allow spaces in the result

#     Returns:
#         A sanitized string safe for use as a filename
#     """
#     valid_chars = set("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_-.")
#     if allow_spaces:
#         valid_chars.add(" ")
#     sanitized = "".join(c for c in name if c in valid_chars)
#     # Collapse multiple spaces and strip
#     sanitized = " ".join(sanitized.split())
#     return sanitized or "Unknown"


def sanitize_filename(name: str, allow_spaces: bool = True) -> str:
    """Sanitize a string for use as a filename."""
    print(f"[Spotify_api] Sanitizing filename: '{name}', allow_spaces={allow_spaces}")

    valid_chars = set("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_-.")
    if allow_spaces:
        valid_chars.add(" ")

    sanitized = "".join(c for c in name if c in valid_chars)
    print(f"[Spotify_api] After filtering invalid characters: '{sanitized}'")

    # Collapse multiple spaces and strip
    sanitized = " ".join(sanitized.split())
    print(f"[Spotify_api] After collapsing spaces: '{sanitized}'")

    sanitized = sanitized or "Unknown"
    print(f"[Spotify_api] Final sanitized filename: '{sanitized}'")

    return sanitized





__all__ = [
    "ExtractionError",
    "NetworkError",
    "PlaylistClient",
    "PlaylistInfo",
    "RateLimitError",
    "SpotifyDownAPI",
    "SpotifyDownAPIError",
    "SpotifyEmbedAPI",
    "SpotifyPublicAPI",
    "TrackInfo",
    "detect_spotify_url_type",
    "extract_playlist_id",
    "extract_track_id",
    "sanitize_filename",
]
