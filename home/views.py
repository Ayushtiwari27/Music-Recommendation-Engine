from django.shortcuts import render, redirect
from django.contrib.auth.models import User
from django.contrib.auth import logout, authenticate, login
from django.contrib import messages
from django.http import HttpResponse, Http404
from django.shortcuts import render
from .models import *
from django.views.decorators.csrf import csrf_exempt
from django.core.exceptions import BadRequest
import numpy as np
import pandas as pd
import spotipy
import os
import streamlit as st
from collections import defaultdict
from scipy.spatial.distance import cdist
from spotipy.oauth2 import SpotifyClientCredentials
from collections import defaultdict
from sklearn.cluster import KMeans
from sklearn.preprocessing import StandardScaler
from sklearn.pipeline import Pipeline

# A function to upload name,year and artists's name all the songs from the dataset to the database.
def nice(request):
    data = pd.read_csv('Dataset/Data.csv.zip')
    data=data.values.tolist()
    indata=[]
    for i in data:
        indata.append([i[14],i[1],i[3]])
    
    for i in indata:
        temp=songs(name=i[0],year=i[1],artists=i[2])
        temp.save()    
    # data=songs.objects.all()          # Incase one needs to delete the database comment above lines and 
    # data.delete()                     # uncomment these two lines and run the code.
    return HttpResponse({"fdsa"})


# home function checks if the user is logged in. if the user is logged in, then he is allowed 
# to use the website otherwise it redirects to login page.
def home(request):
    print(request.user)
    if request.user.is_anonymous:
        return redirect("/login") 
    data1=songs.objects.values().order_by("?")
    data1=list(data1)
    #data2 = random.sample(data1, 100)
    data2=data1[0:100]
    params={"nice":data2}
    return render(request, 'welcome.html',params)


# loginuser function allows the user to login to their account and 
# if the user's entered credentials are not found in the database then,
# it opens the register page for the user to register first.
def loginUser(request):
    if request.method=="POST":
        username = request.POST['username']
        password = request.POST['password']
        print(username, password)

        # check if user has entered correct credentials
        user = authenticate(username=username, password=password)

        if user is not None:
            # A backend authenticated the credentials
            login(request, user)
            data1=songs.objects.values().order_by("?")
            data1=list(data1)
            data2=data1[0:100]
            params={"nice":data2}
            return render(request, 'welcome.html',params)

        else:
            # No backend authenticated the credentials
            messages.success(request, 'No Profile Found! Please register.')
            return render(request, 'register.html')

    return render(request, 'login.html')


# logoutUser function allows user to logout from the website and redirects the user to login page.
def logoutUser(request):
    logout(request)
    return redirect("/login")


# registeruser function takes credentials of the user and makes a new account of the user and
# redirects it to the login page to continue.
def registeruser(request):
    if request.method=="POST":
        # taking details entered in register.html
        username = request.POST['username']
        password = request.POST['password']
        email = request.POST['email']
        name = request.POST['name']
        
        # creating a new user with above details
        myuser = User.objects.create_user(username, email, password)
        myuser.first_name = name
        myuser.save()
        # after successful creation of user display the message
        messages.success(request, 'Profile Created! Please Login to continue. ')
        return redirect("/login")
    else:
        return render(request, 'register.html')

