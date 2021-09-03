import requests, json, sys, html, time, os, re

class TheHandy:
	def __init__(self):
		self.timeSyncMessage = 0
		self.timeSyncAggregatedOffset = 0
		self.timeSyncAverageOffset = 0
		self.timeSyncInitialOffset = 0
		self.URL_BASE = "https://www.handyfeeling.com/"
		self.URL_API_ENDPOINT = "api/v1/"


	def onReady(self, connectionKey, scriptUrl):
		"""
		Sends the script to the handy
		Takes handy key and script url
		"""
		self.urlAPI = self.URL_BASE + self.URL_API_ENDPOINT + connectionKey
		self.updateServerTime()

		with requests.get(self.urlAPI + "/syncPrepare", params={
			"url": scriptUrl,
			"timeout": 30000
		}) as r:
			return json.loads(r.text)

	def onPlay(self, videoTime):
		"""
		Sends a play signal to the handy
		Takes video time in milliseconds
		"""

		with requests.get(self.urlAPI + "/syncPlay", params={
			"play": "true",
			"serverTime": self.getServerTime(),
			"time": videoTime
		}) as r:
			return json.loads(r.text)

	def onPause(self):
		"""
		Sends a pause signal to the handy
		"""
	
		with requests.get(self.urlAPI + "/syncPlay", params={
			"play": "false"
		}) as r:
			return json.loads(r.text)

	def setOffset(self, ms):
		"""
		Sends a set offset signal to the handy
		Takes the offset in milliseconds
		"""

		with requests.get(self.urlAPI + "/syncOffset", params={
			"offset": ms,
			"timeout": 30000
		}) as r:
			return json.loads(r.text)

	def sysTime(self):
		"""
		Returns the current time in milliseconds
		"""
		return int(time.time() * 1000)

	def getServerTime(self):
		serverTimeNow = self.sysTime() + self.timeSyncAverageOffset + self.timeSyncInitialOffset
		return round(serverTimeNow)

	def updateServerTime(self):
		sendTime = self.sysTime()
		url = self.urlAPI  + "/getServerTime"

		with requests.get(url) as r:
			result = json.loads(r.text)

			now = self.sysTime()
			receiveTime = now
			rtd = receiveTime - sendTime
			serverTime = result["serverTime"]
			estimatedServerTimeNow = serverTime + rtd /2
			offset = 0
			if(self.timeSyncMessage == 0):
				self.timeSyncInitialOffset = estimatedServerTimeNow - now
				print("timeSyncInitialOffset: {}".format(self.timeSyncInitialOffset))
			else:
				offset = estimatedServerTimeNow - receiveTime - self.timeSyncInitialOffset
				self.timeSyncAggregatedOffset += offset
				self.timeSyncAverageOffset = self.timeSyncAggregatedOffset / self.timeSyncMessage

			print("Time sync reply nr {} (rtd, this offset, average offset): {}, {}, {}".format(self.timeSyncMessage, rtd, offset, self.timeSyncAverageOffset))

			self.timeSyncMessage = self.timeSyncMessage + 1
			if(self.timeSyncMessage < 30):
				self.updateServerTime()

def upload_funscript(input_file):
	#Handyfeeling rejects files over 2MB
	#So we convert to csv per default avoid that
	#Since it turns 2355KB into 127KB
	if (input_file.endswith(".funscript")):
		old_input_file = input_file
		input_file = input_file.replace(".funscript", ".csv")
		if (not os.path.exists(input_file)):
			convert_funscript_to_csv(old_input_file, input_file)

	filename = input_file[input_file.rfind("/")+1:]

	#Fix weird naming bug
	filename = "".join(re.findall(r"(\w+|\.|\ )", filename))

	multipart_form_data = {
		"syncFile": (filename, open(input_file, "rb")),
	}

	response = requests.post("https://www.handyfeeling.com/api/sync/upload?local=true", files=multipart_form_data)

	#TODO: 413 Request entity too large
	if (response.status_code != 200):
		print(response.text)
		print(response.status_code)
		return None

	data = json.loads((response.content).decode("utf-8"))

	print(data, file=sys.stderr)

	return html.unescape(data["url"])

def convert_funscript_to_csv(input_file,output_file):
	with open(input_file) as fr:
		jsn = json.load(fr)
		with open(output_file, "w") as fw:
			fw.write("#Converted to CSV using script_converter.py")
			#BUT WHAT ABOUT MUH SETTINGS
			#fuckem
			for i in jsn["actions"]:
				fw.write("{},{}\r\n".format(i["at"],i["pos"]))
