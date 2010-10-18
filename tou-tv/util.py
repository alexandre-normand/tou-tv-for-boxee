import mc
import re
import time

TOU_TV_MEDIA_FLAG = 'toutv.mediaData'
TOU_TV_BASE_URL = 'http://www.tou.tv'
DATA_VERSION = 1
DATA_EXPIRATION = 60 * 60 * 24
KEY_DATA_VERSION = "dataVersion"
KEY_LAST_SHOW_LIST_UPDATE = "showsLastUpdated"
KEY_SHOWS = "shows"
KEY_SUFFIX_SHOW_PATH = ".path"
KEY_SUFFIX_EPISODE_LIST = ".episodes"
KEY_SUFFIX_LAST_UPDATE_EPISODES = ".lastUpdated"
SEPARATOR = "<itemseparator>"

def initCache():
	appConfig = mc.GetApp().GetLocalConfig()
	# TODO : remove this once testing has proven it works
	#appConfig.ResetAll()
	
	currentDataVersion = appConfig.GetValue(KEY_DATA_VERSION)
	lastUpdate = appConfig.GetValue(KEY_LAST_SHOW_LIST_UPDATE)
	
	log = "Current config is: DataVersion(" + currentDataVersion + "), lastUpdate(" + lastUpdate + "), Shows(" + appConfig.Implode(SEPARATOR, KEY_SHOWS) + ")"
	print log
	
	if currentDataVersion != "":
		if DATA_VERSION > int(currentDataVersion):
			log = "Resetting all config"
			appConfig.ResetAll()
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
	for show in shows:
		appConfig.PushBackValue(KEY_SHOWS, show.name)
		showPathKey = show.name + KEY_SUFFIX_SHOW_PATH
		appConfig.SetValue(showPathKey, show.path)
	
	lastUpdateTime = time.time()
	appConfig.SetValue(KEY_LAST_SHOW_LIST_UPDATE, str(lastUpdateTime))
	
	log = "Updated list of shows and last update time set to:" + str(lastUpdateTime)
	print log
	return 1

def getShowsFromCache():
	appConfig = mc.GetApp().GetLocalConfig()
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
	else:
		log = "Warning, no shows list found in cache, forgot to initialize cache?"
		print log
		
	showsString = appConfig.Implode(SEPARATOR, KEY_SHOWS)
	log = "Shows string after: " + showsString
	print log
	
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
		episodeItem.SetLabel(episode.title)
		episodeItem.SetSeason(episode.season)
		episodeItem.SetTVShowTitle(show)
		episodeItem.SetDescription(episode.description)
		episodeItem.SetThumbnail(episode.thumbnailUrl)
		episodeItem.SetTitle(episode.title)
		episodeItem.SetPath(episode.videoUrl)
		episodeItem.SetProperty("PlayPath", episode.videoPath)
		episodeItems.append(episodeItem)
		
	return episodeItems
	
def fetchShowEpisodes(name, path):
	log = "Fetch episode list for " + name
	print log
	sg = mc.Http()	
	showpage = sg.Get(path)
	episodes = []
	if TOU_TV_MEDIA_FLAG not in showpage:
		info = re.compile('<img id=".+?" src="(.+?)".+?class="saison">(.+?)</p>.+?class="episode".+?href="(.+?)".+?<b>(.+?)(&nbsp;)*?</b>.+?<p>(.+?)</p>', re.DOTALL).findall(showpage)
		log = "loading " + name + "..."
		print log
		for img, saison, urlvideo, title, trash, desc in info:
			videopageurl = TOU_TV_BASE_URL + urlvideo;
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
				episode.season = int(seasonValues.group(1))
				episode.description = desc
				episode.videoPath = playpath
				episodes.append(episode)
			else:
				mc.LogError("skipping item with url " + showurl + ", videopagedefinition: " + videodef)
	else:
		desc, season, title, img = re.compile('toutv.mediaData.+?"description":"(.+?)".+?"seasonNumber":(.+?),.+?"title":"(.+?)".+?toutv.imageA=\'(.+?)\'').findall(showpage)[0]
		videopageurl = TOU_TV_BASE_URL + showurl;
		videopage = sg.Get(videopageurl)
		p = re.compile("toutv.releaseUrl='(.+?)'")
		pid = p.findall(videopage)
		definitionurl = "http://release.theplatform.com/content.select?pid=" + pid[0] + '&format=SMIL'
		videodef = sg.Get(definitionurl)
		rtmp_url = re.search('<meta base="rtmp:(.+?)"', videodef)
		playurl = re.search('<ref src="mp4:(.+?)"', videodef)
		if playurl: 
			playpath = "mp4:" + playurl.group(1)
			rtmpURL = "rtmp:" + rtmp_url.group(1)
			episode.title = title
			episode.description = desc
			episode.season = int(season)
			episode.thumbnailUrl = img
			episode.videoPath = playpath
			episode.videoUrl = rtmpURL
			episodes.append(episode)
		else:
			mc.LogError("skipping item with url " + showurl + ", videopagedefinition: " + videodef)
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
	episodes = []
	
	def __init__(self):
		self.name = ""
		self.path = ""
		self.episodes = []