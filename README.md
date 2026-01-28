<div align="center">

<h1>Sunnify (Spotify Downloader)</h1>



```
github.com/sunnypatell/sunnify-spotify-downloader
```

<br/>

<img src="./app.png" alt="Sunnify" height="96" />

</div>

[!CAUTION]
**⚠️ EDUCATIONAL PROJECT DISCLAIMER**
>
This software was developed as a **student portfolio project** for educational purposes only. It is intended to demonstrate software engineering skills including API integration, multi-threading, cross-platform development, and full-stack architecture.
>
**By using this software, you acknowledge that:**
- You will only use it in jurisdictions where downloading copyrighted content for personal use is permitted
- You are responsible for complying with all applicable laws in your region
- This tool should only be used with content you own or have explicit permission to download
- The developer assumes no liability for misuse of this software
>
**See [full disclaimer](#legal-disclaimer) below and read [DISCLAIMER.md](DISCLAIMER.md) for complete legal terms.**

<p align="center">
    <a href="#table-of-contents">Jump to Table of Contents</a>
</p>

<hr/>


---

## Table of Contents

1. Usage Guide

### Usage Guide

```bash
# Clone the repository
git clone https://github.com/Tpj-root/sunnify-spotify-downloader-bash.git
cd sunnify-spotify-downloader-bash

# Create and activate a virtual environment (recommended)
python3 -m venv .venv
source .venv/bin/activate

# Install required Python dependencies
pip install -r req.txt

# Ensure FFmpeg is installed and available on PATH
ffmpeg -version

# Download tracks from your list
bash download_tracks.sh
```

### Notes

* **Default download path:**

```python
default_path = "/home/where/Downloads/SONG/MYSONGS"
```

You can modify this to any folder where you want your songs saved.

**Using your own track list:**

Create a `track_ids.txt` file with one Spotify track ID per line:

```
2plbrEY59IikOBgBGLjaoe
3sK8wGT43QFpWrvNQsrQya
6dOtVTDdiauQNBQEDOtlAB
0zirWZTcXBBwGsevrsIpvT
2lTm559tuIvatlT1u0JYG2
6AI3ezQ4o3HUoP6Dhudph3
7ne4VBA60CxGM75vw0EYad
5vNRhkKd0yEAg8suGBpjeY
3GCdLUSnKSMJhs4Tj6CV3s
```

**Why this version:**

The original script sometimes misses tracks in large playlists (e.g., 55+ songs). This modified version downloads using a custom track list to ensure no songs are skipped.

**Pro tip:**

Always double-check your track list and the download folder path to avoid missing files.


**Note:**
If the script encounters an error like:

```
ERROR: unable to download video data: HTTP Error 403: Forbidden
```

**Don’t worry!** 


If a download fails, simply click the download button again.
The script will automatically retry, ensuring you never miss any track from your list.


If a track ID already exists in the local folder, 
it will be skipped and won’t be downloaded again.


The script also checks your tracker list and counts missing songs. 
Just run the script again, and any missing tracks will be downloaded automatically.



The top 10,000 songs span popularities 70–100. You can view them all in this [HTML file](https://annas-archive.li/blog/spotify/spotify-top-10k-songs-table.html).


## Generate `track_id` List


Download the CSV file containing the top 10,000 tracks:


```bash
wget https://raw.githubusercontent.com/Tpj-root/SiteTracker/refs/heads/main/10000_list.csv
```


Extract the `track_id` column (first 10 entries):

```
head -n 10 10000_list.csv | awk -F',' '{print $2}'
```

Or, using a cleaner one-liner:

```
awk -F',' 'NR<=10 {print $2}' 10000_list.csv
```

This generates a plain list of Spotify `track_id`s ready for further processing.


## Add detailed study notes and logging for Spotify API workflow

- [x] Added [debug](https://raw.githubusercontent.com/Tpj-root/sunnify-spotify-downloader-bash/refs/heads/main/API_OUT) logging for all SpotifyEmbedAPI methods to track variable values and API calls
- [] Instrumented PlaylistClient and helper functions (extract IDs, detect URL type, sanitize filenames) for full terminal trace
- [] Added Bash redirection notes for stdout and stderr logging
- [] Provides clear visual trace for understanding API flow and debugging


