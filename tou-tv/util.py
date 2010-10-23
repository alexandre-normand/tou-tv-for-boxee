import mc
import re
import time
import threading

TOU_TV_MEDIA_FLAG = 'toutv.mediaData'
TOU_TV_BASE_URL = 'http://www.tou.tv'
DATA_VERSION = 2
DATA_EXPIRATION = 60 * 60 * 24
KEY_DATA_VERSION = "dataVersion"
KEY_LAST_SHOW_LIST_UPDATE = "showsLastUpdated"
KEY_SHOWS = "shows"
KEY_SUFFIX_SHOW_PATH = ".path"
KEY_SUFFIX_EPISODE_LIST = ".episodes"
KEY_SUFFIX_LAST_UPDATED = ".lastUpdated"
KEY_SUFFIX_SHOW_BACKGROUND = ".backgroundUrl"
KEY_SUFFIX_EPISODE_TITLE = ".title"
KEY_SUFFIX_EPISODE_THUMBNAIL = ".thumbnail"
KEY_SUFFIX_EPISODE_DESCRIPTION = ".description"
KEY_SUFFIX_EPISODE_VIDEO_URL = ".videoUrl"
KEY_SUFFIX_EPISODE_SEASON = ".season"
KEY_SUFFIX_EPISODE_NUMBER = ".number"
SEPARATOR = "<itemseparator>"

locks = dict()
MASTER_LOCK = threading.RLock()

def initCache():
	appConfig = mc.GetApp().GetLocalConfig()
	# TODO : remove this once testing has proven it works
	appConfig.ResetAll()
	
	currentDataVersion = appConfig.GetValue(KEY_DATA_VERSION)
	lastUpdate = appConfig.GetValue(KEY_LAST_SHOW_LIST_UPDATE)
	
	log = "Current config is: DataVersion(" + currentDataVersion + "), lastUpdate(" + lastUpdate + "), Shows(" + appConfig.Implode(SEPARATOR, KEY_SHOWS) + ")"
	print log
	
	if currentDataVersion != "":
		if DATA_VERSION > int(currentDataVersion):
			log = "Resetting all config because new data version is " + str(DATA_VERSION) + " and old data version was " + currentDataVersion
			print log
			appConfig.ResetAll()
			appConfig.SetValue(KEY_DATA_VERSION, str(DATA_VERSION))
	else:
		appConfig.SetValue(KEY_DATA_VERSION, str(DATA_VERSION))
	
	lastUpdate = appConfig.GetValue(KEY_LAST_SHOW_LIST_UPDATE)
	
	if lastUpdate == "":
		updateShowListCache()
	else:
		expirationTime = float(lastUpdate) + DATA_EXPIRATION
		
		log = "Calculated expiration time is: " + str(expirationTime) + ", currentTime is: " + str(time.time())
		print log
		
		if time.time() > expirationTime:
			updateShowListCache()
		else:
			log = "List of shows still valid, last updated: " + lastUpdate
			print log
		
	log = "dataversion: " + str(DATA_VERSION)
	print log
	
	return 0

def updateShowListCache():
	appConfig = mc.GetApp().GetLocalConfig()
	shows = fetchShows()
	log = "Acquiring master lock..."
	print log
	MASTER_LOCK.acquire()
	try:
		appConfig.Reset(KEY_SHOWS)
		
		for show in shows:
			appConfig.PushBackValue(KEY_SHOWS, show.name)
			showPathKey = show.name + KEY_SUFFIX_SHOW_PATH
			appConfig.SetValue(showPathKey, show.path)
			locks[show.name] = threading.RLock()
		
		lastUpdateTime = time.time()
		appConfig.SetValue(KEY_LAST_SHOW_LIST_UPDATE, str(lastUpdateTime))
		
		log = "Updated list of shows and last update time set to:" + str(lastUpdateTime)
		print log
	finally:
		log = "Releasing master lock"
		print log
		MASTER_LOCK.release()
	return 1

