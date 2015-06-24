#!/usr/bin/env python
# -*- coding: utf-8 -*-

# Copyright (c) 2013,2014 Jérémie DECOCK (http://www.jdhp.org)

# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:

# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
 
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
# THE SOFTWARE.

# TODO
# - script d'installation (à executer en tant que root)
# - vérifier la présence des executables, afficher le message d'erreur des processus fils (ie ce qu'ils envoient sur stderr)
# - l'affichage dans un flux à part, le processus/thread maitre ne gère que le timer (sleep(duration) puis killall)
# - flux RSS, etc. dans un thread à part pour ne pas bloquer l'affichage (de l'horloge notamment)
# - paquet Debian
# - séparer l'application en plusieurs modules/bibliothèques indépendants (pour permettre d'activer/desactiver certains composants (affichage, ...), pour rendre l'appli plus robuste (si un composant ne marche pas, le reste tourne quand même) et pour faire une application dbus pour le prochain bus à Orsay par exemple)
# - vidéos (CNNi, BBC world, ...) / podcast vidéos
# + gestion des exceptions (sur les flux RSS, twitter, ... notamment)
# * vérifier toutes les 10 mn si omxplayer est vivant et si du son sort de la carte son -> si non, arrêter vérification et jouer une playlist mp3
# * intégration omxplayer (url dans un fichier .ini, .xspf, .pls ou .m3u ?), kill 0...
# * intégration screen_on/screen_off
# * heure du prochain bus
# * infotrafic transilien en temps réel
# * NTP...
# * calendrier google -> créer un compte pour le réveil + afficher les évènements sur le réveil (attention à ne pas commiter les logins/pwd dans le référentiel git !!!)
# + améliorer l'affichage... (+ d'infos pour la météo: humidité, sunset/sunrise, vent, etc.)
# + changer la police -> style google glass (chercher de l'inspiration sur http://www.google.com/fonts)
# + sonde luminosité, température, bruit, mouvements, ... -> enregistrer dans un fichier (et l'exploiter plus tard) -> codé dans une librarie/projet à part
# - download + play podcasts
# - manette pour allumer/éteindre/changer de station/... (+ fichier de conf .ini)
# - fichiers .ini (nom+url+logo des stations radio, timetable bus, liste des villes pour la météo, liste des flux rss, ...)
# - bypass cron -> met le programme en veille, programme heures de réveil (fichier .ini ?), etc.
# - exploiter les statistiques transilien pour calculer une estimation/prévision du temps de parcours (stats des retards, etc.) et de la fréquentation (ie. du nombre de passagers moy par rame -> code couleur: rouge, orange, vert)
# - serveur X minimaliste (ou pas de serveur X du tout)
# - heures de réveil, stations, durées, etc. programmables via une page web (et application android) -> utiliser Twisted pour le serveur web
# - trouver une meilleur API pour la météo (google ?)
# - twitter (transilien) ?

import argparse
import datetime
import sys
import os

import pygame
import feedparser

CONFIG_DIR="/etc/piclockradio"

###############################################################################

def get_web_radio_dict():
    """Parse web radios"""

    filename = os.path.join(CONFIG_DIR, "radio", "web_radios.txt")

    if not os.path.isfile(filename):
        print "ERROR: can't find data {0}".format(filename)
        sys.exit(1)

    if os.path.splitext(filename)[1] == ".gz":
        # FILENAME IS COMPRESSED
        fd = gzip.open(filename, "rU")
    else:
        # FILENAME ISN'T COMPRESSED
        fd = open(filename, "rU")

    ## PRETTY NAME
    #pretty_name = fd.readline().strip()
    #if pretty_name == "":
    #    pretty_name = filename

    # LOGO
    # TODO

    # WEBRADIOS
    web_radio_dict = {}
    for line in fd.readlines():
        item = line.split()
        if len(item) == 2:
            web_radio_dict[item[0]] = item[1].strip()
    fd.close()

    return web_radio_dict

###############################################################################

