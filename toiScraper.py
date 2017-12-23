#!/usr/bin/python

from bs4 import BeautifulSoup
from decimal import *
from pushbullet import Pushbullet, InvalidKeyError

import urllib
import os
import sys
import configparser
import pickle
import re

# user defined vars
pushbulletAPI = ""
langs = ["tamil", "telugu", "malayalam", "hindi"]
toiLink = "https://timesofindia.indiatimes.com/entertainment/"
ratingThreshold = 3.5

# global vars
newToiMovies = []

class ToiMovies(object):
	def __init__(self):
		self.movieName = ""	  # (string) title of movie
		self.movieRating = ""	  # (string) example: 3.5 / 5
		self.movieAbsRating = ""  # (decimal) absolute rating for movie; example: 3.5
		self.movieLink = ""	  # (string) link to movie in TOI
	def __hash__(self):
		return hash(self.movieName + self.movieRating)
	def __eq__(self, other):
		return (isinstance(other, self.__class__) and getattr(other, 'movieName') == self.movieName and getattr(other, 'movieRating') == self.movieRating)
	def addMovie(self, movieName, movieRating, movieLink):
		# validation
		if (movieName is None) or (movieRating is None) or (movieLink is None):
			return
		self.movieName = movieName.encode('utf-8')
		self.movieRating = str(movieRating)
		self.movieLink = toiLink[:-15] + str(movieLink)
	def computeAbsRating(self):
		stringAbsRating = re.search("\d(\.\d)?", self.movieRating).group()
		self.movieAbsRating = Decimal(stringAbsRating)
		if self.movieAbsRating >= ratingThreshold:
			return True
		else:
			return False

def processURL(link):
	print "Processing URL : " + link;
	url = urllib.urlopen(link).read()
	soup = BeautifulSoup(url, "lxml")

	movies = soup.select("h2 a")
	critic_ratings = soup.select(".mrB10 > .ratingMovie")
	movieLink = soup.select(".mr_listing_right > h2 > a")

	if len(movies) == len(critic_ratings):
		for i in range(0, len(movies)):
			movieObj = ToiMovies()
			movieObj.addMovie(movies[i].string, critic_ratings[i].string, movieLink[i]['href'])
			#validation
			if movieObj.movieName == "":
				continue
			shouldAddMovie = movieObj.computeAbsRating()
			if True == shouldAddMovie:
				newToiMovies.append(movieObj);
				print "This movie " + movieObj.movieName + " matches your filters"

# make current directory the working directory
abspath = os.path.abspath(__file__)
dname = os.path.dirname(abspath)
os.chdir(dname)

# load parameters from config file
config = configparser.ConfigParser()
config.read('config.cfg')
pushbulletAPI = config['Pushbullet']['api']
print "Loaded pushbullet key from config file"

# fetch new movies from TOI
for language in langs:
	fullLink = toiLink + language + "/movie-reviews/"
	processURL(fullLink)

# compare new movies with old
oldToiMovies = []
try:
	pb = Pushbullet(pushbulletAPI)
except InvalidKeyError:
	print "Incorrect pushbullet key. Quitting program."
	sys.exit()

try:
	with open('oldToiList.pkl', 'rb') as input:
		while True:	
			try:
				oldMovie = pickle.load(input)
				#print oldMovie.movieName
				#print oldMovie.movieRating
				oldToiMovies.append(oldMovie)
			except (EOFError):
				break
except IOError:
	print "File not found. Continuing anyways..."

newMoviesAdded = list(set(newToiMovies) - set(oldToiMovies))
if len(newMoviesAdded) == 0:
	print "No new movies to be added to DB. Check back another time"
#print "New movies list: " 
#for movie in newToiMovies:
	#print movie.movieName 
#print "Old movies list: " 
#for movie in oldToiMovies:
	#print movie.movieName 
#print "Movies added: " 
for movie in newMoviesAdded:
	print movie.movieName + " sent to PushBullet"
	push = pb.push_note("This movie got a good rating on TOI: " + movie.movieName, "Check out this movie: " + movie.movieName + " that got a rating of " + movie.movieRating + "\n Link: " + movie.movieLink)

# append new movies to be added to oldToiMovies
for movie in newMoviesAdded:
	with open('oldToiList.pkl', 'ab') as output:
		print "Added " + movie.movieName + " to pickle DB"
		pickle.dump(movie, output, -1)