def getShowsFromCache():
	appConfig = mc.GetApp().GetLocalConfig()
	
	log = "Acquiring master lock to read shows from cache..."
	print log
	MASTER_LOCK.acquire()
	try:
		showsString = appConfig.Implode(SEPARATOR, KEY_SHOWS)
		log = "Shows string: " + showsString
		print log
		
		shows = []
		if showsString != "":
			showlist = showsString.split(SEPARATOR)
			for showname in showlist:
				show = Show()
				show.name = showname
				showPathKey = show.name + KEY_SUFFIX_SHOW_PATH
				show.path = appConfig.GetValue(showPathKey)
				shows.append(show)
				locks[show.name] = threading.RLock()
		else:
			log = "Warning, no shows list found in cache, forgot to initialize cache?"
			print log
			
		showsString = appConfig.Implode(SEPARATOR, KEY_SHOWS)
		log = "Shows string after: " + showsString
		print log
	finally:
		log = "Releasing master lock after reading shows from cache"
		print log
		MASTER_LOCK.release()
	
	return shows

def fetchShows():
	sg = mc.Http()
	html = sg.Get(TOU_TV_BASE_URL + "/repertoire")
	shows = []
	results = re.compile('href="(.+?)">\s+<h1 class="titreemission">(.+?)</h1>').findall(html)
	mc.LogDebug("trying to load list of shows...")
	for url, name in results:
		url = TOU_TV_BASE_URL + url
		show = Show()
		show.name = name
		show.path = url
		shows.append(show)
		log = "adding " + name
		print log
	return shows
	
def getShowListItems(shows):
	showItems = mc.ListItems()
	for show in shows:
		showItem = mc.ListItem(mc.ListItem.MEDIA_UNKNOWN)
		showItem.SetLabel(show.name)
		showItem.SetPath(show.path)
		showItems.append(showItem)
	return showItems

def getEpisodeListItems(show, episodes):
	episodeItems = mc.ListItems()
	for episode in episodes:
		episodeItem = mc.ListItem(mc.ListItem.MEDIA_VIDEO_EPISODE)
		episodeItem.SetImage(0, show.backgroundUrl)
		episodeItem.SetLabel(episode.title)
		episodeItem.SetSeason(episode.season)
		episodeItem.SetTVShowTitle(show.name)
		episodeItem.SetDescription(episode.description)
		episodeItem.SetThumbnail(episode.thumbnailUrl)
		episodeItem.SetTitle(episode.title)
		episodeItem.SetPath(episode.videoUrl)
		episodeItem.SetProperty("PlayPath", episode.videoPath)
		episodeItem.SetEpisode(episode.episode)
		episodeItems.append(episodeItem)
		
	return episodeItems
	
def updateShowDataCache(show, appConfig):
	# Waiting for master lock
	log = "Waiting for Master lock to update show data cache..."
	print log
	MASTER_LOCK.acquire()
	try:
		log = "Acquiring lock to update show data cache (" + show.name + ")"
		print log
		locks[show.name].acquire()
	finally:
		log = "Releasing master lock after getting show data lock (" + show.name + ")"
		print log
		MASTER_LOCK.release()
		
	try:
		episodes = fetchShowEpisodes(show)
		clearShowDataCache(show, appConfig)
		key = show.name + KEY_SUFFIX_SHOW_BACKGROUND
		appConfig.SetValue(key, show.backgroundUrl)
		
		for episode in episodes:
			key = show.name + KEY_SUFFIX_EPISODE_LIST
			appConfig.PushBackValue(key, episode.videoPath)
			key = episode.videoPath + KEY_SUFFIX_EPISODE_TITLE
			appConfig.SetValue(key, episode.title)
			key = episode.videoPath + KEY_SUFFIX_EPISODE_THUMBNAIL
			appConfig.SetValue(key, episode.thumbnailUrl)
			key = episode.videoPath + KEY_SUFFIX_EPISODE_DESCRIPTION
			appConfig.SetValue(key, episode.description)
			key = episode.videoPath + KEY_SUFFIX_EPISODE_VIDEO_URL
			appConfig.SetValue(key, episode.videoUrl)
			key = episode.videoPath + KEY_SUFFIX_EPISODE_SEASON
			appConfig.SetValue(key, str(episode.season))
			key = episode.videoPath + KEY_SUFFIX_EPISODE_NUMBER
			appConfig.SetValue(key, str(episode.episode))
		
		lastUpdateTime = time.time()
		key = show.name + KEY_SUFFIX_LAST_UPDATED
		appConfig.SetValue(key, str(lastUpdateTime))
		
		log = "Updated list of episodes for show (" + show.name + ") and set episode list last update time to:" + str(lastUpdateTime)
		print log
	finally:
		locks[show.name].release()
		log = "Releasing lock after update to show data cache (" + show.name + ")"
		print log
	return 1
	
