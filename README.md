# theHandy_Plex

REQUIRES PLEX PASS

# How to setup
Run a plex server.

Get your plex token (google how to).

Get your handy key.

Copy this directory (most importantly handy.py and plex.py)

With python pip run "pip install -r requirements.txt"

Edit both values into plex.py

Run plex.py on the same machine as the plex server.

Add a webhook with http://127.0.0.1:8008 as the address to plex.

Done.

# How to use

Name the script the same as the video file, and have them in the same directory.

Like:

video.mp4

video.funscript


# Known bugs
There is no webhook call for media scrubbing, so to scrub you need to pause and play it again, for the script to detect it.

Offset is finicky, try stopping and starting.

viewOffset bugs:

If you set the videotime to below 1 minute, plex excludes viewOffset, which is then set to 0 instead.

If you have previously seen a video, and you start from 0 seconds in, viewOffset is still set to your last watchtime.

