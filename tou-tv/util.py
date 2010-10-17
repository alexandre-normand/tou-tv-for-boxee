import mc
import re

TOU_TV_MEDIA_FLAG = 'toutv.mediaData'
TOU_TV_BASE_URL = 'http://www.tou.tv'

def fetchShows():
	sg = mc.Http()
	html = sg.Get(TOU_TV_BASE_URL + "/repertoire")
	items = mc.ListItems()
	results = re.compile('href="(.+?)">\s+<h1 class="titreemission">(.+?)</h1>').findall(html)
	mc.LogDebug("trying to load list of shows...")
	for url, name in results:
		url = TOU_TV_BASE_URL + url
		item = mc.ListItem(mc.ListItem.MEDIA_UNKNOWN)
		item.SetLabel(name)
		item.SetPath(url)
		mc.LogDebug("adding " + name)
		items.append(item)
	return items

def fetchShowEpisodes(name, path):
	mc.LogDebug("Fetch episode list for " + name)
	sg = mc.Http()	
	showpage = sg.Get(path)
	items = mc.ListItems()
	if TOU_TV_MEDIA_FLAG not in showpage:
		info = re.compile('<img id=".+?" src="(.+?)".+?class="saison">(.+?)</p>.+?class="episode".+?href="(.+?)".+?<b>(.+?)(&nbsp;)*?</b>.+?<p>(.+?)</p>', re.DOTALL).findall(showpage)
		mc.LogDebug("loading " + name + "...")
		for img, saison, urlvideo, title, trash, desc in info:
			item = mc.ListItem(mc.ListItem.MEDIA_VIDEO_EPISODE)
			item.SetLabel(name)
			videopageurl = TOU_TV_BASE_URL + urlvideo;
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
				authpath = re.search('auth=(.*)&', rtmpURL)
				item.SetPath(rtmpURL)
				item.SetThumbnail(img)
				item.SetTitle(title)
				seasonValues = re.search('(\d+)', saison)
				item.SetSeason(int(seasonValues.group(1)))
				item.SetTVShowTitle(name)
				item.SetDescription(desc)
				item.SetProperty("PlayPath", playpath)
			else:
				mc.LogError("skipping item with url " + showurl + ", videopagedefinition: " + videodef)
			items.append(item)
	else:
		desc, season, title, img = re.compile('toutv.mediaData.+?"description":"(.+?)".+?"seasonNumber":(.+?),.+?"title":"(.+?)".+?toutv.imageA=\'(.+?)\'').findall(showpage)[0]
		item = mc.ListItem(mc.ListItem.MEDIA_VIDEO_EPISODE)
		item.SetLabel(name)
		item.SetTitle(title)
		item.SetTVShowTitle(name)
		item.SetDescription(desc)
		item.SetSeason(int(season))
		item.SetThumbnail(img)
		videopageurl = TOU_TV_BASE_URL + showurl;
		videopage = sg.Get(videopageurl)
		p = re.compile("toutv.releaseUrl='(.+?)'")
		pid = p.findall(videopage)
		definitionurl = "http://release.theplatform.com/content.select?pid=" + pid[0] + '&format=SMIL'
		videodef = sg.Get(definitionurl)
		if playurl: 
			playpath = "mp4:" + playurl.group(1)
			item.SetPath(playpath)
			item.SetThumbnail(img)
			item.SetTitle(title)
			seasonValues = re.search('(\d+)', saison)
			item.SetSeason(int(seasonValues.group(1)))
			item.SetTVShowTitle(name)
			item.SetDescription(desc)
		else:
			mc.LogError("skipping item with url " + showurl + ", videopagedefinition: " + videodef)
	return items