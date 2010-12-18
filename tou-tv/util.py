import mc
import re
import time
import traceback
import sys

TOU_TV_MEDIA_FLAG = 'toutv.mediaData'
TOU_TV_BASE_URL = 'http://www.tou.tv'
DATA_VERSION = 3
KEY_DATA_VERSION = "dataVersion"
KEY_SUFFIX_SHOW_PATH = ".path"
KEY_RECENTLY_VIEWED = "recentlyViewedShows"
INTERNAL_RECENTLY_VIEWED = "local://RECENTLY_VIEWED"
SEPARATOR = "<itemseparator>"

def initCache():
	appConfig = mc.GetApp().GetLocalConfig()
	# Could be removed to optimize loading but since data fetching had been optimized, it feels more safe to reset everything on startup
	# appConfig.ResetAll()
	
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
	
	mc.LogDebug("dataversion: " + str(DATA_VERSION))
	
	return 0

def getGenres():
	genres = []
	try:
		sg = mc.Http()
		html = sg.Get(TOU_TV_BASE_URL)
		results = re.compile('a id="GenresFooterRepeater.* href="/(.+?)">(.+?)</a>').findall(html)
		mc.LogDebug("trying to load list of shows...")
		if len(results) > 0:
			recentlyViewedShows = loadRecentlyViewedShows()
			if len(recentlyViewedShows) > 0:
				genre = Genre()
				genre.label = "Émissions récemment visionnées"
				genre.listingPage = INTERNAL_RECENTLY_VIEWED
				genres.append(genre)
				
			for path, name in results:
				url = TOU_TV_BASE_URL + "/repertoire/" + path
				genre = Genre()
				genre.label = name
				genre.listingPage = url
				genres.append(genre)
				mc.LogDebug("Adding genre " + name + " with path " + url)
			# Always add filter for all shows
			genre = Genre()
			genre.label = "Toutes les émissions"
			genre.listingPage = TOU_TV_BASE_URL + "/repertoire"
			genres.append(genre)
		else:
			mc.LogError("Error while trying to find genre filters in page content: " + html)
			# create a fake entry with an error message
			genre = Genre()
			genre.label = "Une erreur est survenue en allant récupérer la liste des filtres, si le problème persiste, veuillez envoyer boxee.log à http://code.google.com/p/tou-tv-for-boxee/issues/list."
			genre.listingPage = ""
			genres.append(genre)
	except:
		exc_type, exc_value, exc_traceback = sys.exc_info()
		mc.LogError(repr(traceback.format_exception(exc_type, exc_value, exc_traceback)))
		print repr(traceback.format_exception(exc_type, exc_value, exc_traceback))
		# create a fake entry with an error message
		genre = Genre()
		genre.label = "Une erreur est survenue en allant récupérer la liste des filtres, si le problème persiste, veuillez envoyer boxee.log à http://code.google.com/p/tou-tv-for-boxee/issues/list."
		genre.listingPage = ""
		genres.append(genre)
		
	return genres

def fetchShows(listingPage):
	shows = []
	try:
		sg = mc.Http()
		html = sg.Get(listingPage)
		results = re.compile('href="(.+?)">\s+<h1 class="titreemission">(.+?)</h1>').findall(html)
		mc.LogDebug("trying to load list of shows...")
		if len(results) > 0:
			for url, name in results:
				url = TOU_TV_BASE_URL + url
				show = Show()
				show.name = name
				show.path = url
				shows.append(show)
				mc.LogDebug("Adding " + name)
		else:
			mc.LogError("Error while trying to find shows in page content: " + html)
			# create a fake entry with an error message
			show = Show()
			show.name = "Une erreur est survenue en allant récupérer la liste des émissions, si le problème persiste, veuillez envoyer boxee.log à http://code.google.com/p/tou-tv-for-boxee/issues/list."
			show.path = ""
			shows.append(show)
	except:
		exc_type, exc_value, exc_traceback = sys.exc_info()
		mc.LogError(repr(traceback.format_exception(exc_type, exc_value, exc_traceback)))
		print repr(traceback.format_exception(exc_type, exc_value, exc_traceback))
		# create a fake entry with an error message
		show = Show()
		show.name = "Une erreur est survenue en allant récupérer la liste des émissions, si le problème persiste, veuillez envoyer boxee.log à http://code.google.com/p/tou-tv-for-boxee/issues/list."
		show.path = ""
		shows.append(show)
		
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
	
