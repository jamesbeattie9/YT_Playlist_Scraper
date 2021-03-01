""" Get all youtube videos from a playlist. If the video is deleted/private, 
search for it and return the top 3 google results.
"""
from apiclient.discovery import build
from apiclient.errors import HttpError

import json
import pandas as pd
import sys

YOUTUBE_API_SERVICE_NAME = "youtube"
YOUTUBE_API_VERSION = "v3"

DEVELOPER_KEY = "{YOUR_DEV_KEY}" 
PLAYLIST_ID = "{YOUTUBE_PLAYLIST_ID}"
CSE_ID = "{CUSTOM_SEARCHENGINE_ID}"

def fetch_all_youtube_videos(playlistId):
	"""
	Fetches a playlist (PLAYLIST_ID) of videos from youtube
	Results added and returned in order.

	Takes:
		playlistId (type string, constant.)
	Returns:
		playlistItem (type dict, variable)
	"""
	print(f"Fetching all videos from playlist: {PLAYLIST_ID}\n")

	try:
		youtube = build(YOUTUBE_API_SERVICE_NAME,
						YOUTUBE_API_VERSION,
						developerKey=DEVELOPER_KEY)
	except HttpError as e:
		sys.exit(handleHTTPerrors(e))
	try:
		res = youtube.playlistItems().list(
		part="snippet",
		playlistId=playlistId,
		maxResults="50" #cant go higher than 50 per page.
		).execute()
	except HttpError as e:
		sys.exit(handleHTTPerrors(e))

	#results are paginated. If length of playlist > 50,
	#nextPageToken present in 'res'
	#get name of of this token
	nextPageToken = res.get('nextPageToken')

	#append 'res' list to include nextPageToken
	while ('nextPageToken' in res):
		nextPage = youtube.playlistItems().list(
		part="snippet",
		playlistId=playlistId,
		maxResults="50",
		pageToken=nextPageToken
		).execute()

		#append the next page results to the original 50 'res'
		res['items'] = res['items'] + nextPage['items']

		#If end of playlist reached
		if 'nextPageToken' not in nextPage:
			#while condition breaks
			res.pop('nextPageToken', None)
		else:
			#not reached the end, get new page token and go again.
			nextPageToken = nextPage['nextPageToken']

	#write all 'res' playlist data to json file in current folder.
	with open(f'{PLAYLIST_ID}_allfavourites.json', 'w', encoding='utf-8') as f:
		json.dump(res, f, ensure_ascii=False, indent=4)

	print(f"Completed. Files written to {PLAYLIST_ID}_allfavourites.json\n")

	return res

def getVideoTitles(videos):
	'''
	All youtube videos have a 'title' key.
	Collect the titles from each favourite, store in a text file.
	Where a video has been deleted or made private,
	state that and print unique videoId.

	Takes:
		videos - json (dictionary) format
	Returns:
		nothing
	'''
	print(f"Creating {PLAYLIST_ID}_alltitles.txt with just video titles.\n")

	df = pd.DataFrame(videos['items'])

	#write favourite titles to a text file.
	with open(f'{PLAYLIST_ID}_alltitles.txt','w',encoding='utf-8') as fout:
		for idx,item in enumerate(df['snippet']):
			#if video has been deleted or made private
			if item['title'] in ('Deleted video','Private video'):

				#get unique video id
				Id = item['resourceId']
				#search for it on google and return first 3 results.
				searchUniqueIds(Id['videoId'], item['position'])

				fout.write(str(item['position']) + ': ' + item['title'] + ' --- ' + Id['videoId'] + '\n')
			else:
				fout.write(str(item['position']) + ': ' + item['title'] + '\n')

def searchUniqueIds(search_term, pos_idx):
	'''
	Where a video has been deleted or made private,
	it is often useful to google search the unique video id.

	Often the entire url with the uniqueId has been pasted and posted
	elsewhere on the internet. This info typically contains the artist
	and song title of the original video. This allows the playlist 
	owner to remember that missing video is.

	Takes:
		search_term - string
		num - 1st n google results for search term
	'''
	service = build("customsearch", "v1", developerKey=DEVELOPER_KEY)

	try:
		#google the youtube ID and return first 3 results.
		google_res = service.cse().list(q=search_term, cx=CSE_ID, num=3).execute()
	except HttpError as e:
		sys.exit(handleHTTPerrors(e))

	with open(f'{PLAYLIST_ID}_searchytcodes.txt','a+',encoding='utf-8') as fout:
		fout.write(str(pos_idx) + ': --- ' + search_term + ' ---\n\n')
		try:
			#get search results
			results = google_res['items']
		except KeyError:
			#if there are no results, write to cmd line and file
			print(f"Sorry, no search results for {search_term}")
			fout.write("--- NO SEARCH RESULTS FOUND ---\n\n\n")
			#break out of searchUniqueIds function.
			return

		#the three pieces of info written to the file
		details = ['link','snippet','title']

		for idx,result in enumerate(results):
			fout.write(f'---Result {idx+1}---\n')
			#for some reason not all results return link, snippet + title
			for i in range(0,len(details)):
				try:
					#try writing them but if they dont exist:
					fout.write(details[i].title() + ' --> ' + result[details[i]] + '\n\n')
				except KeyError:
					#explicitly state in file item doesnt exist.
					fout.write(f'{details[i]} not present in search.\n\n')
		fout.write('\n')

def handleHTTPerrors(err):
	'''
	When an HTTP error is encountered, print the code, reason
	and message. All HTTP error messages are followed by a sys.exit

	Takes:
		err: JSON formatted HTTP error.
		https://developers.google.com/webmaster-tools/search-console-api-original/v3/errors
	'''
	err_code = json.loads(err.content)['error']['code']
	err_reason = json.loads(err.content)['error']['errors'][0]['reason']
	err_message = json.loads(err.content)['error']['errors'][0]['message']

	print(f"\tHTTP Error: {err_code}")
	print(f"\tReason:{err_reason}\n\tMessage: {err_message}\n")

if __name__ == '__main__':

	videos = fetch_all_youtube_videos(PLAYLIST_ID)
	getVideoTitles(videos)