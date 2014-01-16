## Test Command: python -m unittest discover webminer/

import unittest
from webminer.parser import LinkParser

class TestLinkParser(unittest.TestCase):

	## Preparation for each case
	#
	def setUp(self):
		self.parser = LinkParser()

	## Test for a simple input
	#
	def test_00simple(self):
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
	def test_01nested(self):
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
	def test_02bad_depth(self):
		htmlcode = '<a href="first">Good Link 1</a>Bad link</a><a href="second">Good Link 2</a>'
		self.parser.feed(htmlcode)
		self.assertEqual(self.parser.sa_count, 2)
		self.assertEqual(self.parser.ea_count, 3)
		self.assertEqual(len(self.parser.links),2)
		self.assertEqual(self.parser.links[0][0],'Good Link 1')
		self.assertEqual(self.parser.links[1][0],'Good Link 2')
