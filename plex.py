from flask import Flask, request
from xml.dom import minidom
from handy import TheHandy, upload_funscript
import json, time, requests, os

app = Flask(__name__)
#Set this to anything else
app.secret_key = "very_secret_key_goes_here"

#Your plex token
plex_token = "plex_token_goes_here"
#Your handy key
handy_key = "handy_key_goes_here"

#Very real database, dont question it
database = {}

@app.route("/", methods=["POST"])
def index():
	start = time.time()*1000

	parsed = json.loads(request.form["payload"])
	#View offset in milliseconds
	#BUG: Only works after 1 minute
	unique_id = "{}_{}".format(parsed["Player"]["uuid"], parsed["Metadata"]["ratingKey"])
	viewOffset = int(parsed["Metadata"]["viewOffset"] if "viewOffset" in parsed["Metadata"] else 0)

	print(json.dumps(parsed, indent='\t'))
	print(parsed["event"])

	#New video event
	if (parsed["event"] == "media.play"):
		video_file = None
		data_url = "http://127.0.0.1:32400{}?X-Plex-Token={}".format(parsed["Metadata"]["key"], plex_token)
		with requests.get(data_url) as r:
			with minidom.parseString(r.text) as xmldoc:
				part = xmldoc.getElementsByTagName("Part")
				if (len(part) > 0):
					video_file = part[0].attributes["file"].value

		if (video_file):
			print(video_file)
			script_path = video_file[:video_file.rfind(".")] + ".funscript"
			if (os.path.exists(script_path)):
				print("Has funscript")
				database[unique_id] = TheHandy()
				script_url = upload_funscript(script_path)
				print(database[unique_id].onReady(handy_key, script_url))

	if unique_id in database:
		if (parsed["event"] == "media.pause" or parsed["event"] == "media.stop"):
			print(database[unique_id].onPause())
		if (parsed["event"] == "media.resume" or parsed["event"] == "media.play"):
			viewOffset = viewOffset + int(time.time()*1000 - start)
			print(viewOffset)
			print(database[unique_id].onPlay(viewOffset))
		if (parsed["event"] == "media.stop"):
			del database[unique_id]

	return "OK"

if __name__ == "__main__":
	app.run(port=8008)
