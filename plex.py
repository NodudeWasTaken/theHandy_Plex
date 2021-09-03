from flask import Flask, request, send_file
from xml.dom import minidom
from handyv2 import TheHandy
import json, time, requests, os, sys

app = Flask(__name__)

settings = {
	"app_secret": "REPLACE_ME_WITH_SOMETHING",
	"plex_token": "REPLACE_ME",
	"handy_key": "REPLACE_ME",
	"plex_ip": "REPLACE_ME",
	"access_ip": "REPLACE_ME_if_you_want",
	"view_offset": 0,
}

if not os.path.exists("settings.json"):
	with open("settings.json", "w") as f:
		json.dump(settings, f, indent="\t")
	print("Please edit settings.json!")
	sys.exit(0)

with open("settings.json") as f:
	settings = json.load(f)
	if ("REPLACE_ME" in [
		settings["plex_token"],
		settings["handy_key"],
		settings["plex_ip"],
	]):
		print("Please edit settings.json!")
		sys.exit(1) #Its an error this time

app.secret_key = settings["app_secret"]

#Very real database, dont question it
database = {}

def test():
	#Test plex connection
	data_url = "http://{}?X-Plex-Token={}".format(settings["plex_ip"],settings["plex_token"])
	with requests.get(data_url) as r:
		if (r.status_code != 200):
			raise Exception("HTTP Error when connecting to plex server {}".format(r.status_code))

	#TODO: Text handyfeeling connection
	#TODO: Test handy_key (not here, as media.play event)
	#TODO: Better errors

test()

#Return video file path
def plex_getvideofile(video_key):
	data_url = "http://{}{}?X-Plex-Token={}".format(settings["plex_ip"], video_key, settings["plex_token"])
	with requests.get(data_url) as r: #BUG: KeyError on non-video
		print("Plex video data", r.text)
		with minidom.parseString(r.text) as xmldoc:
			part = xmldoc.getElementsByTagName("Part")
			if (len(part) > 0):
				return part[0].attributes["file"].value
	
	return None

#Return viewOffset in ms
def plex_gettime(player_uuid):
	data_url = "http://{}/status/sessions?X-Plex-Token={}".format(settings["plex_ip"], settings["plex_token"])
	with requests.get(data_url) as r:
		#print("Plex session data", r.text)
		with minidom.parseString(r.text) as xmldoc:
			part = xmldoc.getElementsByTagName("Video")
			for i in part:
				playerelm = i.getElementsByTagName("Player")[0]
				if (playerelm.attributes["machineIdentifier"].value) == player_uuid:
					viewOffset = int(i.attributes["viewOffset"].value)
					return viewOffset

	return None

#Return if the player is on the same network as the server (that we assume the script is running on aswell)
def plex_islocal(player_uuid):
	data_url = "http://{}/status/sessions?X-Plex-Token={}".format(settings["plex_ip"], settings["plex_token"])
	with requests.get(data_url) as r:
		print("Plex session data", r.text)
		with minidom.parseString(r.text) as xmldoc:
			part = xmldoc.getElementsByTagName("Video")
			for i in part:
				playerelm = i.getElementsByTagName("Player")[0]
				if (playerelm.attributes["machineIdentifier"].value) == player_uuid:
					return playerelm.attributes["local"].value == "1"

	return False

scripts = {} #memory leak yeah
@app.route("/script/<name>", methods=["GET"])
def script_dir(name):
	return send_file(scripts[name])

@app.route("/", methods=["POST"])
def index():
	parsed = json.loads(request.form["payload"]) 
	player_uuid = parsed["Player"]["uuid"]

	print("Plex json data", json.dumps(parsed, indent='\t'))
	print("Plex event type", parsed["event"])

	#New video event
	if (parsed["event"] in ["media.resume", "media.play"]):
		if not player_uuid in database:
			print("Media playback event fired")
			video_file = plex_getvideofile(parsed["Metadata"]["key"])
			if (video_file):
				print("Found video file", video_file)
				#TODO: csv support
				script_path = video_file[:video_file.rfind(".")] + ".funscript"
				if (os.path.exists(script_path)):
					print("Has funscript")
					database[player_uuid] = TheHandy()
					#TODO: What if this fails
					#TODO: Keep instances as to avoid recalculating delay
					print("onReady", database[player_uuid].onReady(settings["handy_key"]))

					scriptUrl = None
					if (settings["access_ip"] != "REPLACE_ME" and plex_islocal(player_uuid)):
						print("isLocal", True)
						script_path, name = database[player_uuid].path_to_name(script_path)
						scriptUrl = "http://{}/script/{}".format(settings["access_ip"],name)
						scripts[name] = script_path
					else:
						print("isLocal", False)
						script_path, scriptUrl = database[player_uuid].upload_funscript(script_path)
					print("scriptUrl", scriptUrl)

					print("setScript", database[player_uuid].setScript(scriptUrl))
					if (settings["view_offset"] != 0):
						print("setOffset", database[player_uuid].setOffset(settings["view_offset"]))

		viewOffset = plex_gettime(player_uuid)
		print("onPlay", database[player_uuid].onPlay(viewOffset))

	if player_uuid in database:
		if (parsed["event"] in ["media.pause", "media.stop"]):
			print("onPause", database[player_uuid].onPause())
		if (parsed["event"] in ["media.stop"]):
			del database[player_uuid]
			#TODO: Delete script path from scripts

	return "OK"

if __name__ == "__main__":
	app.run(host="0.0.0.0",port=8008)
