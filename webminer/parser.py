from codecs import *
import os.path
import re

from HTMLParser import HTMLParser

## Parser for <a> tag analysis
#
class LinkParser(HTMLParser, object):

	# class members
	ACCEPTED_PROTOCOLS = ('http:', 'https:')

	## constructor
	def __init__(self):
		super(LinkParser, self).__init__()

		## link info
		self.rank  = 0
		self.link  = '' # current link
		self.label = '' # current label
		self.title = ''
		self.startpos = ()

		## to determine fullpath
		self.protocol = ''
		self.siteurl  = ''
		self.baseurl  = ''
		self.fullurl  = ''

		## nested buffer
		#  (rank,link,label,title,startpos)
		self.status_stack = []

		## statistic
		self.a_depth  = 0
		self.sa_count = 0
		self.ea_count = 0

		## captured links (label,title,link,startpos,endpos)
		self.links = []

	## start tag analysis
	#  @param tag
	#  @param attrs
	def handle_starttag(self, tag, attrs):
		if (tag == 'a'):
			if self.a_depth > 0:
				curr_status = (self.rank, self.link, self.label, self.title, self.startpos)
				self.status_stack.append(curr_status)
			
			self.rank  = self.sa_count + 1
			self.link  = self.getAttribute(attrs,'href')
			self.label = ''
			self.title = ''
			self.startpos = self.getpos()

			self.links.append(False)
			self.a_depth  = self.a_depth  + 1
			self.sa_count = self.sa_count + 1
		else:
			if (self.a_depth > 0 and tag == 'img'):
				t = self.getAttribute(attrs,'title')
				self.appendTitle(t)

	## data analysis
	#  @param data
	def handle_data(self, data):
		if self.a_depth > 0:
			self.appendLabel(data)

	## end tag analysis
	#  @param tag
	def handle_endtag(self, tag):
		if (tag == 'a'):
			if self.a_depth > 0:
				# reduce space chars
				self.label = re.sub(r'\s{2,}', ' ', self.label)

				self.links[self.rank-1] = (
					self.label,
					self.title,
					self.link,
					self.startpos,
					self.getpos()
				)

				if self.a_depth > 1:
					nested_label = self.label
					nested_title = self.title

					prev_status   = self.status_stack.pop()
					self.rank     = prev_status[0]
					self.link     = prev_status[1]
					self.label    = prev_status[2]
					self.title    = prev_status[3]
					self.startpos = prev_status[4]

					self.appendLabel(nested_label)
					self.appendTitle(nested_title)

				self.a_depth = self.a_depth - 1
			else:
				# Found </a> without <a>
				self.a_depth = 0
			self.ea_count = self.ea_count + 1

	## append text in <a> ... </a>
	#  @param text
	def appendLabel(self, text):
		text = text.strip()
		if text != '':
			if (self.label != '' and text[0].isalnum()):
				self.label = self.label + ' '
			self.label = self.label + text

	## append text in <img title="..."/>
	#  @param text
	def appendTitle(self, text):
		text = text.strip()
		if (text != ''):
			if (self.title !=''):
				self.title = self.title + '\n'
			self.title = self.title + text

	## get attribute from a list of tuple
	#  @param attrs the list of tuple
	#  @param key   attribute name
	def getAttribute(self, attrs, key):
		for (k,v) in attrs:
			if (k==key):
				return v
		return ''

	## get all links that are in the same domain
	#
	def getInnerLinks(self, currurl):
		ilinks = []

		if self.parseCurrentURL(currurl) != False:
			for link in self.links:
				fullurl = self.convertFullpath(link[2])
				if fullurl != False and fullurl.startswith(self.siteurl):
					ilinks.append(fullurl)
		
		return ilinks

	## get protocol, siteurl, baseurl from an absolute URL
	#  @param currurl current url, fullpath needed
	def parseCurrentURL(self, currurl):
		eop = currurl.find(':')
		if eop != -1:
			protocol = currurl[0:eop+1] # semicolon included
			if protocol in self.ACCEPTED_PROTOCOLS:
				# ignore bookmark
				spos = currurl.find('#')
				if spos > -1:
					currurl = currurl[0:spos]

				eod = currurl.find('/',eop+3)
				if eod != -1:
					# e.g. http://example.com/a/b/c
					siteurl = currurl[0:eod]
					baseurl = os.path.dirname(currurl) + '/'
				elif len(currurl) > len(protocol)+2:
					# e.g. http://example.com
					siteurl = currurl
					baseurl = currurl + '/'
				else:
					# e.g. http://
					return False

				self.protocol = protocol
				self.siteurl  = siteurl
				self.baseurl  = baseurl
				self.fullurl  = currurl
				return True
		return False

	## convert hyperlink to fullpath
	#  @param href hyperlink
	def convertFullpath(self, href):
		fullpath = False

		if   href.startswith('//'):
			# e.g. //example.com
			fullpath = self.protocol + href
		elif href.startswith('/'):
			# e.g. /a/b/c
			fullpath = self.siteurl + href
		elif href.startswith('#'):
			# e.g. #a
			fullpath = self.fullurl
		else:
			# check if protocol exists
			semipos = href.find(':')
			if semipos > -1:
				# e.g. http://example.com/...
				protocol = href[0:semipos+1]
				if protocol in self.ACCEPTED_PROTOCOLS:
					fullpath = href
			else:
				# no protocol here
				if href != '':
					fullpath = self.baseurl + href
				else:
					fullpath = self.fullurl

		# ignore bookmark
		if fullpath != False:
			spos = fullpath.find('#')
			if spos > -1:
				fullpath = fullpath[0:spos]

		# match nothing
		return fullpath