def fetchShowEpisodes(show):
	mc.LogDebug("Fetch episode list for " + show.name)
	episodes = []
	try:
		sg = mc.Http()	
		showpage = sg.Get(show.path)
		background = re.search('background-image:url\(.*http://(.+)\&.*\)', showpage)
		if background is not None:
			show.backgroundUrl = "http://" + background.group(1)
			mc.LogDebug("Background url found with local path " + show.backgroundUrl)
		
		if TOU_TV_MEDIA_FLAG not in showpage:
			results = re.compile('<img id=".+?Details" src="(.+?)".+?class="saison">(.+?)</p>.+?class="episode".+?href="(.+?)".+?<b>(.+?)(&nbsp;)*?</b>.+?<p>(.+?)</p>', re.DOTALL).findall(showpage)
			mc.LogDebug("loading " + show.name + " episodes...")
			if len(results) > 0:
				for img, saison, urlvideo, title, trash, desc in results:
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
				mc.LogError("Error while trying to find episodes in page: " + showpage)
				# create a fake entry with an error message
				episode = Episode()
				episode.title = "Une erreur est survenue en allant récupérer la liste des épisodes, si le problème persiste, veuillez envoyer boxee.log à http://code.google.com/p/tou-tv-for-boxee/issues/list."
				episodes.append(episode)
		else:
			results = re.compile('toutv.mediaData.+?"[dD]escription":"(.+?)".+?"[eE]pisodeNumber":(\d+).+?"[sS]easonNumber":(.+?),.+?"[tT]itle":"(.+?)".+?toutv.imageA=\'(.+?)\'').findall(showpage)
			if len(results) > 0:
				desc, episodeNumber, season, title, img = results[0]
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
			else:
				mc.LogError("Error while trying to find episodes in single-occurence page: " + showpage)
				# create a fake entry with an error message
				episode = Episode()
				episode.title = "Une erreur est survenue en allant récupérer la liste des épisodes, si le problème persiste, veuillez envoyer boxee.log à http://code.google.com/p/tou-tv-for-boxee/issues/list."
				episodes.append(episode)
	except:
		exc_type, exc_value, exc_traceback = sys.exc_info()
		mc.LogError(repr(traceback.format_exception(exc_type, exc_value, exc_traceback)))
		print repr(traceback.format_exception(exc_type, exc_value, exc_traceback))
		# create a fake entry with an error message
		episode = Episode()
		episode.title = "Une erreur est survenue en allant récupérer la liste des épisodes, si le problème persiste, veuillez envoyer boxee.log à http://code.google.com/p/tou-tv-for-boxee/issues/list."
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
	
def addShowToRecentList(show):
	shows = loadRecentlyViewedShows()
	if show in set(shows):
		shows.remove(show)
	shows.insert(0, show)
	
	if len(shows) > 5:
		del shows[5:len(shows) - 1]
	
	updateRecentlyViewedShows(shows)
	
def loadRecentlyViewedShows():
	appConfig = mc.GetApp().GetLocalConfig()
	recentlyViewedString = appConfig.Implode(SEPARATOR, KEY_RECENTLY_VIEWED)
	shows = []
	if recentlyViewedString != "":
		showlist = recentlyViewedString.split(SEPARATOR)
		for showname in showlist:
			show = Show()
			show.name = showname
			showPathKey = show.name + KEY_SUFFIX_SHOW_PATH
			show.path = appConfig.GetValue(showPathKey)
			shows.append(show)
	return shows
	
def updateRecentlyViewedShows(shows):
	appConfig = mc.GetApp().GetLocalConfig()
	appConfig.ResetAll()
	appConfig.SetValue(KEY_DATA_VERSION, str(DATA_VERSION))
	for show in shows:
		appConfig.PushBackValue(KEY_RECENTLY_VIEWED, show.name)
		key = show.name + KEY_SUFFIX_SHOW_PATH
		appConfig.SetValue(key, show.path)
	
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
		
	def __eq__(self, other) : 
		return self.name == other.name

	def __hash__(self):
		return hash(self.name)
	
class Genre:
	label = ""
	listingUrl = ""
	
	def __init__(self):
		self.label = ""
		self.listingUrl = ""