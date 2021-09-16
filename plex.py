from flask import Flask, request, send_file
from xml.dom import minidom
from inspect import currentframe
from handyv2 import TheHandy
import json, time, requests, os, sys

app = Flask(__name__)

#Default settings
settings = {
	"app_secret": "REPLACE_ME",
	"plex_token": "REPLACE_ME",
	"handy_key": "REPLACE_ME",
	"plex_ip": "127.0.0.1:32400",
	"access_ip": "REPLACE_ME",
	"view_offset": 0,
	"dlna_offset": 0,
}

#If there are no default settings
if not os.path.exists("settings.json"):
	with open("settings.json", "w") as f:
		json.dump(settings, f, indent="\t")
	print("Please edit settings.json!")
	sys.exit(0)

#Load user settings
with open("settings.json", "r+") as f:
	#Append settings with user specified settings
	settings.update(json.load(f))

	#Detect invalid values
	if ("REPLACE_ME" in [
		settings["plex_token"],
		settings["handy_key"],
		settings["plex_ip"],
	]):
		print("Please edit settings.json!")
		sys.exit(1) #Its an error this time

	#Update settings (if any new ones are present)
	f.seek(0)
	json.dump(settings, f, indent="\t")
	f.truncate()


app.secret_key = settings["app_secret"]

#Very real database, dont question it
#We could easily support multiple handy users, but i don't see why i would do that
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

#Get current line number
def get_linenumber():
	cf = currentframe()
	return cf.f_back.f_lineno

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
			for i in xmldoc.getElementsByTagName("Video"):
				for playerelm in i.getElementsByTagName("Player"):

					if playerelm.attributes["machineIdentifier"].value == player_uuid:
						if (playerelm.attributes["product"].value != "DLNA"):
							return int(i.attributes["viewOffset"].value)
						else:
							return int(i.attributes["viewOffset"].value + settings["dlna_offset"])

	return None

#Return if the player is on the same network as the server (that we assume the script is running on aswell)
def plex_islocal(player_uuid):
	data_url = "http://{}/status/sessions?X-Plex-Token={}".format(settings["plex_ip"], settings["plex_token"])
	with requests.get(data_url) as r:
		print("Plex session data", r.text)
		with minidom.parseString(r.text) as xmldoc:
			for i in xmldoc.getElementsByTagName("Video"):
				for playerelm in i.getElementsByTagName("Player"):

					if (playerelm.attributes["machineIdentifier"].value) == player_uuid:
						return playerelm.attributes["local"].value == "1" or playerelm.attributes["product"].value == "DLNA"

	return False

scripts = {}
@app.route("/script/<name>", methods=["GET"])
def script_dir(name):
	return send_file(scripts[name])

def hasFunscript(video_file):
	ext_less = video_file[:video_file.rfind(".")]

	script_path = ext_less + ".funscript"
	if (os.path.exists(script_path)):
		return script_path

	script_path = ext_less + ".csv"
	if (os.path.exists(script_path)):
		return script_path

	return None
	


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
				print("video_file: {}".format(video_file))
				script_path = hasFunscript(video_file)
				if (script_path != None):
					print("funscript: {}".format(script_path))
					database[player_uuid] = TheHandy()
					#TODO: What if this fails
					#TODO: Keep instances as to avoid recalculating delay
					print("onReady", database[player_uuid].onReady(settings["handy_key"]))

					scriptUrl = None
					if (settings["access_ip"] != "REPLACE_ME" and plex_islocal(player_uuid)):
						print("isLocal", True)
						script_path, name = database[player_uuid].path_to_name(script_path)
						scripts[player_uuid] = script_path
						scriptUrl = "http://{}/script/{}".format(settings["access_ip"],player_uuid)
					else:
						print("isLocal", False)
						script_path, scriptUrl = database[player_uuid].upload_funscript(script_path)
					print("scriptUrl", scriptUrl)

					print("setScript", database[player_uuid].setScript(scriptUrl))
					print("setOffset", database[player_uuid].setOffset(settings["view_offset"]))
				else:
					print("funscript: not found")
			else:
				print("video_file: not found")

		if player_uuid in database:
			viewOffset = plex_gettime(player_uuid)
			print("onPlay", database[player_uuid].onPlay(viewOffset))

	if player_uuid in database:
		if (parsed["event"] in ["media.pause", "media.stop"]):
			print("onPause", database[player_uuid].onPause())
		if (parsed["event"] in ["media.stop"]):
			del database[player_uuid]
			del scripts[player_uuid]

	return "OK"

if __name__ == "__main__":
	app.run(host="0.0.0.0",port=8008)