class Timetable:
    def __init__(self, filename):
        """Parse timetables"""

        if not os.path.isfile(filename):
            print "ERROR: can't find data {0}".format(filename)
            sys.exit(1)

        if os.path.splitext(filename)[1] == ".gz":
            # FILENAME IS COMPRESSED
            fd = gzip.open(filename, "rU")
        else:
            # FILENAME ISN'T COMPRESSED
            fd = open(filename, "rU")

        # PRETTY NAME
        self.pretty_name = fd.readline().strip()
        if self.pretty_name == "":
            self.pretty_name = filename

        # THRESHOLDS
        # TODO
        self.min_delta = 0

        # TIMETABLE
        self.timetable_list = []
        for line in fd.readlines():
            item = line.split(':')
            if len(item) == 2:
                #self.timetable_list.append(datetime.time(hour=int(item[0]), minute=int(item[1])))
                self.timetable_list.append(int(item[0]) * 60 + int(item[1]))
        fd.close()

        self.timetable_list.sort()       # TODO: test if sort is working


def get_next_time(timetable):
    now = datetime.datetime.now()
    now = now.hour * 60 + now.minute

    deltatime = [t - now for t in timetable.timetable_list]
    positive_deltatime = [dt for dt in deltatime if dt >= timetable.min_delta]

    if len(positive_deltatime) >= 2:
        next_time = positive_deltatime[:2]
    elif len(positive_deltatime) == 1:
        next_time = positive_deltatime.append(deltatime[0] + (24 * 60))
    else:
        if len(deltatime) >= 2:
            next_time = [t + (24 * 60) for t in deltatime[:2]]
        else:
            next_time = [deltatime[0] + (24 * 60), deltatime[0] + (48 * 60)]

    return next_time


def get_next_time_str(timetable):
    next_bus = [divmod(t, 60) for t in get_next_time(timetable)]
    next_bus_str = timetable.pretty_name + " : "
    if next_bus is not None:
        if next_bus[0][0] > 0:
            next_bus_str += str(next_bus[0][0]) + "h"
        #threshold : warn, hurry, min
        next_bus_str += str(next_bus[0][1]) + "min  "

        if next_bus[1][0] > 0:
            next_bus_str += str(next_bus[1][0]) + "h"
        #threshold : warn, hurry, min
        next_bus_str += str(next_bus[1][1]) + "min"
    else:
        next_bus_str += "-"
    return next_bus_str


###############################################################################

YAHOO_CITY_CODES_DICT = {'cergy': '583634', 'orsay':'55863553', 'paris': '615702', 'survilliers': '627883'}
DISPLAY_WEATHER = True
DISPLAY_RSS_RER = True

def weather(city):
    weather_str_tuple = ("-", "")

    if DISPLAY_WEATHER and (city in YAHOO_CITY_CODES_DICT):
        rss_url = "http://weather.yahooapis.com/forecastrss?w=" + YAHOO_CITY_CODES_DICT[city] + "&u=c"
        feed_dict = feedparser.parse(rss_url)

        location_dict   = feed_dict.feed.yweather_location   # contains the locations dictionary
        atmosphere_dict = feed_dict.feed.yweather_atmosphere # contains the atmospheric conditions dictionary (pressure/humidity)
        astronomy_dict  = feed_dict.feed.yweather_astronomy  # contains the astronomy dictionary (sunset/sunrise hours)
        summary_list = feed_dict.entries[0].summary.splitlines()

        city = location_dict['city']
        humidity = atmosphere_dict['humidity']
        pressure = atmosphere_dict['pressure']
        sunrise = astronomy_dict['sunrise']
        sunset = astronomy_dict['sunset']
        weather_pic = summary_list[0].split("<br />")[0].split("\"")[1]
        current_conditions = summary_list[2].split("<br />")[0][:-2]
        current_conditions, current_temp = current_conditions.split(",")
        current_conditions = current_conditions.strip()
        current_temp = current_temp.strip()
        today_forecast, today_forecast_temp = summary_list[4].split("<br />")[0].split(" - ")[1].split(". ")
        today_forecast_temp_list = today_forecast_temp.split()
        today_forecast_temp_max = today_forecast_temp_list[1]
        today_forecast_temp_min = today_forecast_temp_list[3]

        #print city
        #print "humidity", humidity
        #print "pressure", pressure
        #print "sunrise", sunrise
        #print "sunset", sunset
        #print weather_pic
        #print current_conditions
        #print today_forecast, today_forecast_temp

        current_conditions_str = current_conditions.lower() + " (" + current_temp + u"°C)"
        today_forecast_str = today_forecast.lower() + " (" + today_forecast_temp_min + u"°C / " + today_forecast_temp_max + u"°C)"

        weather_str_tuple = (current_conditions_str, today_forecast_str)

    return weather_str_tuple

