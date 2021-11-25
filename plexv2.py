from handyv2 import TheHandy
from flask import Flask, request, send_file
from xml.dom import minidom
from inspect import currentframe
from plexapi.server import PlexServer
from tempfile import NamedTemporaryFile
import tempfile, time, os, json, shutil, requests, sys, html, re, hashlib, threading

#Classes
class bcolors:
	HEADER = '\033[95m'
	OKBLUE = '\033[94m'
	OKCYAN = '\033[96m'
	OKGREEN = '\033[92m'
	WARNING = '\033[93m'
	FAIL = '\033[91m'
	ENDC = '\033[0m'
	BOLD = '\033[1m'
	UNDERLINE = '\033[4m'


class ScriptHandler:
	"""
	Caches scripts for usage
	"""
	def __init__(self):
		self.db = []
		self.len = 5
	#Keep only 5 latest
	def clean(self):
		self.db = self.db[-(self.len):]
	#Prepare a script for usage
	def addScript(self, file_loc, _id, local=False):
		fx = get_extless(file_loc)

		csv_path = fx + ".csv"
		tmp = NamedTemporaryFile()

		if (not os.path.exists(csv_path)):
			fun_path = fx + ".funscript"
			assert os.path.exists(fun_path)
			self.convert_funscript_to_csv(fun_path, tmp.name)
		else:
			with open(csv_path, "r") as fr:
				with open(tmp.name, "w") as fw:
					fw.write(fr.read())

		csv_path = tmp.name

		http = None
		if (local):
			print("Uploaded to local server")
			http = "http://{}/script/{}".format(settings["access_ip"],_id)
		else:
			print("Uploaded to handyfeeling server")
			http = self.upload_funscript(csv_path)
			#TODO: These run out after some hours, account for that
		print(f"Script url: {http}")

		self.db.append({
			"id": _id,
			"http": http,
			"hash": self.get_digest(csv_path),

			"csv": tmp,
			"local": local
		})

		self.clean()

		return http
	#Return a script (if it exists)
	def getScript(self, _id):
		for i in self.db:
			if i["id"] == _id:
				return i["csv"].name,i["http"]
		return None,None
	#Return if script exists
	def hasScript(self, filepath):
		fx = get_extless(filepath)
		return os.path.exists(fx + ".funscript") or os.path.exists(fx + ".csv")
	#Remove a given script
	def removeScript(self, _id):
		self.db = [i for i in self.db if i["id"] != _id]
	def get_digest(self, file_path):
		"""
		Calculate sha256 hash of given file
		"""
		h = hashlib.sha256()

		with open(file_path, "rb") as file:
			while True:
				# Reading is buffered, so we can read smaller chunks.
				chunk = file.read(h.block_size)
				if not chunk:
					break
				h.update(chunk)

		return h.hexdigest()
	def convert_funscript_to_csv(self,input_file,output_file):
		"""
		Convert a funscript to csv
		"""
		with open(input_file) as fr:
			jsn = json.load(fr)
			with open(output_file, "w") as fw:
				fw.write("#Converted to CSV using script_converter.py")
				#BUT WHAT ABOUT MUH SETTINGS
				#fuckem
				for i in jsn["actions"]:
					fw.write("{},{}\r\n".format(i["at"],i["pos"]))
	def upload_funscript(self, input_file):
		"""
		Upload a script to handyfeelings hosting api and return the url

		Handyfeeling rejects files over 2MB
		So we convert to csv per default avoid that
		Since it turns 2355KB into 127KB
		"""
		filename = "".join(re.findall(r"(\w+|\.)", input_file[input_file.rfind("/")+1:])) #|\ 

		multipart_form_data = {
			"syncFile": (filename, open(input_file, "rb")),
		}

		response = requests.post("https://www.handyfeeling.com/api/sync/upload?local=true", files=multipart_form_data)

		#TODO: 413 Request entity too large
		if (not response.status_code in range(200,299)):
			print(f"{bcolors.WARNING}{response.text}\n{response.status_code}{bcolors.ENDC}", file=sys.stderr)
			return None

		data = json.loads((response.content).decode("utf-8"))

		print(f"{bcolors.OKCYAN}handyfeeling {data}{bcolors.ENDC}", file=sys.stderr)

		return html.unescape(data["url"])

