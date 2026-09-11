from pathlib import Path
import requests

from .config import PEXELS_API_KEY, PIXABAY_API_KEY


# ============================================================
# API ENDPOINTS
# ============================================================

PEXELS_API = "https://api.pexels.com/v1/videos/search"
PIXABAY_API = "https://pixabay.com/api/videos/"


# ============================================================
# PEXELS
# ============================================================

def search_pexels(query: str, min_duration: float = 3.0) -> str | None:
    """
    Search Pexels for a vertical video.

    Returns:
        Direct video URL or None if no suitable video is found.
    """

    if not PEXELS_API_KEY:
        return None

    try:
        response = requests.get(
            PEXELS_API,
            headers={
                "Authorization": PEXELS_API_KEY
            },
            params={
                "query": query,
                "orientation": "portrait",
                "per_page": 15,
                "size": "medium",
            },
            timeout=30,
        )

        response.raise_for_status()

        videos = response.json().get("videos", [])

        for video in videos:
            # Check duration
            if video.get("duration", 0) < min_duration:
                continue

            files = video.get("video_files", [])

            suitable_files = []

            for file in files:
                width = file.get("width", 0)
                height = file.get("height", 0)
                link = file.get("link")

                # Vertical video
                if (
                    link
                    and width >= 720
                    and height > width
                ):
                    suitable_files.append(file)

            if not suitable_files:
                continue

            # Choose the smallest suitable file
            # to reduce download size
            suitable_files.sort(
                key=lambda f: (
                    f.get("width", 0),
                    f.get("height", 0)
                )
            )

            return suitable_files[0]["link"]

    except requests.RequestException as e:
        print(f"[Pexels] API error: {e}")

    except Exception as e:
        print(f"[Pexels] Unexpected error: {e}")

    return None


# ============================================================
# PIXABAY
# ============================================================

def search_pixabay(query: str, min_duration: float = 3.0) -> str | None:
    """
    Search Pixabay for a vertical video.

    Returns:
        Direct video URL or None if no suitable video is found.
    """

    if not PIXABAY_API_KEY:
        return None

    try:
        response = requests.get(
            PIXABAY_API,
            params={
                "key": PIXABAY_API_KEY,
                "q": query,
                "video_type": "all",
                "safesearch": "true",
                "per_page": 20,
                "order": "popular",
            },
            timeout=30,
        )

        response.raise_for_status()

        hits = response.json().get("hits", [])

        for video in hits:

            # Check duration
            if video.get("duration", 0) < min_duration:
                continue

            video_files = video.get("videos", {})

            # Prefer higher quality first
            quality_order = [
                "large",
                "medium",
                "small",
                "tiny",
            ]

            for quality in quality_order:

                file = video_files.get(quality)

                if not file:
                    continue

                width = file.get("width", 0)
                height = file.get("height", 0)
                url = file.get("url")

                # Vertical video
                if (
                    url
                    and width >= 480
                    and height > width
                ):
                    return url

    except requests.RequestException as e:
        print(f"[Pixabay] API error: {e}")

    except Exception as e:
        print(f"[Pixabay] Unexpected error: {e}")

    return None


# ============================================================
# COMBINED SEARCH
# ============================================================

def search_video(query: str, min_duration: float = 3.0) -> str | None:
    """
    Search multiple video providers.

    Priority:
        1. Pexels
        2. Pixabay
    """

    print(f"[Visuals] Searching: {query}")

    # --------------------------------------------------------
    # PEXELS
    # --------------------------------------------------------

    url = search_pexels(
        query,
        min_duration=min_duration
    )

    if url:
        print("[Visuals] Source: Pexels")
        return url

    print("[Visuals] No suitable Pexels video found.")

    # --------------------------------------------------------
    # PIXABAY
    # --------------------------------------------------------

    url = search_pixabay(
        query,
        min_duration=min_duration
    )

    if url:
        print("[Visuals] Source: Pixabay")
        return url

    print("[Visuals] No suitable Pixabay video found.")

    return None


# ============================================================
# DOWNLOAD
# ============================================================

def download(url: str, out_path: Path) -> Path:
    """
    Download a video from a direct URL.
    """

    try:
        with requests.get(
            url,
            stream=True,
            timeout=120
        ) as response:

            response.raise_for_status()

            with open(out_path, "wb") as file:

                for chunk in response.iter_content(
                    chunk_size=1024 * 1024
                ):
                    if chunk:
                        file.write(chunk)

    except requests.RequestException as e:
        raise RuntimeError(
            f"Failed to download video: {e}"
        ) from e

    return out_path


# ============================================================
# FETCH VIDEOS FOR ALL SCENES
# ============================================================

def fetch_for_scenes(
    scenes: list[dict],
    out_dir: Path
) -> list[Path]:

    """
    Download one vertical video for every scene.

    Search order:
        Pexels -> Pixabay
    """

    out_dir.mkdir(
        parents=True,
        exist_ok=True
    )

    paths = []

    for i, scene in enumerate(scenes):

        query = scene.get(
            "visual_query",
            "abstract background"
        )

        print(
            f"\n[Visuals] Scene {i + 1}/{len(scenes)}"
        )

        # ----------------------------------------------------
        # Search using both providers
        # ----------------------------------------------------

        url = search_video(query)

        # ----------------------------------------------------
        # Fallback search
        # ----------------------------------------------------

        if url is None:

            print(
                "[Visuals] Trying fallback: "
                "abstract background"
            )

            url = search_video(
                "abstract background"
            )

        # ----------------------------------------------------
        # No result
        # ----------------------------------------------------

        if url is None:

            raise RuntimeError(
                f"No suitable video found for scene "
                f"{i}: {query}"
            )

        # ----------------------------------------------------
        # Download
        # ----------------------------------------------------

        output_path = (
            out_dir / f"scene_{i:02d}.mp4"
        )

        print(
            f"[Visuals] Downloading: {output_path.name}"
        )

        paths.append(
            download(
                url,
                output_path
            )
        )

    return paths