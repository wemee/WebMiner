#!/usr/bin/python
# -.- encoding: utf-8 -.-

from webminer.crawler import Crawler

try:
	c = Crawler()
	c.MAX_AGE = 0

	# 隨便測試
	#c.fetch('http://stackoverflow.com/users/1844300/raymond-wu')

	# 測試深度效率
	#c.fetch('http://bibleclick.me')

	# 測試 <a> label
	#c.fetch('http://localhost/wiki/index.php?title=%E9%A6%96%E9%A0%81')
	#c.fetch('http://www.chinapost.com.tw/')
	#c.fetch('http://www.economist.com/')
	c.fetch('http://localhost/samples/a-depth2.html')
	#c.fetch('http://arshaw.com/phpti/')

	# 測試 304
	#c.fetch('http://l.yimg.com/bf/ysm/ruby/ruby_iframe_ne.html?ctxtID=ysmcmtarget&Partner=yahoo_tw_ruby_homepage_ne2_cm')
except KeyboardInterrupt as e:
	print('Termainated by user.')