class HandyDB:
	"""
	Caches theHandy for usage
	"""
	def __init__(self):
		self.db = {}
	#Add a handy instance
	def addInstance(self, _id):
		self.clean()

		hnd = TheHandy()
		hnd.onReady(settings["handy_key"])

		self.db[_id] = {
			"time": time.time(),
			"handy": hnd,
			"video": None
		}

		return hnd
	#Yeah this sucks, get a small wrapper class, or anything else, please
	def getHandy(self, _id):
		self.db[_id]["time"] = time.time()

		return self.db[_id]["handy"]
	def getVideo(self, _id):
		self.db[_id]["time"] = time.time()

		return self.db[_id]["video"]
	def setVideo(self, _id, data):
		self.db[_id]["time"] = time.time()

		self.db[_id]["video"] = data
	def hasInstance(self, _id):
		self.clean()
		return len([i for i in self.db if i == _id]) > 0
	def clean(self):
		for _id in self.db:
			if ((time.time() - self.db[_id]["time"]) / 60 / 60 > settings["timeout"]):
				del self.db[_id]

#Support functions
def get_extless(filename):
	dot = filename.rfind(".")
	if (dot == -1):
		return filename
	else:
		return filename[:dot]

#Return video file path
def plex_getvideofile(video_key):
	data_url = "http://{}{}?X-Plex-Token={}".format(settings["plex_ip"], video_key, settings["plex_token"])
	with requests.get(data_url) as r: #BUG: KeyError on non-video
		with minidom.parseString(r.text) as xmldoc:
			print(f"{bcolors.OKCYAN}Plex video data {xmldoc.toprettyxml()}{bcolors.ENDC}")
			part = xmldoc.getElementsByTagName("Part")
			if (len(part) > 0):
				return part[0].attributes["file"].value
	
	return None

#Return viewOffset in ms
def plex_gettime_old(player_uuid):
	data_url = "http://{}/status/sessions?X-Plex-Token={}".format(settings["plex_ip"], settings["plex_token"])
	with requests.get(data_url) as r:
		with minidom.parseString(r.text) as xmldoc:
			print(f"{bcolors.OKCYAN}Plex session data {xmldoc.toprettyxml()}{bcolors.ENDC}")
			for i in xmldoc.getElementsByTagName("Video"):
				for playerelm in i.getElementsByTagName("Player"):

					if playerelm.attributes["machineIdentifier"].value == player_uuid:
						#if (playerelm.attributes["product"].value != "DLNA"):
						return int(i.attributes["viewOffset"].value)

	return None

#Return if the player is on the same network as the server (that we assume the script is running on aswell)
def plex_islocal(player_uuid):
	for session in plex.sessions():
		for player in session.players:
			if (player.machineIdentifier == player_uuid):
				if player.product == "DLNA":
					return "DLNA"
				return player.local

	return None

app = Flask(__name__)

#Default settings
settings = {
	"app_secret": "REPLACE_ME",
	"plex_token": "REPLACE_ME",
	"handy_key": "REPLACE_ME",
	"plex_ip": "127.0.0.1:32400",
	"access_ip": "REPLACE_ME",
	"view_offset": 50,
	"timeout": 2,
	"pause_sync": True
}

#If there are no default settings
if not os.path.exists("settings.json"):
	with open("settings.json", "w") as f:
		json.dump(settings, f, indent="\t")
	print(f"{bcolors.WARNING}Please edit settings.json!{bcolors.ENDC}")
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
		print(f"{bcolors.WARNING}Please edit settings.json!{bcolors.ENDC}")
		sys.exit(1) #Its an error this time

	#Update settings (if any new ones are present)
	f.seek(0)
	json.dump(settings, f, indent="\t")
	f.truncate()

app.secret_key = settings["app_secret"]

#Nice api
plex = PlexServer("http://" + settings["plex_ip"],settings["plex_token"])
script_db = ScriptHandler()
handy_db = HandyDB()

@app.route("/script/<name>", methods=["GET"])
def script_dir(name):
	"""
	Returns local scripts stored for local usage
	"""
	script_path, script_http = script_db.getScript(name)
	assert os.path.exists(script_path)
	return send_file(script_path)

