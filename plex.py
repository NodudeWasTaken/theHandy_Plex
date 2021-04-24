from flask import Flask, request
from xml.dom import minidom
from handy import TheHandy, upload_funscript
import json, time, requests, os, sys

app = Flask(__name__)
#Set this to anything else
app.secret_key = "much_secret_such_wow"

#Your plex token
plex_token = "YOUR_PLEX_TOKEN"
#Your handy key
handy_key = "YOUR_HANDY_KEY"
server_ip = "127.0.0.1" #TODO: Get from HTTP GET ip

default_viewoffset = 50 #50ms

#Very real database, dont question it
database = {}

def test():
	#Test plex connection
	data_url = "http://{}:32400?X-Plex-Token={}".format(server_ip,plex_token)
	with requests.get(data_url) as r:
		if (r.status_code != 200):
			raise Exception("HTTP Error when connecting to plex server {}".format(r.status_code))

	#TODO: Text handyfeeling connection
	#TODO: Test handy_key (not here, as media.play event)
	#TODO: Better errors

test()

#Return video file path
def plex_getvideofile(video_key):
	data_url = "http://{}:32400{}?X-Plex-Token={}".format(server_ip,video_key, plex_token)
	with requests.get(data_url) as r: #BUG: KeyError on non-video
		print(r.text)
		with minidom.parseString(r.text) as xmldoc:
			part = xmldoc.getElementsByTagName("Part")
			if (len(part) > 0):
				return part[0].attributes["file"].value
	
	return None

#Return viewOffset in ms
def plex_gettime(player_uuid):
	data_url = "http://{}:32400/status/sessions?X-Plex-Token={}".format(server_ip, plex_token)
	with requests.get(data_url) as r:
		with minidom.parseString(r.text) as xmldoc:
			part = xmldoc.getElementsByTagName("Video")
			for i in part:
				if (i.getElementsByTagName("Player")[0].attributes["machineIdentifier"].value) == player_uuid:
					viewOffset = int(i.attributes["viewOffset"].value)
					return viewOffset

	return None

@app.route("/", methods=["POST"])
def index():
	parsed = json.loads(request.form["payload"]) 
	unique_id = "{}_{}".format(parsed["Player"]["uuid"], parsed["Metadata"]["ratingKey"]) #TODO: Use userid instead

	print(json.dumps(parsed, indent='\t'))
	print(parsed["event"])

	#New video event
	if (parsed["event"] in ["media.resume", "media.play"]):
		if not unique_id in database:
			print("Media playback event fired")
			video_file = plex_getvideofile(parsed["Metadata"]["key"])
			if (video_file):
				print("Found video file {}".format(video_file))
				script_path = video_file[:video_file.rfind(".")] + ".funscript"
				if (os.path.exists(script_path)):
					print("Has funscript")
					database[unique_id] = TheHandy()
					script_url = upload_funscript(script_path)
					#TODO: What if this fails
					print(database[unique_id].onReady(handy_key, script_url))
					print(database[unique_id].setOffset(default_viewoffset))

		viewOffset = plex_gettime(parsed["Player"]["uuid"])
		print(database[unique_id].onPlay(viewOffset))
	
	if unique_id in database:
		if (parsed["event"] in ["media.pause", "media.stop"]):
			print(database[unique_id].onPause())
		if (parsed["event"] in ["media.stop"]):
			del database[unique_id]

	return "OK"

if __name__ == "__main__":
	app.run(host="0.0.0.0",port=8008)