def clearShowDataCache(show, appConfig):
	# Waiting for master lock
	log = "Waiting for Master lock to clear show data cache..."
	print log
	MASTER_LOCK.acquire()
	try:
		log = "Acquiring lock to clear show data cache (" + show.name + ")"
		print log
		locks[show.name].acquire()
	finally:
		log = "Releasing master lock after getting lock for show data cache (" + show.name + ")"
		print log
		MASTER_LOCK.release()
		
	try:
		key = show.name + KEY_SUFFIX_EPISODE_LIST
		episodesString = appConfig.Implode(SEPARATOR, key)
		log = "Episodes string: " + episodesString
		print log
		
		key = show.name + KEY_SUFFIX_SHOW_BACKGROUND
		appConfig.Reset(key)
		
		episodes = []
		if episodesString != "":
			episodes = episodesString.split(SEPARATOR)
			for videoPath in episodes:
				key = videoPath + KEY_SUFFIX_EPISODE_TITLE
				appConfig.Reset(key)
				key = videoPath + KEY_SUFFIX_EPISODE_THUMBNAIL
				appConfig.Reset(key)
				key = videoPath + KEY_SUFFIX_EPISODE_DESCRIPTION
				appConfig.Reset(key)
				key = videoPath + KEY_SUFFIX_EPISODE_VIDEO_URL
				appConfig.Reset(key)
				key = videoPath + KEY_SUFFIX_EPISODE_SEASON
				appConfig.Reset(key)
				key = videoPath + KEY_SUFFIX_EPISODE_NUMBER
				appConfig.Reset(key)
			key = show.name + KEY_SUFFIX_EPISODE_LIST
			appConfig.Reset(key)
			key = show.name + KEY_SUFFIX_LAST_UPDATED
			appConfig.Reset(key)
		else:
			log = "Warning, no episode list found in cache, cache inconsistent"
			print log
	finally:
		locks[show.name].release()
		log = "Releasing lock after clearing show data cache (" + show.name + ")"
		print log
	log = "Cleared show data from cache (" + show.name + ")"
	print log
	return 1
	
