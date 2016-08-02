#!/usr/bin/python

import pygal
import pygn
import pylast

import sys

import json

import time

settings = {
    'filter': True,
    # 'filter': False,
    'filter_threshold': 15,
    'metadata_cache': "metadata.json",
    'normalize': True,
    # 'normalize': False,
    'only_main_mood': False,
    'output': 'out.svg',
    'use_weight': True,
    'weeks_to_fetch': 60
}

LASTFM_USERNAME = "empty91"

print "Reading secrets...",
secrets = json.load(open("SECRETS.json", "r"))

LASTFM_API_KEY = secrets["LASTFM_API_KEY"]
LASTFM_SECRET = secrets["LASTFM_SECRET"]
GN_CLIENT_ID = secrets["GN_CLIENT_ID"]
GN_USER_ID = secrets["GN_USER_ID"]
print "OK"


if len(sys.argv) == 2:
  LASTFM_USERNAME = sys.argv[1]
  settings['output'] = LASTFM_USERNAME + ".svg"
  print "Working on", LASTFM_USERNAME
  

def open_cache(name):
    cache = {}
    try:
        cache = json.load(open(name, "r"))
    except ValueError:
        pass
    except IOError:
        pass

    return cache


def dump_cache(obj, name):
    json.dump(obj, open(name, "w"))


def song_to_key(song_item):
    return "%s - %s" % (song_item.artist.name, song_item.title)


lastfm_api = pylast.LastFMNetwork(api_key=LASTFM_API_KEY, api_secret=LASTFM_SECRET)
lastfm_user = lastfm_api.get_user(LASTFM_USERNAME)

weekly_chart_dates = lastfm_user.get_weekly_chart_dates()
weekly_chart_dates = weekly_chart_dates[-settings['weeks_to_fetch']:]
weekcharts = [lastfm_user.get_weekly_track_charts(from_date=d[0], to_date=d[1]) for d in weekly_chart_dates]

tracks = {}
for chart in weekcharts:
    for song in chart:
        item = song.item
        tracks[song_to_key(item)] = item


metadata = open_cache(settings["metadata_cache"])
for track in tracks.values():
    k = song_to_key(track)

    if not metadata.has_key(k):
        print "Fetching '%s'..." % (k)

        m = pygn.search(clientID=GN_CLIENT_ID,
                        userID=GN_USER_ID,
                        artist=track.artist.name,
                        #album=track.a,
                        track=track.title)
        metadata[k] = m
dump_cache(metadata, settings["metadata_cache"])

if settings['only_main_mood']:
    for k in metadata:
        if '1' in metadata[k]['mood'].keys():
            metadata[k]['mood'] = {'1': metadata[k]['mood']['1']}

song_moods_dict = {}
for song, mdata in metadata.items():
    song_moods_dict[song] = mdata['mood']


history = []
for chart in weekcharts:
    week = {}

    for song in chart:
        artist = song.item.artist.name
        title = song.item.title

        counter = 1
        if settings['use_weight']:
            counter = song.weight

        song_moods = song_moods_dict[song_to_key(song.item)]
        for mood in song_moods.values():
            m = mood['TEXT']

            if m in week.keys():
                week[m] += counter
            else:
                week[m] = counter

    history.append(week)


moods_list = []
for week in history:

    for mood_name in week:

        if not mood_name in moods_list:
            moods_list.append(mood_name)


import datetime


def extract_starting_date(x):
    return datetime.datetime.fromtimestamp(int(x[0]))
dates = map(extract_starting_date, weekly_chart_dates)

datey = pygal.StackedLine(interpolate='cubic',
                          fill=True,
                          print_values=False,
                          # show_legend=False,
                          show_dots=False,
                          width=800,
                          height=480,
                          x_label_rotation=20)

final_moods = []
final_moods_y = []
for mood in moods_list:
    yy = []

    for week, date in zip(history, dates):
        if mood in week.keys():
            yy.append(week[mood])
            #yy.append((date, week[mood]))
        else:
            yy.append(0)
            #yy.append((date, 0))

    if settings['filter'] and max(yy) < settings['filter_threshold']:
        continue
    else:
        final_moods.append(mood)
        final_moods_y.append(yy)
        #datey.add(mood, yy)

#print final_moods_y
if settings['normalize']:
    for i, y_values in enumerate(zip(*final_moods_y)):
        #print y_values
        ss = sum(y_values)
        if ss < 1:
            ss = 1
            print "Sum = 0... :/"

        for j in xrange(len(y_values)):
            final_moods_y[j][i] /= float(ss)

for mood, yy in zip(final_moods, final_moods_y):
    datey.add(mood, yy)
datey.render_to_file("out/" + settings["output"])
