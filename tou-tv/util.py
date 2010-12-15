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
KEY_SUFFIX_EPISODE_DOES_DETAIL_URL_INCLUDE_DATA = ".doesDetailUrlIncludeData"
KEY_SUFFIX_GENRE_LISTING_PAGE = ".listingPage"
SEPARATOR = "<itemseparator>"

locks = dict()
MASTER_LOCK = threading.RLock()

def initCache():
	appConfig = mc.GetApp().GetLocalConfig()
	# Could be removed to optimize loading but since data fetching had been optimized, it feels more safe to reset everything on startup
	appConfig.ResetAll()
	
	currentDataVersion = appConfig.GetValue(KEY_DATA_VERSION)
	lastUpdate = appConfig.GetValue(KEY_LAST_SHOW_LIST_UPDATE)
	
	mc.LogDebug("Current config is: DataVersion(" + currentDataVersion + "), lastUpdate(" + lastUpdate + "), Shows(" + appConfig.Implode(SEPARATOR, KEY_SHOWS) + ")")
	
	if currentDataVersion != "":
		if DATA_VERSION > int(currentDataVersion):
			mc.LogDebug("Resetting all config because new data version is " + str(DATA_VERSION) + " and old data version was " + currentDataVersion)
			appConfig.ResetAll()
			appConfig.SetValue(KEY_DATA_VERSION, str(DATA_VERSION))
	else:
		appConfig.SetValue(KEY_DATA_VERSION, str(DATA_VERSION))
	
	lastUpdate = appConfig.GetValue(KEY_LAST_SHOW_LIST_UPDATE)
	
	if lastUpdate == "":
		updateShowListCache()
	else:
		expirationTime = float(lastUpdate) + DATA_EXPIRATION
		
		mc.LogDebug("Calculated expiration time is: " + str(expirationTime) + ", currentTime is: " + str(time.time()))
		
		if time.time() > expirationTime:
			updateShowListCache()
		else:
			mc.LogDebug("List of shows still valid, last updated: " + lastUpdate)
		
	mc.LogDebug("dataversion: " + str(DATA_VERSION))
	
	return 0

def getGenres():
	sg = mc.Http()
	html = sg.Get(TOU_TV_BASE_URL)
	genres = []
	results = re.compile('a id="GenresFooterRepeater.* href="/(.+?)">(.+?)</a>').findall(html)
	mc.LogDebug("trying to load list of shows...")
	for path, name in results:
		url = TOU_TV_BASE_URL + "/repertoire/" + path
		genre = Genre()
		genre.label = name
		genre.listingPage = url
		genres.append(genre)
		mc.LogDebug("Adding genre " + name + " with path " + url)
	return genres
	
def updateShowListCache(listingPage):
	appConfig = mc.GetApp().GetLocalConfig()
	shows = fetchShows(listingPage)
	mc.LogDebug("Acquiring master lock...")
	MASTER_LOCK.acquire()
	try:
		# Workaround for reset just removing the first entry for that key instead of clearing all 
		# stacked values
		appConfig.SetValue(KEY_SHOWS, "")
		appConfig.Reset(KEY_SHOWS)
		
		for show in shows:
			appConfig.PushBackValue(KEY_SHOWS, show.name)
			showPathKey = show.name + KEY_SUFFIX_SHOW_PATH
			appConfig.SetValue(showPathKey, show.path)
			locks[show.name] = threading.RLock()
		
		lastUpdateTime = time.time()
		appConfig.SetValue(KEY_LAST_SHOW_LIST_UPDATE, str(lastUpdateTime))
		
		mc.LogDebug("Updated list of shows and last update time set to:" + str(lastUpdateTime))
	finally:
		mc.LogDebug("Releasing master lock")
		MASTER_LOCK.release()
	return 1