def getShowDataFromCache(show):
	appConfig = mc.GetApp().GetLocalConfig()
	
	# Waiting for master lock
	log = "Waiting for Master lock to retrieve show data cache..."
	print log
	MASTER_LOCK.acquire()
	try:
		log = "Acquiring lock to retrieve show data cache (" + show.name + ")"
		print log
		locks[show.name].acquire()
	finally:
		log = "Releasing master lock after getting lock for show data cache (" + show.name + ")"
		print log
		MASTER_LOCK.release()
		
	try:
		key = show.name + KEY_SUFFIX_LAST_UPDATED
		lastUpdate = appConfig.GetValue(key)
		
		if lastUpdate == "":
			updateShowDataCache(show, appConfig)
		else:
			expirationTime = float(lastUpdate) + DATA_EXPIRATION
			
			log = "Calculated expiration time for episodes is: " + str(expirationTime) + ", currentTime is: " + str(time.time())
			print log
			
			if time.time() > expirationTime:
				updateShowDataCache(show, appConfig)
			else:
				log = "List of episodes still valid, last updated: " + lastUpdate
				print log
		
		key = show.name + KEY_SUFFIX_EPISODE_LIST
		episodesString = appConfig.Implode(SEPARATOR, key)
		log = "Episodes string: " + episodesString
		print log
		
		key = show.name + KEY_SUFFIX_SHOW_BACKGROUND
		show.backgroundUrl = appConfig.GetValue(key)
		
		episodes = []
		if episodesString != "":
			videoPaths = episodesString.split(SEPARATOR)
			for videoPath in videoPaths:
				episode = Episode()
				episode.videoPath = videoPath
				log = "parsing cache data for episode: " + str(videoPath)
				print log
				key = videoPath + KEY_SUFFIX_EPISODE_TITLE
				episode.title = appConfig.GetValue(key)
				key = videoPath + KEY_SUFFIX_EPISODE_THUMBNAIL
				episode.thumbnailUrl = appConfig.GetValue(key)
				key = videoPath + KEY_SUFFIX_EPISODE_DESCRIPTION
				episode.description = appConfig.GetValue(key)
				key = videoPath + KEY_SUFFIX_EPISODE_VIDEO_URL
				episode.videoUrl = appConfig.GetValue(key)
				key = videoPath + KEY_SUFFIX_EPISODE_SEASON
				episode.season = int(appConfig.GetValue(key))
				key = videoPath + KEY_SUFFIX_EPISODE_NUMBER
				episode.episode = int(appConfig.GetValue(key))
				episodes.append(episode)
		else:
			log = "Warning, no episode list found in cache, something is wrong"
			print log
	finally:
		locks[show.name].release()
		log = "Releasing lock after retrieving show data cache (" + show.name + ")"
		print log
	showsString = appConfig.Implode(SEPARATOR, KEY_SHOWS)
	log = "Finished loading episodes from cache for show (" + show.name + ")"
	print log
	
	return episodes
	
