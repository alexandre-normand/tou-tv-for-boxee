#!/usr/bin/python
# -*- coding: utf-8 -*-

import mc
import re
import time
import traceback
import sys
import simplejson as json

TOU_TV_MEDIA_FLAG = "toutv.mediaData"
TOU_TV_BASE_URL = "http://www.tou.tv"
DATA_VERSION = 3
KEY_DATA_VERSION = "dataVersion"
KEY_SUFFIX_SHOW_PATH = ".path"
KEY_RECENTLY_VIEWED = "recentlyViewedShows"
INTERNAL_RECENTLY_VIEWED = "local://RECENTLY_VIEWED"
SEPARATOR = "<itemseparator>"

REPERTOIRE_SERVICE_URL = "http://api.tou.tv/v1/toutvapiservice.svc/json/GetPageRepertoire"
EMISSION_SERVICE_URL = "http://api.tou.tv/v1/toutvapiservice.svc/json/GetPageEmission?emissionId="

globalEmissions = None
globalGenres = None

def initialGet():

	global globalEmissions
	global globalGenres

	sg = mc.Http()
	url_data = sg.Get(REPERTOIRE_SERVICE_URL)
	jsonRepertoire = json.loads(url_data)

	globalEmissions = jsonRepertoire["d"]["Emissions"]
	globalGenres = jsonRepertoire["d"]["Genres"]

def getGenres():
	genres = []
	try:
		#mc.LogDebug("trying to load list of shows...")
		genre = Genre()
		genre.label = "Émissions récemment visionnées"
		genre.filter = INTERNAL_RECENTLY_VIEWED
		genres.append(genre)

		for g in globalGenres:
			genre = Genre()
			genre.label = g["Title"].encode("utf-8")
			genre.filter = g["Title"].encode("utf-8")
			genres.append(genre)
			#mc.LogDebug("Adding genre " + genre.label)
		# Always add filter for all shows
		genre = Genre()
		genre.label = "Toutes les émissions"
		genre.filter = ""
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

def fetchShows(filter):
	shows = []
	try:
		#mc.LogDebug("trying to load list of shows...")
		for e in globalEmissions:

			if(filter != "" and filter != e["Genre"].encode("utf-8")):
				continue

			show = Show()
			show.name = e["Titre"].encode("utf-8")
			show.path = "%s%i" % (EMISSION_SERVICE_URL, e["Id"])
			shows.append(show)
			#mc.LogDebug("Adding " + name)

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

def fetchShowEpisodes(show):
	#mc.LogDebug("Fetch episode list for " + show.name)
	episodes = []
	try:

		sg = mc.Http()
		url_data = sg.Get(show.path)
		obj = json.loads(url_data)
		jsonEpisodes = obj["d"]["Episodes"]
		jsonEmission = obj['d']['Emission']

		if(jsonEmission["ImageBackground"] != None):
			show.backgroundUrl = jsonEmission["ImageBackground"].encode("ascii")

		for e in jsonEpisodes:
			episode = Episode()
			episode.title = e["Title"].encode("utf-8")
			episode.description = e["Description"].encode("utf-8")
			episode.season = e["SeasonNumber"]
			episode.episode = e["EpisodeNumber"]
			if(e["ImageThumbMicroG"] != None):
				episode.thumbnailUrl = e["ImageThumbMicroG"].encode("ascii")
			episode.path = "http://api.radio-canada.ca/validationMedia/v1/Validation.html?appCode=thePlatform&deviceType=iphone4&connectionType=wifi&idMedia=" + e["PID"].encode("ascii") + "&output=json"
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

def getGenreListItems(genres):
	genreItems = mc.ListItems()
	for genre in genres:
		genreItem = mc.ListItem(mc.ListItem.MEDIA_UNKNOWN)
		genreItem.SetLabel(genre.label)
		genreItem.SetPath(genre.filter)
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
		episodeItem.SetPath(episode.path)
		episodeItem.SetProperty("show.path", show.path)
		episodeItem.SetProperty("background", show.backgroundUrl)
		episodeItem.SetEpisode(episode.episode)
		episodeItem.SetProperty("isFilter", "false")
		episodeItems.append(episodeItem)

	return episodeItems

def addVideoDataToItem(episodeItem):
	sg = mc.Http()
	videodef = sg.Get(episodeItem.GetPath())
	print videodef
	videodata = json.loads(videodef)
	if videodata["url"]:
		url = videodata["url"].encode("ascii")
		episodeItem.SetPath(url)
		mc.LogError("Play: " + url)
	else:
		mc.LogError("skipping item with url " + episodeItem.GetPath() + ", videopagedefinition: " + videodef)
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
			if(show.path.startswith(EMISSION_SERVICE_URL) == False):
				# Check for shows added after or equal to version 1.7
				continue
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
	videoPath = ""
	path = ""
	season = 0
	episode = 0

	def __init__(self):
		self.title = ""
		self.thumbnailUrl = ""
		self.description = ""
		self.videoPath = ""
		self.path = ""
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
	filter = ""

	def __init__(self):
		self.label = ""
		self.filter = ""