# Undermentioned function reads the dataset and using K-Means algorithm finds the best reccommendation
@st.cache(allow_output_mutation=True)
def func(name,year):
    spotify_data = pd.read_csv('Dataset/Data.csv.zip')
    spotify_data.head(10)

    os.environ['SPOTIPY_CLIENT_ID'] = '' #write client ID from Spotify API
    os.environ['SPOTIPY_CLIENT_SECRET'] = '' #write client Secret from Spotify API

    sp = spotipy.Spotify(auth_manager=SpotifyClientCredentials(client_id=os.environ['SPOTIPY_CLIENT_ID'],client_secret=os.environ['SPOTIPY_CLIENT_SECRET']))

    song_cluster_pipeline = Pipeline([('scaler', StandardScaler()), 
                                    ('kmeans', KMeans(n_clusters=20, 
                                    verbose=2))], verbose=True)
    X = spotify_data.select_dtypes(np.number)
    number_cols = list(X.columns)
    song_cluster_pipeline.fit(X.values)
    song_cluster_labels = song_cluster_pipeline.predict(X)
    spotify_data['cluster_label'] = song_cluster_labels

    def find_song(name, year):
        
        song_data = defaultdict()
        results = sp.search(q= 'track: {} year: {}'.format(name, year), limit=1)
        if results['tracks']['items'] == []:
            return None
        
        results = results['tracks']['items'][0]

        track_id = results['id']
        audio_features = sp.audio_features(track_id)[0]
        
        song_data['name'] = [name]
        song_data['year'] = [year]
        song_data['explicit'] = [int(results['explicit'])]
        song_data['duration_ms'] = [results['duration_ms']]
        song_data['popularity'] = [results['popularity']]
        
        for key, value in audio_features.items():
            song_data[key] = value
        
        return pd.DataFrame(song_data)

    number_cols = ['valence', 'year', 'acousticness', 'danceability', 'duration_ms', 'energy', 'explicit',
    'instrumentalness', 'key', 'liveness', 'loudness', 'mode', 'popularity', 'speechiness', 'tempo']

    def get_song_data(song, spotify_data):
        
        try:
            song_data = spotify_data[(spotify_data['name'] == song['name']) & (spotify_data['year'] == song['year'])].iloc[0]
            return song_data
        
        except IndexError:
            return find_song(song['name'], song['year'])
            

    def get_mean_vector(song_list, spotify_data):
        
        song_vectors = []
        
        for song in song_list:
            song_data = get_song_data(song, spotify_data)
            if song_data is None:
                print('Warning: {} does not exist in Spotify or in database'.format(song['name']))
                continue
            song_vector = song_data[number_cols].values
            song_vectors.append(song_vector)  
        
        song_matrix = np.array(list(song_vectors))
        return np.mean(song_matrix, axis=0)

    def flatten_dict_list(dict_list):
        
        flattened_dict = defaultdict()
        for key in dict_list[0].keys():
            flattened_dict[key] = []
        
        for dictionary in dict_list:
            for key, value in dictionary.items():
                flattened_dict[key].append(value)
                
        return flattened_dict
            

    def recommend_songs( song_list, spotify_data, n_songs=11):
        
        metadata_cols = ['name', 'year', 'artists']
        song_dict = flatten_dict_list(song_list)
        
        song_center = get_mean_vector(song_list, spotify_data)
        scaler = song_cluster_pipeline.steps[0][1]
        scaled_data = scaler.transform(spotify_data[number_cols])
        scaled_song_center = scaler.transform(song_center.reshape(1, -1))
        distances = cdist(scaled_song_center, scaled_data, 'cosine')
        index = list(np.argsort(distances)[:, :n_songs][0])
        
        rec_songs = spotify_data.iloc[index]
        rec_songs = rec_songs[~rec_songs['name'].isin(song_dict['name'])]
        return rec_songs[metadata_cols].to_dict(orient='records') 

    return recommend_songs([{'name': name, 'year':year}],  spotify_data)

# For more information of the above function got /Algo/test.py

 
# Function below executes the above mentioned code to show the recommendation
# based on the above algorithm
@csrf_exempt
def recommend_songs1(request,myid):
    try:
        name = myid      
        data1=songs.objects.values().filter(name=name)
        data1=list(data1)
        data2=func(data1[0]['name'],data1[0]['year'])
        inidata=[data1[0]['name'],data1[0]['year'],data1[0]['artists']]
        params = {'hello': [inidata,data2]}
        
        return render(request, 'index.html', params)
    except songs.DoesNotExist:
        raise Http404
    except Exception as e:
        raise BadRequest()
