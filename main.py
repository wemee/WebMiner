#!/usr/bin/python
# -.- encoding: utf-8 -.-

from webminer.crawler import Crawler

c = Crawler()
#c.fetch('http://stackoverflow.com');
#c.fetch('http://stackoverflow.com/');
#c.fetch('http://stackoverflow.com?a=1');
#c.fetch('http://stackoverflow.com?b=2');
#c.fetch('http://stackoverflow.com/users/1844300/raymond-wu')
#c.fetch('http://diveintomark.org/xml/atom.xml')
c.fetch('http://bibleclick.me')

# 用來測 304
#c.fetch('http://l.yimg.com/bf/ysm/ruby/ruby_iframe_ne.html?ctxtID=ysmcmtarget&Partner=yahoo_tw_ruby_homepage_ne2_cm')