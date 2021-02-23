from flask import Flask, request
from xml.dom import minidom
from handy import TheHandy, upload_funscript
import json, time, requests, os

app = Flask(__name__)
#Set this to anything else
app.secret_key = "much_secret_such_wow"

#Your plex token
plex_token = "YOUR_PLEX_TOKEN"
#Your handy key
handy_key = "YOUR_HANDY_KEY"
server_ip = "127.0.0.1" #If custom ip

#Very real database, dont question it
database = {}

@app.route("/", methods=["POST"])
def index():
	parsed = json.loads(request.form["payload"]) 
	unique_id = "{}_{}".format(parsed["Player"]["uuid"], parsed["Metadata"]["ratingKey"]) #TODO: Use userid instead

	print(json.dumps(parsed, indent='\t'))
	print(parsed["event"])

	#New video event
	if (parsed["event"] == "media.play"):
		print("Media playback event fired")
		video_file = None
		data_url = "http://{}:32400{}?X-Plex-Token={}".format(server_ip,parsed["Metadata"]["key"], plex_token)
		with requests.get(data_url) as r:
			with minidom.parseString(r.text) as xmldoc:
				part = xmldoc.getElementsByTagName("Part")
				if (len(part) > 0):
					print(r.text)
					video_file = part[0].attributes["file"].value

		if (video_file):
			print("Found video file {}".format(video_file))
			script_path = video_file[:video_file.rfind(".")] + ".funscript"
			if (os.path.exists(script_path)):
				print("Has funscript")
				database[unique_id] = TheHandy()
				script_url = upload_funscript(script_path)
				#TODO: What if this fails
				print(database[unique_id].onReady(handy_key, script_url))

	if unique_id in database:
		if (parsed["event"] == "media.pause" or parsed["event"] == "media.stop"):
			print(database[unique_id].onPause())
		if (parsed["event"] == "media.resume" or parsed["event"] == "media.play"):
			data_url = "http://{}:32400/status/sessions?X-Plex-Token={}".format(server_ip, plex_token)
			with requests.get(data_url) as r:
				with minidom.parseString(r.text) as xmldoc:
					part = xmldoc.getElementsByTagName("Video")
					for i in part:
						if (i.getElementsByTagName("Player")[0].attributes["machineIdentifier"].value) == parsed["Player"]["uuid"]:
							viewOffset = int(i.attributes["viewOffset"].value)
							print(viewOffset)
							print(database[unique_id].onPlay(viewOffset))
		if (parsed["event"] == "media.stop"):
			del database[unique_id]

	return "OK"

if __name__ == "__main__":
	app.run(host="0.0.0.0",port=8008)
