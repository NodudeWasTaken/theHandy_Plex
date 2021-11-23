import requests, json, time, hashlib
import sys, html, os, re, collections

class TheHandy:
	"""
	Updated for OAS3
	"""
	def __init__(self):
		self.numSync = 0
		self.URL_BASE = "https://www.handyfeeling.com/" #TODO: Use staging instead of www when its fixed
		self.URL_API_ENDPOINT = "api/handy/v2"
		self.offsetQueue = collections.deque(maxlen=30)

	def quickCheck(self, r):
		print(r.text)
		assert r.status_code in range(200,299)
		rtn = json.loads(r.text)
		assert rtn["result"] != -1 if "result" in rtn else True
		assert not "error" in rtn
		return rtn

	def isReady(self):
		"""
		Get current mode
		"""
		with requests.get(self.urlAPI + "/hssp/state", headers=self.connectionHeader) as r:
			rtn = self.quickCheck(r)
			return rtn["state"] != 2

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

		self.updateServerTime()

	def setScript(self, scriptUrl, scriptHash=None):
		"""
		Upload a script to theHandy
		"""

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
			"estimatedServerTime": self.getServerTime(), #tserver, estimatedServerTime
			"startTime": videoTime #tstream, startTime
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
			#self.updateServerTime(num=1) #Might aswell update every once in a while
			return rtn

	def setOffset(self, ms):
		"""
		Sends a set offset signal to the handy
		Takes the offset in milliseconds
		"""

		data = json.dumps({
			"offset": int(ms)
		})

		with requests.put(self.urlAPI + "/hstp/offset", data=data, headers=self.connectionHeader) as r:
			rtn = self.quickCheck(r)
			return rtn

	def sysTime(self):
		"""
		Returns the current time in milliseconds
		"""
		return time.time() * 1000

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
			Tsend = self.sysTime()
			with requests.get(url) as r:
				Treceive = self.sysTime()

				#Round trip-time
				RTT = Treceive - Tsend

				#Get servertime
				Ts = self.quickCheck(r)["serverTime"]

				#Given serverTime plus predicted server time
				Ts_est = Ts + (RTT / 2)

				#Difference between local time and server time
				offset = Ts_est - Treceive

				self.offsetQueue.append(offset)
				print("Time sync reply (num, rtt, this offset): {}, {}, {}".format(i, RTT, offset))

		self.numSync += num
		self.serverAvgOffset = sum(self.offsetQueue) / len(self.offsetQueue)
		print("Handy server delay: {self.serverAvgOffset}")