class PlexDelay:
	def __init__(self):
		self.isRunning = False
		self.calculated = False
		self.command_delay = 0
		self.report_delay = 0
		self.catched = False
	def shouldCatch(self):
		return self.isRunning
	def hasCalculated(self):
		return self.calculated
	def _auxRun(self, player_uuid):
		client = [i for i in plex.clients() if i.machineIdentifier == player_uuid][0]

		#Get command/device delay
		times = []
		for i in range(30):
			when = time.time()
			if (i % 2 == 0):
				client.pause()
			else:
				client.play()

			rtt = (time.time() - when) / 2
			print(f"Command sync: (num, rtt): {i} {rtt*1000}")
			times.append(rtt)
		self.command_delay = sum(times) / len(times)
		time.sleep(5) #Allow plenty of delay for plex
		self.catched = False

		#Dont allow less than zero (usually indicates a early fire from previous command)
		print(f"Command delay: {self.command_delay*1000}")
		self.command_delay = max(self.command_delay, 0)

		#Get report delay (inconsistent)
		times = []
		for i in range(30):
			when = time.time()
			if (i % 2 == 0):
				client.pause()
			else:
				client.play()
			while (not self.catched): #Busy wait
				pass
			self.catched = False
			rtt = (time.time() - when) - self.command_delay
			print(f"Report sync: (num, rtt): {i} {rtt*1000}")
			times.append(rtt)
			time.sleep(0.1)
		self.report_delay = sum(times) / len(times)
		self.catched = False

		print(f"Report delay: {self.report_delay*1000}")
		self.report_delay = max(self.report_delay, 0)

		print(f"Command delay: {self.command_delay*1000}ms\nReport delay: {self.report_delay*1000}ms")
		self.calculated=True
	def totalDelay(self):
		if (not settings["pause_sync"]):
			return settings["view_offset"]

		return (self.report_delay + self.command_delay) * 1000
	def run(self, player_uuid):
		if (not settings["pause_sync"] or self.calculated):
			return
		self.isRunning = True
		self._auxRun(player_uuid)
		self.isRunning = False
	def catch(self, event_type):
		if (event_type in ["media.resume", "media.play", "media.pause"]):
			self.catched=True

delay_c = PlexDelay()

@app.route("/", methods=["POST"])
def index():
	global delay_c
	"""
	Receives a Plex event and handles accordingly
	"""
	#Video data
	parsed = json.loads(request.form["payload"])
	#Player device unique id
	player_uuid = parsed["Player"]["uuid"]
	#Video unique id
	video_uuid = parsed["Metadata"]["ratingKey"]
	#Video url
	video_url = parsed["Metadata"]["key"]
	#Event type
	event_type = parsed["event"]

	if (delay_c.shouldCatch()):
		delay_c.catch(event_type)
		return "OK"

	#Plex data
	json_data = json.dumps(parsed, indent='\t')
	print(f"{bcolors.OKCYAN}Plex json data {json_data}{bcolors.ENDC}")
	print(f"{bcolors.OKCYAN}Plex event type {event_type}{bcolors.ENDC}")

	#Any play event
	if (event_type in ["media.resume", "media.play"]):
		#Video file exists
		video_file = plex_getvideofile(video_url)
		if (video_file != None):
			print("Video File: ", video_file)

			#Script exists
			script_path, script_http = script_db.getScript(video_uuid)
			if (script_http == None):
				#If we run over DLNA, we have a hard time knowing the viewOffset
				#So we ignore DLNA clients
				isLocal = plex_islocal(player_uuid)
				if (isLocal == "DLNA"):
					print("Ignoring DLNA...")
					return "OK"

				#Uploaded the given script
				script_http = script_db.addScript(video_file, video_uuid, local=isLocal)

			#Script exists
			if (script_http != None):
				print("Script HTTP: ", script_http)

				#If we dont have an instance of theHandy or the instance got broken
				if (not handy_db.hasInstance(player_uuid) or not handy_db.getHandy(player_uuid).isReady()):
					#Create new instance
					handy_db.addInstance(player_uuid)
					delay_c.calculated = False
					delay_c.run(player_uuid)
					#Set offset
					print("setOffset", handy_db.getHandy(player_uuid).setOffset(delay_c.totalDelay()))

				#If its a different video than last time, initialize
				if (handy_db.getVideo(player_uuid) != video_uuid):
					#Send the script to theHandy
					print("setScript", handy_db.getHandy(player_uuid).setScript(script_http))
					#Set current video playing in our db
					handy_db.setVideo(player_uuid, video_uuid)

		#If handy exists
		if handy_db.hasInstance(player_uuid):
			#And has same video (we didnt switch from scripted to non-scripted)
			if (handy_db.getVideo(player_uuid) == video_uuid):
				#Get viewOffset and play from there
				viewOffset = plex_gettime_old(player_uuid)
				print("onPlay", handy_db.getHandy(player_uuid).onPlay(viewOffset))

	#If handy exists
	if handy_db.hasInstance(player_uuid):
		#If video is paused
		if (event_type in ["media.pause", "media.stop"]):
			print("onPause", handy_db.getHandy(player_uuid).onPause())
		#If video is stopped
		if (event_type in ["media.stop"]):
			script_db.removeScript(video_uuid)

	return "OK"

if __name__ == "__main__":
	app.run(host="0.0.0.0",port=8008)