def rss_rer(line):
    rss_str = ""

    line = line.upper()
    lines = ['A', 'B', 'C', 'D']
    if DISPLAY_RSS_RER and (line in lines):
        rss_url = "http://www.transilien.com/flux/rss/traficLigne?codeLigne=" + line
        feed_dict = feedparser.parse(rss_url)
        #entries_set = {(entry['published'], entry['title']) for entry in feed_dict.entries}
        entries_set = {entry['title'] for entry in feed_dict.entries}

        for entry in entries_set:
            rss_str += entry      # TODO

    if rss_str == "":
        rss_str = "RER " + line + " : -"

    return rss_str

###############################################################################

def screen_on():

    pid = os.fork()

    if pid==0:
        # CHILD PROCESS
        try:
            os.execlp('screen_on', 'screen_on')
        except OSError as e:
            print "ERROR: can't turn on the screen"
        sys.exit(1)

    # PARENT PROCESS
    print "screen_on (PID {})".format(pid)
    (wait_pid, status) = os.wait()        # wait the child process
    if os.WIFEXITED(status):
        print "{} EXITED: {}".format(wait_pid, os.WEXITSTATUS(status))
    elif os.WIFSIGNALED(status):
        print "{} SIGNALED: {}".format(wait_pid, os.WTERMSIG(status))

###############################################################################

def screen_off():

    pid = os.fork()

    if pid==0:
        # CHILD PROCESS
        try:
            os.execlp('screen_off', 'screen_off')
        except OSError as e:
            print "ERROR: can't turn off the screen"
        sys.exit(1)

    # PARENT PROCESS
    print "screen_off (PID {})".format(pid)
    (wait_pid, status) = os.wait()        # wait the child process
    if os.WIFEXITED(status):
        print "{} EXITED: {}".format(wait_pid, os.WEXITSTATUS(status))
    elif os.WIFSIGNALED(status):
        print "{} SIGNALED: {}".format(wait_pid, os.WTERMSIG(status))

###############################################################################

def play_radio(radio):
    web_radio_dict = get_web_radio_dict()
    url = web_radio_dict[radio]

    pid = os.fork()

    if pid==0:
        # CHILD PROCESS
        try:
            os.execlp('omxplayer', 'omxplayer', url)
        except OSError as e:
            print "ERROR: can't launch omxplayer"
        sys.exit(1)

    # PARENT PROCESS
    print "omxplayer (PID {})".format(pid)
    return pid

###############################################################################

