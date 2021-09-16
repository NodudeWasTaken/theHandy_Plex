import requests, json, time, hashlib
import sys, html, os, re

class TheHandy:
	def __init__(self):
		self.numSync = 0
		self.URL_BASE = "https://www.handyfeeling.com/" #TODO: Use staging instead of www when its fixed
		self.URL_API_ENDPOINT = "api/handy/v2"

	def quickCheck(self, r):
		assert r.status_code in range(200,299)
		rtn = json.loads(r.text)
		assert rtn["result"] != -1 if "result" in rtn else True
		return rtn

	#Set theHandy operation mode to video sync
	def onReady(self, connectionKey):
		"""
		Sends the script to the handy
		Takes handy key and script url
		"""
		self.urlAPI = self.URL_BASE + self.URL_API_ENDPOINT
		self.connectionHeader = {
			'accept': 'application/json',
			'X-Connection-Key': connectionKey,
			'Content-Type': 'application/json',
		}

		data = json.dumps({ 
			"mode": 1 
		}) #HAMP 0, HSSP 1, HDSP 2, MAINTENANCE 3

		with requests.put(self.urlAPI + "/mode", data=data, headers=self.connectionHeader) as r:
			rtn = self.quickCheck(r)
			print("Mode request: {}".format(rtn))

		self.deviceSync()
		self.updateServerTime()

	def setScript(self, scriptUrl, scriptHash=None):
		"""
		Upload a script to theHandy
		"""
		#scriptHash = hashlib.sha256(open(scriptPath).read().encode("utf-8")).hexdigest()

		data = {
			"url": scriptUrl,
		}
		if (scriptHash != None):
			data["sha256"] = scriptHash
		
		data = json.dumps(data)

		with requests.put(self.urlAPI + "/hssp/setup", data=data, headers=self.connectionHeader) as r:
			rtn = self.quickCheck(r)
			return rtn

	def onPlay(self, videoTime):
		"""
		Sends a play signal to the handy
		Takes video time in milliseconds
		"""

		data = json.dumps({
			"tserver": self.getServerTime(), #tserver
			"tstream": videoTime #tstream
		})
		#print(data)

		with requests.put(self.urlAPI + "/hssp/play", data=data, headers=self.connectionHeader) as r:
			rtn = self.quickCheck(r)
			return rtn

	def onPause(self):
		"""
		Sends a pause signal to the handy
		"""

		with requests.put(self.urlAPI + "/hssp/stop", headers=self.connectionHeader) as r:
			rtn = self.quickCheck(r)
			self.updateServerTime(num=1) #Might aswell update every once in a while
			return rtn

	def setOffset(self, ms):
		"""
		Sends a set offset signal to the handy
		Takes the offset in milliseconds
		"""

		data = json.dumps({
			"offset": ms
		})

		with requests.put(self.urlAPI + "/hssp/offset", data=data, headers=self.connectionHeader) as r:
			rtn = self.quickCheck(r)
			return rtn

	def sysTime(self):
		"""
		Returns the current time in milliseconds
		"""
		return time.time() * 1000

	def deviceSync(self):
		"""
		Supposedly finds the delay from theHandy to SweetTech's api
		"""
		headers = {"syncCount": "6"}
		for i in self.connectionHeader:
			headers[i] = self.connectionHeader[i]

		with requests.get(self.urlAPI + "/hssp/sync", 
			headers=headers
		) as r:
			rtn = self.quickCheck(r)
			print("dtserver time: {}".format(rtn["dtserver"]))
			return rtn

	def getServerTime(self):
		"""
		Return the predicted server time
		"""
		serverTimeNow = self.sysTime() + self.serverAvgOffset
		return int(serverTimeNow)

	def updateServerTime(self, num=30):
		"""
		Calculate the server time difference offset
		"""
		url = self.urlAPI + "/servertime"

		for i in range(0,num):
			self.numSync = self.numSync + i
			Tsend = self.sysTime()
			with requests.get(url) as r:
				Treceive = self.sysTime()
				RTD = Treceive - Tsend

				Ts = self.quickCheck(r)["serverTime"]
				Ts_est = Ts + (RTD / 2)

				offset = Ts_est - Treceive
				if (self.numSync == 0):
					print("initial sync offset: {}".format(offset))
					self.serverAvgOffset = offset
				else:
					#Iteratively calculate sum(offset)/len(offset)
					self.serverAvgOffset = self.serverAvgOffset + ((offset - self.serverAvgOffset) / self.numSync)

				print("Time sync reply (num, rtd, this offset): {}, {}, {}".format(i, RTD, offset))

		print("serverAvgOffset", self.serverAvgOffset)

	def path_to_name(self, input_file):
		"""
		Get the name of a script, and convert it to .csv if applicable
		"""
		if (input_file.endswith(".funscript")):
			old_input_file = input_file
			input_file = input_file.replace(".funscript", ".csv")
			if (not os.path.exists(input_file)):
				self.convert_funscript_to_csv(old_input_file, input_file)

		filename = input_file[input_file.rfind("/")+1:]

		#Fix weird naming bug
		filename = "".join(re.findall(r"(\w+|\.)", filename)) #|\ 

		return input_file, filename

	def upload_funscript(self, input_file):
		"""
		Upload a script to handyfeelings hosting api and return the url

		Handyfeeling rejects files over 2MB
		So we convert to csv per default avoid that
		Since it turns 2355KB into 127KB
		"""
		input_file, filename = self.path_to_name(input_file)

		multipart_form_data = {
			"syncFile": (filename, open(input_file, "rb")),
		}

		response = requests.post("https://www.handyfeeling.com/api/sync/upload?local=true", files=multipart_form_data)

		#TODO: 413 Request entity too large
		if (not response.status_code in range(200,299)):
			print(response.text)
			print(response.status_code)
			return None

		data = json.loads((response.content).decode("utf-8"))

		print("handyfeeling", data, file=sys.stderr)

		return input_file, html.unescape(data["url"])

	def convert_funscript_to_csv(self, input_file,output_file):
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
