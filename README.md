# theHandy_Plex

# How to setup
Run a plex server.

Get your plex token (google how to).

Get your handy key.


Edit both values into plex.py

Run plex.py on the same machine as the plex server.

# Known bugs
There is no webhook call for media scrubbing, so to scrub you need to pause and play it again, for the script to detect it.

Offset is finicky, try stopping and starting.

# viewOffset bugs
If you set the videotime to below 1 minute, plex excludes viewOffset, which is then set to 0 instead.

If you have previously seen a video, and you start from 0 seconds in, viewOffset is still set to your last watchtime.