def getShowsFromCache():
	appConfig = mc.GetApp().GetLocalConfig()
	
	mc.LogDebug("Acquiring master lock to read shows from cache...")
	MASTER_LOCK.acquire()
	try:
		showsString = appConfig.Implode(SEPARATOR, KEY_SHOWS)
		mc.LogDebug("Shows string: " + showsString)
		
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
			mc.LogDebug("Warning, no shows list found in cache, forgot to initialize cache?")
			
		showsString = appConfig.Implode(SEPARATOR, KEY_SHOWS)
		mc.LogDebug("Shows string after: " + showsString)
	finally:
		mc.LogDebug("Releasing master lock after reading shows from cache")
		MASTER_LOCK.release()
	
	return shows

def fetchShows(listingPage):
	sg = mc.Http()
	html = sg.Get(listingPage)
	shows = []
	results = re.compile('href="(.+?)">\s+<h1 class="titreemission">(.+?)</h1>').findall(html)
	mc.LogDebug("trying to load list of shows...")
	for url, name in results:
		url = TOU_TV_BASE_URL + url
		show = Show()
		show.name = name
		show.path = url
		shows.append(show)
		mc.LogDebug("Adding " + name)
	return shows
	
def getGenreListItems(genres):
	genreItems = mc.ListItems()
	for genre in genres:
		genreItem = mc.ListItem(mc.ListItem.MEDIA_UNKNOWN)
		genreItem.SetLabel(genre.label)
		genreItem.SetPath(genre.listingPage)
		genreItem.SetProperty("isFilter", "true")
		genreItems.append(genreItem)
	return genreItems
	
def getShowListItems(shows):
	showItems = mc.ListItems()
	for show in shows:
		showItem = mc.ListItem(mc.ListItem.MEDIA_UNKNOWN)
		showItem.SetLabel(show.name)
		showItem.SetPath(show.path)
		showItem.SetProperty("isFilter", "false")
		showItems.append(showItem)
	return showItems

def getEpisodeListItems(show, episodes):
	episodeItems = mc.ListItems()
	for episode in episodes:
		episodeItem = mc.ListItem(mc.ListItem.MEDIA_VIDEO_EPISODE)
		episodeItem.SetLabel(episode.title)
		episodeItem.SetSeason(episode.season)
		episodeItem.SetTVShowTitle(show.name)
		episodeItem.SetDescription(episode.description)
		episodeItem.SetThumbnail(episode.thumbnailUrl)
		episodeItem.SetTitle(episode.title)
		episodeItem.SetProperty("DetailUrl", episode.detailUrl)
		episodeItem.SetProperty("DoesDetailUrlIncludeData", episode.doesDetailUrlIncludeData)
		# Dummy path that simply needs to be unique, otherwise boxee won't refresh the thumbnail if the path is empty or always the same
		episodeItem.SetPath(episode.thumbnailUrl)
		episodeItem.SetProperty("show.path", show.path)
		episodeItem.SetProperty("background", show.backgroundUrl)
		episodeItem.SetEpisode(episode.episode)
		episodeItem.SetProperty("isFilter", "false")
		episodeItems.append(episodeItem)
		
	return episodeItems
	