def fetchShowEpisodes(show):
	log = "Fetch episode list for " + show.name
	print log
	sg = mc.Http()	
	showpage = sg.Get(show.path)
	background = re.search('background-image:url\(.*http://(.+)\&.*\)', showpage)
	if background is not None:
		show.backgroundUrl = "http://" + background.group(1)
		#localpath = mc.GetTempDir() + show.name + ".jpg"
		#show.backgroundUrl = localpath
		#sg.Download(backgroundurl, localpath)
		log = "Background url found with local path " + show.backgroundUrl
		print log
	
	episodes = []
	if TOU_TV_MEDIA_FLAG not in showpage:
		info = re.compile('<img id=".+?Details" src="(.+?)".+?class="saison">(.+?)</p>.+?class="episode".+?href="(.+?)".+?<b>(.+?)(&nbsp;)*?</b>.+?<p>(.+?)</p>', re.DOTALL).findall(showpage)
		log = "loading " + show.name + "..."
		print log
		for img, saison, urlvideo, title, trash, desc in info:
			videopageurl = TOU_TV_BASE_URL + urlvideo;
			log = "Interpreting video page at url " + videopageurl
			print log
			videopage = sg.Get(videopageurl)
			p = re.compile("toutv.releaseUrl='(.+?)'")
			pid = p.findall(videopage)
			definitionurl = "http://release.theplatform.com/content.select?pid=" + pid[0] + '&format=SMIL'
			videodef = sg.Get(definitionurl)
			rtmp_url = re.search('<meta base="rtmp:(.+?)"', videodef)
			playurl = re.search('<ref src="mp4:(.+?)"', videodef)
			if playurl: 
				episode = Episode()
				playpath = "mp4:" + playurl.group(1)
				rtmpURL = "rtmp:" + rtmp_url.group(1)
				authpath = re.search('auth=(.*)&', rtmpURL)
				episode.videoUrl = rtmpURL
				episode.thumbnailUrl = img
				episode.title = title
				seasonValues = re.search('(\d+)', saison)
				if seasonValues is not None:
					episode.season = int(seasonValues.group(1))
				episodeValues = re.search('pisode (\d+)', title)
				if episodeValues is not None:
					episode.episode = int(episodeValues.group(1))
				episode.description = desc
				episode.videoPath = playpath
				episodes.append(episode)
			else:
				mc.LogError("skipping item with url " + show.path + ", videopagedefinition: " + videodef)
	else:
		desc, episodeNumber, season, title, img = re.compile('toutv.mediaData.+?"description":"(.+?)".+?"episodeNumber":(\d+).+?"seasonNumber":(.+?),.+?"title":"(.+?)".+?toutv.imageA=\'(.+?)\'').findall(showpage)[0]
		p = re.compile("toutv.releaseUrl='(.+?)'")
		pid = p.findall(showpage)
		definitionurl = "http://release.theplatform.com/content.select?pid=" + pid[0] + '&format=SMIL'
		videodef = sg.Get(definitionurl)
		rtmp_url = re.search('<meta base="rtmp:(.+?)"', videodef)
		playurl = re.search('<ref src="mp4:(.+?)"', videodef)
		if playurl: 
			episode = Episode()
			playpath = "mp4:" + playurl.group(1)
			rtmpURL = "rtmp:" + rtmp_url.group(1)
			episode.title = title
			episode.description = desc
			episode.season = int(season)
			episode.episode = int(episodeNumber)
			episode.thumbnailUrl = img
			episode.videoPath = playpath
			episode.videoUrl = rtmpURL
			episodes.append(episode)
		else:
			mc.LogError("skipping item with url " + show.path + ", videopagedefinition: " + videodef)
	return episodes
	
class Episode:
	title = ""
	thumbnailUrl = ""
	description = ""
	videoUrl = ""
	videoPath = ""
	season = 0
	episode = 0
	
	def __init__(self):
		self.title = ""
		self.thumbnailUrl = ""
		self.description = ""
		self.videoUrl = ""
		self.videoPath = ""
		self.season = 0
		self.episode = 0

class Show:
	name = ""
	path = ""
	backgroundUrl = ""
	
	def __init__(self):
		self.name = ""
		self.path = ""
		self.backgroundUrl = ""
		
class PreFetchingWorker(threading.Thread):
	def __init__(self, shows):
		self.shows = shows
		threading.Thread.__init__(self, name="PreFetchingWorker-Thread")
	
	def run(self):
		log = "[PreFetchWorker] Updating episodes for list of shows"
		print log
		
		numberOfShowsUpdated = 0
		appConfig = mc.GetApp().GetLocalConfig()
		
		for show in self.shows:
			key = show.name + KEY_SUFFIX_LAST_UPDATED
			lastUpdate = appConfig.GetValue(key)
			
			if lastUpdate == "":
				numberOfShowsUpdated = numberOfShowsUpdated + 1
				updateShowDataCache(show, appConfig)
			else:
				expirationTime = float(lastUpdate) + DATA_EXPIRATION
		
				log = "[PreFetchWorker] Calculated expiration time for episodes is: " + str(expirationTime) + ", currentTime is: " + str(time.time())
				print log
		
				if time.time() > expirationTime:
					numberOfShowsUpdated = numberOfShowsUpdated + 1
					updateShowDataCache(show, appConfig)
				else:
					log = "[PreFetchWorker] List of episodes still valid, last updated: " + lastUpdate
					print log
			
		log = "[PreFetchWorker] job is done, updated " + str(numberOfShowsUpdated) + " shows"
		print log