def display(duration=None):

    # INIT DISPLAY ############################################################

    # Windows : windib, directx
    # Unix : x11, dga, fbcon, directfb, ggi, vgl, svgalib, aalib
    #os.environ["SDL_VIDEODRIVER"] = "dummy"  # use svga, framebuffer, ... instead X11

    pygame.init()

    modes_list = pygame.display.list_modes()
    screen = pygame.display.set_mode(modes_list[0], pygame.FULLSCREEN)   # the highest resolution with fullscreen
    #screen = pygame.display.set_mode(modes_list[-2])                     # the lowest resolution

    background_color = (255, 255, 255)

    font_name = pygame.font.get_default_font()
    font_size = 46
    text_font = pygame.font.Font(font_name, font_size)

    # INIT EVENTS #############################################################

    CLOCK_EVENT = pygame.USEREVENT+1
    WEATHER_EVENT = pygame.USEREVENT+2
    RSS_RER_EVENT = pygame.USEREVENT+3
    NEXT_BUS_EVENT = pygame.USEREVENT+4

    CLOCK_INTERVAL_MS = 1000 # ms
    WEATHER_INTERVAL_MS = 15 * 60 * 1000 # ms
    RSS_RER_INTERVAL_MS = 10 * 60 * 1000 # ms
    NEXT_BUS_INTERVAL_MS = 1000 # ms

    pygame.time.set_timer(CLOCK_EVENT, CLOCK_INTERVAL_MS)
    pygame.time.set_timer(WEATHER_EVENT, WEATHER_INTERVAL_MS)
    pygame.time.set_timer(RSS_RER_EVENT, RSS_RER_INTERVAL_MS)
    pygame.time.set_timer(NEXT_BUS_EVENT, NEXT_BUS_INTERVAL_MS)

    # Add some userevents at the end of the event queue to display the associated informations at startup
    pygame.event.post(pygame.event.Event(CLOCK_EVENT))
    pygame.event.post(pygame.event.Event(WEATHER_EVENT))
    pygame.event.post(pygame.event.Event(RSS_RER_EVENT))
    pygame.event.post(pygame.event.Event(NEXT_BUS_EVENT))

    # DISPLAY LOOP ############################################################

    timetable_r2_fosses_mairie = Timetable(os.path.join(CONFIG_DIR, "transportation", "r2_fosses_mairie.txt"))
    timetable_9501_fosses_centre_ville = Timetable(os.path.join(CONFIG_DIR, "transportation", "9501_fosses_centre_ville.txt"))
    timetable_9501_roissy_centre_ville = Timetable(os.path.join(CONFIG_DIR, "transportation", "9501_roissy_centre_ville.txt"))

    date_str = ""
    time_str = ""
    weather_str1 = ""
    weather_str2 = ""
    weather_str3 = "" 
    rss_rerb_str = ""
    rss_rerd_str = ""
    next_bus_r2_fosses_mairie_str = ""
    next_bus_9501_fosses_centre_ville_str = ""
    next_bus_9501_roissy_centre_ville_str = ""

    quit = False
    while ((duration is None) or (pygame.time.get_ticks() < 1000 * duration)) and (not quit):
        #pygame.time.wait(100)                # wait 100ms to unstress the CPU
        #for event in pygame.event.get():     # check events

        # WAIT AND GET EVENTS
        event = pygame.event.wait()
        if event.type == pygame.QUIT or (event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE):
            # QUIT
            pygame.time.set_timer(CLOCK_EVENT, 0)     # RESET CLOCK_EVENT
            pygame.time.set_timer(WEATHER_EVENT, 0)   # RESET WEATHER_EVENT
            pygame.time.set_timer(RSS_RER_EVENT, 0)   # RESET RSS_RER_EVENT
            pygame.time.set_timer(NEXT_BUS_EVENT, 0)  # RESET NEXT_BUS_EVENT
            quit = True
        elif event.type == CLOCK_EVENT:
            # UPDATE THE CURRENT DATETIME
            dt = datetime.datetime.now()
            date_str = dt.strftime("%A, %B %d %Y")
            time_str = dt.strftime("%H:%M:%S")
        elif event.type == WEATHER_EVENT:
            # UPDATE THE CURRENT WEATHER
            weather_str1 = "Paris : "
            weather_str2, weather_str3 = weather("paris")
        elif event.type == RSS_RER_EVENT:
            # UPDATE THE CURRENT RSS (RER) FEED
            rss_rerb_str = rss_rer("B")
            rss_rerd_str = rss_rer("D")
        elif event.type == NEXT_BUS_EVENT:
            # UPDATE THE CURRENT RSS (RER) FEED
            next_bus_r2_fosses_mairie_str = get_next_time_str(timetable_r2_fosses_mairie)
            next_bus_9501_fosses_centre_ville_str = get_next_time_str(timetable_9501_fosses_centre_ville)
            next_bus_9501_roissy_centre_ville_str = get_next_time_str(timetable_9501_roissy_centre_ville)


        # UPDATE THE DISPLAY
        screen.fill(background_color)

        # MAKE CLOCK SURFACES
        date_surface = text_font.render(date_str, True, (0,0,0))
        time_surface = text_font.render(time_str, True, (0,0,0))

        # MAKE WEATHER SURFACES
        weather_surface1 = text_font.render(weather_str1, True, (0,0,0))
        weather_surface2 = text_font.render(weather_str2, True, (0,0,0))
        weather_surface3 = text_font.render(weather_str3, True, (0,0,0))

        # MAKE RSS (RER) SURFACES
        rss_rerb_surface = text_font.render(rss_rerb_str, True, (0,0,0))
        rss_rerd_surface = text_font.render(rss_rerd_str, True, (0,0,0))

        # MAKE NEXT BUS SURFACES
        next_bus_r2_fosses_mairie_surface = text_font.render(next_bus_r2_fosses_mairie_str, True, (0,0,0))
        next_bus_9501_fosses_centre_ville_surface = text_font.render(next_bus_9501_fosses_centre_ville_str, True, (0,0,0))
        next_bus_9501_roissy_centre_ville_surface = text_font.render(next_bus_9501_roissy_centre_ville_str, True, (0,0,0))

        # DISLPAY SURFACES
        # TODO: use the location of the previous surface to compute surface positions...
        screen.blit(date_surface, (10, 10))
        screen.blit(time_surface, (10, 10 + date_surface.get_height() + 4))

        screen.blit(weather_surface1, (10, 10 + date_surface.get_height() + 4 + time_surface.get_height() + 30))
        screen.blit(weather_surface2, (10 + weather_surface1.get_width(), 10 + date_surface.get_height() + 4 + time_surface.get_height() + 30))
        screen.blit(weather_surface3, (10 + weather_surface1.get_width(), 10 + date_surface.get_height() + 4 + time_surface.get_height() + 30 + weather_surface2.get_height() + 4))

        screen.blit(rss_rerb_surface, (10, 10 + date_surface.get_height() + 4 + time_surface.get_height() + 30 + weather_surface2.get_height() + 4 + weather_surface3.get_height() + 30))
        screen.blit(rss_rerd_surface, (10, 10 + date_surface.get_height() + 4 + time_surface.get_height() + 30 + weather_surface2.get_height() + 4 + weather_surface3.get_height() + 30 + rss_rerb_surface.get_height() + 4))

        screen.blit(next_bus_r2_fosses_mairie_surface,         (10, 10 + date_surface.get_height() + 4 + time_surface.get_height() + 30 + weather_surface2.get_height() + 4 + weather_surface3.get_height() + 30 + rss_rerb_surface.get_height() + 4 + rss_rerd_surface.get_height() + 30))
        screen.blit(next_bus_9501_fosses_centre_ville_surface, (10, 10 + date_surface.get_height() + 4 + time_surface.get_height() + 30 + weather_surface2.get_height() + 4 + weather_surface3.get_height() + 30 + rss_rerb_surface.get_height() + 4 + rss_rerd_surface.get_height() + 30 + next_bus_r2_fosses_mairie_surface.get_height() + 4))
        screen.blit(next_bus_9501_roissy_centre_ville_surface, (10, 10 + date_surface.get_height() + 4 + time_surface.get_height() + 30 + weather_surface2.get_height() + 4 + weather_surface3.get_height() + 30 + rss_rerb_surface.get_height() + 4 + rss_rerd_surface.get_height() + 30 + next_bus_r2_fosses_mairie_surface.get_height() + 4 + next_bus_9501_fosses_centre_ville_surface.get_height() + 4))

        pygame.display.flip()

    pygame.time.set_timer(CLOCK_EVENT, 0)     # RESET CLOCK_EVENT
    pygame.time.set_timer(WEATHER_EVENT, 0)   # RESET WEATHER_EVENT
    pygame.time.set_timer(RSS_RER_EVENT, 0)   # RESET RSS_RER_EVENT
    pygame.time.set_timer(NEXT_BUS_EVENT, 0)  # RESET NEXT_BUS_EVENT

    pygame.quit()   # UNINITIALIZE ALL PYGAME MODULES


