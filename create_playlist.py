import json
import requests
from secrets import spotify_user_id, spotify_token

import os

import google_auth_oauthlib.flow
import googleapiclient.discovery
import googleapiclient.errors
import youtube_dl

#copied
# from exceptions import ResponseException

class CreatePlaylist:

    def __init__(self):
        self.user_id = spotify_user_id
        self.spotify_token = spotify_token
        self.youtube_client = self.get_youtube_cient()
        self.all_song_information = {}

    # step 1: log into YouTube
    def get_youtube_client(self):
        # Disable OAuthlib's HTTPS verification when running locally.
        # *DO NOT* leave this option enabled in production.
        os.environ["OAUTHLIB_INSECURE_TRANSPORT"] = "1"

        api_service_name = "youtube"
        api_version = "v3"
        client_secrets_file = "YOUR_CLIENT_SECRET_FILE.json"

        # Get credentials and create an API client
        scopes = ["https://www.googleapis.com/auth/youtube.readonly"]
        flow = google_auth_oauthlib.flow.InstalledAppFlow.from_client_secrets_file(
            client_secrets_file, scopes)
        credentials = flow.run_console()
        youtube_client = googleapiclient.discovery.build(
            api_service_name, api_version, credentials=credentials)
        return youtube_client


    # step 2: grab our liked songs
    def get_liked_videos(self):
        request = self.youtube_client.videos().list(
            part="snippet,contentDetails,statistics",
            myRating='like'
        )
        response = request.execute()

        #collect each video and get important information
        for i in response['items']:
            video_title = item['snippet']['title']
            youtube_url = "https://www.youtube.com/watch?v={}".format(item['id'])

            #use youtube_dl to collect artist name and song name
            video = youtube_dl.YouTubeDL({}).extract_info(youtube_url, download=False)

            song_name = video['track']
            artist = video['artist']

            if song_name is not None and artist is not None:
            #save all important info
                self.all_song_info[video_title]={
                    'youtube_url':youtube_url,
                    'song_name':song_name,
                    'artist':artist,

                    # get uri, easy to add to a playlist
                    'spotify_uri':self.get_spotify_uri(song_name, artist)
                }

    # step 3: create a new playlist
    def create_playlist(self):
        request_body = json.dumps({
            "name": "YouTube liked videos",
            "description": "All songs from YouTube",
            "public": True
        })

        query = 'https://api.spotify.com/v1/users/{user_id}/playlists'.format(self.user_id)
        response = requests.post(
            query,
            data=request_body,
            headers={
                "Content-Type":'application/json',
                "Authorization":"Bearer {}".format(spotify_token)
            }
        )
        response_json = response.json()

        #playlist_id
        return response_json['id']

    # step 4: find the song on Spotify
    def get_spotify_uri(self, song_name, artist):
        query = 'https://api.spotify.com/v1/search?query=track%3A{}+artist%3A{}&type=track&offset=0&limit=20'.format(
            song_name,
            artist
        )
        response = requests.get(
            query,
            headers={
                "Content-Type": 'application/json',
                "Authorization": "Bearer {}".format(self.spotify_token)
            }
        )
        response_json = response.json()
        songs = response_json['tracks']['items']

        #only use the first song
        uri = songs[0]['uri']

        return uri

    # step 5: add it to a Spotify playlist
    def add_song_to_playlist(self):
        #populate our songs dictionary
        self.get_liked_videos()

        #collect all uris
        uris = [info["spotify_uri"] for song,info in self.all_song_info.items()]

            # uris.append(info['spotify_uri'])

        #create a new playlist
        playlist_id = self.create_playlist()

        #add all songs to a playlist
        request_data = json.dumps(uris)

        query = 'https://api.spotify.com/v1/playlists/{}/tracks'.format(playlist_id)

        response = requests.post(
            query,
            data = request_data,
            headers={
                "Content-Type": 'application/json',
                "Authorization": "Bearer {}".format(self.spotify_token)
            }
        )


        # check for valid response status
        if response.status_code != 200:
            raise ResponseException(response.status_code)



        response_json = response.json()
        return response_json
