import mc
import re
import time
import traceback
import sys

TOU_TV_MEDIA_FLAG = 'toutv.mediaData'
TOU_TV_BASE_URL = 'http://www.tou.tv'
DATA_VERSION = 3
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

def initCache():
	appConfig = mc.GetApp().GetLocalConfig()
	# Could be removed to optimize loading but since data fetching had been optimized, it feels more safe to reset everything on startup
	#appConfig.ResetAll()
	
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
	except:
		exc_type, exc_value, exc_traceback = sys.exc_info()
		mc.LogError(repr(traceback.format_exception(exc_type, exc_value, exc_traceback)))
		print repr(traceback.format_exception(exc_type, exc_value, exc_traceback))
		
	return genres

def fetchShows(listingPage):
	shows = []
	try:
		sg = mc.Http()
		html = sg.Get(listingPage)
		results = re.compile('href="(.+?)">\s+<h1 class="titreemission">(.+?)</h1>').findall(html)
		mc.LogDebug("trying to load list of shows...")
		for url, name in results:
			url = TOU_TV_BASE_URL + url
			show = Show()
			show.name = name
			show.path = url
			shows.append(show)
			mc.LogDebug("Adding " + name)
	except:
		exc_type, exc_value, exc_traceback = sys.exc_info()
		mc.LogError(repr(traceback.format_exception(exc_type, exc_value, exc_traceback)))
		print repr(traceback.format_exception(exc_type, exc_value, exc_traceback))
		
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
			desc, episodeNumber, season, title, img = re.compile('toutv.mediaData.+?"[dD]escription":"(.+?)".+?"[eE]pisodeNumber":(\d+).+?"[sS]easonNumber":(.+?),.+?"[tT]itle":"(.+?)".+?toutv.imageA=\'(.+?)\'').findall(showpage)[0]
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
	except:
		exc_type, exc_value, exc_traceback = sys.exc_info()
		mc.LogError(repr(traceback.format_exception(exc_type, exc_value, exc_traceback)))
		print repr(traceback.format_exception(exc_type, exc_value, exc_traceback))
	
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