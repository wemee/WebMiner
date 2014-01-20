## Test module of webminer
#
#  Test Command: python -m unittest -v webminer.test
#                python -m unittest discover -v webminer/
#

import unittest
from webminer.parser import LinkParser

class TestLinkParser(unittest.TestCase):

	## Preparation for each case
	#
	def setUp(self):
		self.parser = LinkParser()

	## Test for a simple input
	#
	def test_01_simple(self):
		htmlcode = '<a href="http://www.google.com">Google</a>'
		self.parser.feed(htmlcode)

		# check parser status
		self.assertEqual(len(self.parser.links),1)
		self.assertEqual(self.parser.a_depth,0)
		self.assertEqual(self.parser.sa_count,1)
		self.assertEqual(self.parser.ea_count,1)

		# check the types of links
		self.assertIsInstance(self.parser.links,list)        # [(...), (...), (...), ...]
		self.assertIsInstance(self.parser.links[0],tuple)    # (label,title,link,startpos,endpos)
		self.assertIsInstance(self.parser.links[0][0],str)   # label    str
		self.assertIsInstance(self.parser.links[0][1],str)   # title    str
		self.assertIsInstance(self.parser.links[0][2],str)   # link     str
		self.assertIsInstance(self.parser.links[0][3],tuple) # startpos (int, int)
		self.assertIsInstance(self.parser.links[0][4],tuple) # endpos   (int, int)

		# check the contents of links
		self.assertEqual(self.parser.links[0][0],'Google')
		self.assertEqual(self.parser.links[0][1],'')
		self.assertEqual(self.parser.links[0][2],'http://www.google.com')
		self.assertEqual(self.parser.links[0][3],(1,0))
		self.assertEqual(self.parser.links[0][4],(1,38)) # begin position of </a>

	## Test for nested <a> tags and multiline html code
	#
	def test_02_nested(self):
		htmlcode = '''
			<a href="http://example.com/book">
				The book includes 
				a <a href="cd">CD</a>, a <a href="cd">DVD</a>
				and a gift.
			</a>
		'''
		self.parser.feed(htmlcode)
		self.assertEqual(len(self.parser.links),3)
		self.assertEqual(self.parser.links[0][0],'The book includes a CD, a DVD and a gift.')
		self.assertEqual(self.parser.links[1][0],'CD')
		self.assertEqual(self.parser.links[2][0],'DVD')

	## Test for bad depth of <a> and fault torrance
	#
	def test_03_bad_depth(self):
		htmlcode = '<a href="first">Good Link 1</a>Bad link</a><a href="second">Good Link 2</a>'
		self.parser.feed(htmlcode)
		self.assertEqual(self.parser.sa_count,2)
		self.assertEqual(self.parser.ea_count,3)
		self.assertEqual(len(self.parser.links),2)
		self.assertEqual(self.parser.links[0][0],'Good Link 1')
		self.assertEqual(self.parser.links[1][0],'Good Link 2')

	## Test parsing current URL
	#
	def test_04_relative_path(self):
		# basic test
		self.assertEqual(self.parser.parseCurrentURL('http://example.com'), True)
		self.assertEqual(self.parser.protocol, 'http:')
		self.assertEqual(self.parser.siteurl, 'http://example.com')
		self.assertEqual(self.parser.baseurl, 'http://example.com/')
		self.assertEqual(self.parser.fullurl, 'http://example.com')

		self.assertEqual(self.parser.parseCurrentURL('http://example.com/'), True)
		self.assertEqual(self.parser.protocol, 'http:')
		self.assertEqual(self.parser.siteurl, 'http://example.com')
		self.assertEqual(self.parser.baseurl, 'http://example.com/')
		self.assertEqual(self.parser.fullurl, 'http://example.com/')

		# good test
		self.assertEqual(self.parser.parseCurrentURL('http://example.com/a'), True)
		self.assertEqual(self.parser.baseurl, 'http://example.com/')
		self.assertEqual(self.parser.parseCurrentURL('http://example.com/a/'), True)
		self.assertEqual(self.parser.baseurl, 'http://example.com/a/')
		self.assertEqual(self.parser.parseCurrentURL('http://example.com/a/b#c'), True)
		self.assertEqual(self.parser.baseurl, 'http://example.com/a/')
		self.assertEqual(self.parser.fullurl, 'http://example.com/a/b')

		# bad cases
		pr = self.parser.parseCurrentURL('ftp://example.com')
		self.assertEqual(pr, False)
		pr = self.parser.parseCurrentURL('http://')
		self.assertEqual(pr, False)
		pr = self.parser.parseCurrentURL('#shit')
		self.assertEqual(pr, False)

	## Test gathering inner links
	#
	def test_05_inner_links(self):
		currurl  = 'http://example.com/a/b'
		htmlcode = '''
			<a href="http://ad.com">Link #1</a>
			<a href="//ad.com">Link #2</a>
			<a href="javascript:alert('something')">Link #4</a>
			<a href="about:blank">Link #5</a>
			<a href="mailto:nobody@example.com">Link #6</a>
			<a href="">Link #7</a>
			<a href="#xxx">Link #3</a>
			<a href="c">Link #8</a>
			<a href="/d">Link #9</a>
			<a href="//example.com/e">Link #10</a>
			<a href="http://example.com/f">Link #11</a>
			<a href="http://example.com/f/g#c">Link #11</a>
			<a href="/">Link #12</a>
		'''

		self.parser.feed(htmlcode)
		ilinks = self.parser.getInnerLinks(currurl)

		self.assertIsInstance(ilinks,list)
		self.assertEqual(len(ilinks),8)
		self.assertEqual(ilinks[0],'http://example.com/a/b') # ''                       => 'http://example.com/a/b'
		self.assertEqual(ilinks[1],'http://example.com/a/b') # '#xxx'                   => 'http://example.com/a/b'
		self.assertEqual(ilinks[2],'http://example.com/a/c') # 'c'                      => 'http://example.com/a/c'
		self.assertEqual(ilinks[3],'http://example.com/d')   # '/d'                     => 'http://example.com/d'
		self.assertEqual(ilinks[4],'http://example.com/e')   # '//example.com/e'        => 'http://example.com/e'
		self.assertEqual(ilinks[5],'http://example.com/f')   # 'http://example.com/f'   => 'http://example.com/f'
		self.assertEqual(ilinks[6],'http://example.com/f/g') # 'http://example.com/f/g' => 'http://example.com/f/g'
		self.assertEqual(ilinks[7],'http://example.com/')    # '/'                      => 'http://example.com/'