def updateShowDataCache(show, appConfig):
	# Waiting for master lock
	mc.LogDebug("Waiting for Master lock to update show data cache...")
	MASTER_LOCK.acquire()
	try:
		mc.LogDebug("Acquiring lock to update show data cache (" + show.name + ")")
		locks[show.name].acquire()
	finally:
		mc.LogDebug("Releasing master lock after getting show data lock (" + show.name + ")")
		MASTER_LOCK.release()
		
	try:
		episodes = fetchShowEpisodes(show)
		clearShowDataCache(show, appConfig)
		key = show.name + KEY_SUFFIX_SHOW_BACKGROUND
		appConfig.SetValue(key, show.backgroundUrl)
		
		for episode in episodes:
			key = show.name + KEY_SUFFIX_EPISODE_LIST
			appConfig.PushBackValue(key, episode.detailUrl)
			key = episode.detailUrl + KEY_SUFFIX_EPISODE_TITLE
			appConfig.SetValue(key, episode.title)
			key = episode.detailUrl + KEY_SUFFIX_EPISODE_DOES_DETAIL_URL_INCLUDE_DATA
			appConfig.SetValue(key, episode.doesDetailUrlIncludeData)
			key = episode.detailUrl + KEY_SUFFIX_EPISODE_THUMBNAIL
			appConfig.SetValue(key, episode.thumbnailUrl)
			key = episode.detailUrl + KEY_SUFFIX_EPISODE_DESCRIPTION
			appConfig.SetValue(key, episode.description)
			key = episode.detailUrl + KEY_SUFFIX_EPISODE_SEASON
			appConfig.SetValue(key, str(episode.season))
			key = episode.detailUrl + KEY_SUFFIX_EPISODE_NUMBER
			appConfig.SetValue(key, str(episode.episode))
		
		lastUpdateTime = time.time()
		key = show.name + KEY_SUFFIX_LAST_UPDATED
		appConfig.SetValue(key, str(lastUpdateTime))
		
		mc.LogDebug("Updated list of episodes for show (" + show.name + ") and set episode list last update time to:" + str(lastUpdateTime))
	finally:
		locks[show.name].release()
		mc.LogDebug("Releasing lock after update to show data cache (" + show.name + ")")
	return 1
	
def clearShowDataCache(show, appConfig):
	# Waiting for master lock
	mc.LogDebug("Waiting for Master lock to clear show data cache...")
	MASTER_LOCK.acquire()
	try:
		mc.LogDebug("Acquiring lock to clear show data cache (" + show.name + ")")
		locks[show.name].acquire()
	finally:
		mc.LogDebug("Releasing master lock after getting lock for show data cache (" + show.name + ")")
		MASTER_LOCK.release()
		
	try:
		key = show.name + KEY_SUFFIX_EPISODE_LIST
		episodesString = appConfig.Implode(SEPARATOR, key)
		mc.LogDebug("Episodes string: " + episodesString)
		
		key = show.name + KEY_SUFFIX_SHOW_BACKGROUND
		appConfig.Reset(key)
		
		episodes = []
		if episodesString != "":
			episodes = episodesString.split(SEPARATOR)
			for detailUrl in episodes:
				key = detailUrl + KEY_SUFFIX_EPISODE_TITLE
				appConfig.Reset(key)
				key = episode.detailUrl + KEY_SUFFIX_EPISODE_DOES_DETAIL_URL_INCLUDE_DATA
				appConfig.Reset(key)
				key = detailUrl + KEY_SUFFIX_EPISODE_THUMBNAIL
				appConfig.Reset(key)
				key = detailUrl + KEY_SUFFIX_EPISODE_DESCRIPTION
				appConfig.Reset(key)
				key = detailUrl + KEY_SUFFIX_EPISODE_SEASON
				appConfig.Reset(key)
				key = detailUrl + KEY_SUFFIX_EPISODE_NUMBER
				appConfig.Reset(key)
			key = show.name + KEY_SUFFIX_EPISODE_LIST
			# Workaround for reset just removing the first entry for that key instead of clearing all 
			# stacked values
			appConfig.SetValue(key, "")
			appConfig.Reset(key)
			key = show.name + KEY_SUFFIX_LAST_UPDATED
			appConfig.Reset(key)
		else:
			mc.LogDebug("Warning, no episode list found in cache, cache inconsistent")
	finally:
		locks[show.name].release()
		mc.LogDebug("Releasing lock after clearing show data cache (" + show.name + ")")
	mc.LogDebug("Cleared show data from cache (" + show.name + ")")
	return 1
	