###############################################################################

def main():

    if not os.path.isdir(CONFIG_DIR):
        print "ERROR: can't find {0}".format(CONFIG_DIR)
        sys.exit(1)

    # PARSE ARGUMENTS #########################################################

    parser = argparse.ArgumentParser(description='A smart alarm for Raspberry Pi.')

    parser.add_argument("--radio", "-r",  help="the name of the radio to play", metavar="STRING")
    parser.add_argument("--duration", "-d",  help="the number of seconds before the alarm stop", metavar="INTEGER", type=int)
    #parser.add_argument("--screen", "-s", help="switch on the screen saver", action="store_true")

    args = parser.parse_args()

    # LAUNCH OMXPLAYER ########################################################

    try:
        radio_pid = play_radio(args.radio)
    except:
        print "ERROR: radio failed."

    # TURN SCREEN ON ##########################################################

    try:
        screen_on()
    except:
        print "ERROR: screen_on failed."

    # DISPLAY #################################################################

    try:
        display(args.duration)
    except:
        print "ERROR: display failed."

    # TURN SCREEN OFF #########################################################

    try:
        screen_off()
    except:
        print "ERROR: screen_off failed."

    # KILL ALL ################################################################

    #os.kill(radio_pid, 15)
    os.kill(0, 15)

if __name__ == '__main__':
    main()

