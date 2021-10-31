# theHandy_Plex

**REQUIRES PLEX PASS**

Webhooks are a plex premium feature, you need to pay for it

# How to setup
## 1: Git clone or download this branch**


## 2: Run plexv2.py once


## 3: Edit settings.json


Set app_secret to a random string


Set plex_token (X-Plex-Token) to your plex_token, this can be found in your web f12 menu on the networks section when doing something on app.plex.tv.


Set handy_key to your handy key.


Modify plex_ip to the plex server ip, if this script runs on a different ip, otherwise leave it be.


Set access_ip, this should be the ip of the machine that runs plex script, this enables local script upload instead of uploading the script to the handyfeeling server and is recommended.


Set view_offset to 50 if not using pause_sync.


Set pause_sync if you want to use the experimental pause sync.


Pause sync attempts to find the plex webhook delay by sending pause and play commands to plex and recording the latency until it receives said webhook response again.

Also use 0 view_offset if using pause_sync, otherwise it will be way off.


## 4: Add a webhook with http://127.0.0.1:8008 (or the ip of the machine running the script) as the address to plex.


## 5: Install systemd service


Copy the plex_hand.service file into /etc/systemd/system and edit the user, group and directory path.


## 6: Done


# How to use

Name the script the same as the video file, and have them in the same directory.

Like:

video.mp4

video.funscript or video.csv

# Known bugs
There is no webhook call for media scrubbing, so to resync after scrub you need to pause and play it again.

Slow initialization, since the script attempts to find the latency the handy's api, takes about 10s~.

Custom transcoding sometimes excludes original file path, so the script is unable to find the funscript.