def getShowDataFromCache(show):
	appConfig = mc.GetApp().GetLocalConfig()
	
	# Waiting for master lock
	mc.LogDebug("Waiting for Master lock to retrieve show data cache...")
	MASTER_LOCK.acquire()
	try:
		mc.LogDebug("Acquiring lock to retrieve show data cache (" + show.name + ")")
		locks[show.name].acquire()
	finally:
		mc.LogDebug("Releasing master lock after getting lock for show data cache (" + show.name + ")")
		MASTER_LOCK.release()
		
	try:
		key = show.name + KEY_SUFFIX_LAST_UPDATED
		lastUpdate = appConfig.GetValue(key)
		
		if lastUpdate == "":
			updateShowDataCache(show, appConfig)
		else:
			expirationTime = float(lastUpdate) + DATA_EXPIRATION
			
			mc.LogDebug("Calculated expiration time for episodes is: " + str(expirationTime) + ", currentTime is: " + str(time.time()))
			
			if time.time() > expirationTime:
				updateShowDataCache(show, appConfig)
			else:
				mc.LogDebug("List of episodes still valid, last updated: " + lastUpdate)
		
		key = show.name + KEY_SUFFIX_EPISODE_LIST
		episodesString = appConfig.Implode(SEPARATOR, key)
		mc.LogDebug("Episodes string: " + episodesString)
		
		key = show.name + KEY_SUFFIX_SHOW_BACKGROUND
		show.backgroundUrl = appConfig.GetValue(key)
		
		episodes = []
		if episodesString != "":
			detailUrls = episodesString.split(SEPARATOR)
			for detailUrl in detailUrls:
				episode = Episode()
				episode.detailUrl = detailUrl
				mc.LogDebug("parsing cache data for episode: " + str(detailUrl))
				key = detailUrl + KEY_SUFFIX_EPISODE_TITLE
				episode.title = appConfig.GetValue(key)
				key = detailUrl + KEY_SUFFIX_EPISODE_DOES_DETAIL_URL_INCLUDE_DATA
				episode.doesDetailUrlIncludeData = appConfig.GetValue(key)
				key = detailUrl + KEY_SUFFIX_EPISODE_THUMBNAIL
				episode.thumbnailUrl = appConfig.GetValue(key)
				key = detailUrl + KEY_SUFFIX_EPISODE_DESCRIPTION
				episode.description = appConfig.GetValue(key)
				key = detailUrl + KEY_SUFFIX_EPISODE_SEASON
				episode.season = int(appConfig.GetValue(key))
				key = detailUrl + KEY_SUFFIX_EPISODE_NUMBER
				episode.episode = int(appConfig.GetValue(key))
				episodes.append(episode)
		else:
			mc.LogDebug("Warning, no episode list found in cache, something is wrong")
	finally:
		locks[show.name].release()
		mc.LogDebug("Releasing lock after retrieving show data cache (" + show.name + ")")
	showsString = appConfig.Implode(SEPARATOR, KEY_SHOWS)
	mc.LogDebug("Finished loading episodes from cache for show (" + show.name + ")")
	
	return episodes
	
def fetchShowEpisodes(show):
	mc.LogDebug("Fetch episode list for " + show.name)
	sg = mc.Http()	
	showpage = sg.Get(show.path)
	background = re.search('background-image:url\(.*http://(.+)\&.*\)', showpage)
	if background is not None:
		show.backgroundUrl = "http://" + background.group(1)
		mc.LogDebug("Background url found with local path " + show.backgroundUrl)
	
	episodes = []
	if TOU_TV_MEDIA_FLAG not in showpage:
		info = re.compile('<img id=".+?Details" src="(.+?)".+?class="saison">(.+?)</p>.+?class="episode".+?href="(.+?)".+?<b>(.+?)(&nbsp;)*?</b>.+?<p>(.+?)</p>', re.DOTALL).findall(showpage)
		mc.LogDebug("loading " + show.name + " episodes...")
		for img, saison, urlvideo, title, trash, desc in info:
			videopageurl = TOU_TV_BASE_URL + urlvideo;
			episode = Episode()
			episode.detailUrl = videopageurl
			episode.thumbnailUrl = img
			realtitle = re.search('(?:Épisode\s(?:\d+)\s:\s)?(.*)', title)
			if not realtitle:
				episode.title = title
			else:
				episode.title = realtitle.group(1)
			seasonValues = re.search('(\d+)', saison)
			if seasonValues is not None:
				episode.season = int(seasonValues.group(1))
			episodeValues = re.search('pisode (\d+)', title)
			if episodeValues is not None:
				episode.episode = int(episodeValues.group(1))
			episode.description = desc
			episode.doesDetailUrlIncludeData = "false"
			episodes.append(episode)
	else:
		desc, episodeNumber, season, title, img = re.compile('toutv.mediaData.+?"description":"(.+?)".+?"episodeNumber":(\d+).+?"seasonNumber":(.+?),.+?"title":"(.+?)".+?toutv.imageA=\'(.+?)\'').findall(showpage)[0]
		p = re.compile("toutv.releaseUrl='(.+?)'")
		pid = p.findall(showpage)
		definitionurl = "http://release.theplatform.com/content.select?pid=" + pid[0] + '&format=SMIL'
		episode = Episode()
		episode.title = title
		episode.description = desc
		episode.season = int(season)
		episode.episode = int(episodeNumber)
		episode.thumbnailUrl = img
		episode.detailUrl = definitionurl
		episode.doesDetailUrlIncludeData = "true"
		episodes.append(episode)
	return episodes

def addVideoDataToItem(episodeItem):
	sg = mc.Http()
	definitionUrl = ""
	if (episodeItem.GetProperty("doesDetailUrlIncludeData") == "true"):
		definitionUrl = episodeItem.GetProperty("detailUrl")
	else:
		videopageurl = episodeItem.GetProperty("detailUrl")
		mc.LogDebug("Interpreting video page at url " + videopageurl)
		videopage = sg.Get(videopageurl)
		p = re.compile("toutv.releaseUrl='(.+?)'")
		pid = p.findall(videopage)
		definitionUrl = "http://release.theplatform.com/content.select?pid=" + pid[0] + '&format=SMIL'
	
	videodef = sg.Get(definitionUrl)
	rtmp_url = re.search('<meta base="rtmp:(.+?)"', videodef)
	playurl = re.search('<ref src="mp4:(.+?)"', videodef)
	if playurl: 
		playpath = "mp4:" + playurl.group(1)
		rtmpURL = "rtmp:" + rtmp_url.group(1)
		authpath = re.search('auth=(.*)&', rtmpURL)
		episodeItem.SetPath(rtmpURL)
		episodeItem.SetProperty("PlayPath", playpath)
	else:
		mc.LogError("skipping item with url " + definitionUrl + ", videopagedefinition: " + videodef)
	return episodeItem
	

class Episode:
	title = ""
	thumbnailUrl = ""
	description = ""
	videoUrl = ""
	videoPath = ""
	detailUrl = ""
	doesDetailUrlIncludeData = "false"
	season = 0
	episode = 0
	
	def __init__(self):
		self.title = ""
		self.thumbnailUrl = ""
		self.description = ""
		self.videoUrl = ""
		self.videoPath = ""
		self.detailUrl = ""
		self.doesDetailUrlIncludeData = "false"
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
	
class Genre:
	label = ""
	listingUrl = ""
	
	def __init__(self):
		self.label = ""
		self.listingUrl = ""
	
class PreFetchingWorker(threading.Thread):
	def __init__(self, shows):
		self.shows = shows
		threading.Thread.__init__(self, name="PreFetchingWorker-Thread")
	
	def run(self):
		mc.LogDebug("[PreFetchWorker] Updating episodes for list of shows")
		
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
		
				mc.LogDebug("[PreFetchWorker] Calculated expiration time for episodes is: " + str(expirationTime) + ", currentTime is: " + str(time.time()))
		
				if time.time() > expirationTime:
					numberOfShowsUpdated = numberOfShowsUpdated + 1
					updateShowDataCache(show, appConfig)
				else:
					mc.LogDebug("[PreFetchWorker] List of episodes still valid, last updated: " + lastUpdate)
			
		mc.LogDebug("[PreFetchWorker] job is done, updated " + str(numberOfShowsUpdated) + " shows")
