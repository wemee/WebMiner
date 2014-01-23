# -.- encoding: utf-8 -.-

import hashlib
import json
import logging
from logging import Formatter
from logging import StreamHandler
from logging.handlers import TimedRotatingFileHandler
import os
import os.path
import pprint
import re
import time
import urllib
# import urllib2
# from urllib2 import URLError
from webminer.parser import LinkParser
from HTMLParser import HTMLParseError

## Crawler
#
# @todo check charset from HTML tags <html charset="..."> <meta http-equiv="..."> <meta charset="...">
#
class Crawler(object):

	# Tools, use static member to save memory
	hashtool = hashlib.new("md5")
	ppout    = pprint.PrettyPrinter(indent=4)
	logger   = logging.getLogger('Crawler')
	parser   = LinkParser()

	# Defaults
	CACHE_ROOT = os.environ['HOME'] + '/.crawler'
	CROSS_SITE = False
	MAX_DEPTH  = 3
	MAX_COUNT  = 100   # Max pages to download
	MAX_AGE    = 60*60 # Duration to validate cache
	GET_INTV   = 2     # Interval seconds between 2 requests

	# 建構方法, 只配置 logger
	def __init__(self):
		# 文件狀態
		self.is_html = False
		self.charset = 'utf-8'
		self.body    = ''
		self.header  = {}

		# 流程狀態
		self.url     = ''      # 目前的 URL
		self.load_ok = False   # 載入狀況
		self.depth   = 0       # 目前深度
		self.count   = 0       # 目前造訪次數
		self.elapsed = 0.0     # 載入 URL 耗費時間
		self.cached  = False   # 是否使用快取
		self.cache_url    = '' # url 快取檔
		self.cache_body   = '' # body 快取檔
		self.cache_header = '' # header 快取檔
		self.visited_urls = [] # 已拜訪路徑

		# Logging
		self.logger.setLevel(logging.DEBUG)
		self.logger.setLevel(logging.INFO)
		#formatter = Formatter("[%(asctime)s] %(levelname)s - %(name)s: %(message)s")
		formatter = Formatter("%(levelname)s: %(message)s")

		# 輸出到檔案
		handler = TimedRotatingFileHandler(self.CACHE_ROOT+'/crawler.log')
		handler.setFormatter(formatter)
		self.logger.addHandler(handler)
		
		# 輸出到 stdin
		handler = StreamHandler()
		handler.setFormatter(formatter)
		self.logger.addHandler(handler)

	# 取得資源
	def fetch(self, url):
		if url in self.visited_urls: return

		self.depth = self.depth + 1
		self.count = self.count + 1

		self.url = url
		self._load()
		self.visited_urls.append(url)

		branch = '| ' * (self.depth-1) + '|--'
		self.logger.info('%s (d=%d/c=%d/e=%.2fs/t=%.2fs) %s' % (branch, self.depth, self.count, self.elapsed, self.totaltime, url))

		if self.load_ok:
			msg = 'Header Informations:\n' + self.ppout.pformat(self.header)
			self.logger.debug(msg)

			# HTML 分析與遞迴拜訪處理
			if (self.is_html == True) and (self.depth < self.MAX_DEPTH):
				self.logger.debug('Parsing links in %s' % url)
				self.logger.debug('Current depth: %d' % self.depth)
				#self.parser.setCurrentURL(url)

				try:
					# 有可能 parsing 失敗
					self.parser.feed(self.body)
					inner_urls = self.parser.getInnerLinks(url)

					for nexturl in inner_urls:
						if (self.count < self.MAX_COUNT):
							self.fetch(nexturl)
				except HTMLParseError as e:
					self.logger.error('parsing error')
			else:
				# 遞迴停止狀況
				if (self.is_html == True):
					self.logger.debug('Hit the max depth %s.' % self.depth)
				else:
					self.logger.debug('Not a HTML')

		self.depth = self.depth - 1
		if self.depth == 0:
			print('done!')

	## 載入 URL
	#
	# 1. 檢查快取讀寫環境
	# 2. 檢查快取狀態
	# 3. 載入快取 or 實際下載
	#
	def _load(self):
		beg_time = time.time()

		# 分解 domain / URI
		m = re.match(r'https?://([^/?]+)(.*)', self.url)
		domain = m.group(1)
		uri    = m.group(2)

		# 計算快取路徑與快取檔名
		if uri is '' or uri is '/':
			cache_name = 'root'
		else:
			self.hashtool.update(uri)
			cache_name = self.hashtool.hexdigest()

		cache_path = '%s/%s' % (self.CACHE_ROOT, domain)
		self.cache_url    = '%s/%s.url' % (cache_path, cache_name)
		self.cache_body   = '%s/%s.htm' % (cache_path, cache_name)
		self.cache_header = '%s/%s.hdr' % (cache_path, cache_name)

		# 自動產生快取路徑
		# TODO:
		# - is file / is link ...
		# - bad privilege
		if not os.path.isdir(cache_path):
			os.makedirs(cache_path)

		# 判別是否直接使用快取 (self.MAX_AGE 之內使用快取)
		self.cached = False
		if os.path.isfile(self.cache_body) and os.path.isfile(self.cache_header):
			mtime = os.path.getmtime(self.cache_body)
			now   = time.time()
			tdiff = now - mtime
			if tdiff <= self.MAX_AGE:
				self.cached = True

		delay_secs = 0

		# 載入方式決定
		if self.cached:
			self._loadFromCache()
		else:
			# 載入
			self._loadFromHTTP()

			# Delay
			if self.load_ok:
				delay_secs = self.GET_INTV - (time.time() - beg_time)
				if delay_secs > 0:
					time.sleep(delay_secs)
				else:
					delay_secs = 0

		if self.load_ok:
			self.body = unicode(self.body, self.charset)

		end_time = time.time()
		self.totaltime = end_time - beg_time
		self.elapsed   = self.totaltime - delay_secs

		# dump debug message
		self.logger.debug("==================================================")
		self.logger.debug("         self.url: %s" % self.url)
		self.logger.debug("           domain: %s" % domain)
		self.logger.debug("              URI: %s" % uri)
		self.logger.debug("       cache_name: %s" % cache_name)
		self.logger.debug("       cache_path: %s" % cache_path)
		self.logger.debug("  self.cache_body: %s" % self.cache_body)
		self.logger.debug("self.cache_header: %s" % self.cache_header)
		self.logger.debug("      self.cached: %s" % self.cached)
		self.logger.debug("     self.elapsed: %f second(s)" % self.elapsed)
		self.logger.debug("==================================================")

	## 從 Cache 載入文件, _load() 最後階段
	#
	def _loadFromCache(self):
		# TODO: I/O Error

		# header 載入
		hdump = self._loadFile(self.cache_header)
		self.header = json.loads(hdump)
		self._parseType()

		# body 載入
		self.body = self._loadFile(self.cache_body)

		self.logger.debug("Load from cache")
		self.load_ok = True

	## 從 HTTP 載入文件, _load() 最後階段
	#
	def _loadFromHTTP(self):
		try:
			# 使用 urllib2 存取 HTTP
			httpreq = urllib2.Request(self.url)
			httpreq.add_header('User-Agent', 'Mozilla/9.9 (Shit Browser)')

			# HTTP 快取驗證 (快取都正常才做)
			if os.path.isfile(self.cache_body) and os.path.isfile(self.cache_header):
				lastmod = self._loadLastModified()
				if lastmod != None:
					self.logger.debug('啟動時間快取驗證')
					httpreq.add_header('If-Modified-Since', lastmod)

			# 開始 HTTP 串流處理 (f 為 HTTP 連線)
			f = urllib2.urlopen(httpreq)

			#-----------------
			# Begin of 200 OK
			#-----------------

			# header (list to dict)
			self.header = {}
			for h in f.info().headers:
				semipos = h.find(":")
				hkey = h[0:semipos] 
				hval = h[semipos+2:len(h)-2] # 遇到非標準的 http server 這段可能會出錯
				self.header[hkey] = hval

			# 處理 mime-type 與 charset
			self._parseType()

			# body 讀取/轉碼
			self.body = f.read()

			# 結束 HTTP 串流處理，之後是離線作業 (f 為檔案)
			f.close()

			if self.is_html:
				# header 暫存
				hdump = json.dumps(self.header, sort_keys=True, indent=2)
				self._saveFile(self.cache_header,hdump)

				# body 暫存
				self._saveFile(self.cache_body,self.body)

				# URI 暫存，Crawler 不會用到，供 Parser 使用
				self._saveFile(self.cache_url,self.url)

				self.logger.debug("Load from HTTP")
				self.load_ok = True
			else:
				self.logger.debug('Not HTML document')
				self.body = ''
				self.load_ok = False

			#---------------
			# End of 200 OK
			#---------------

		except URLError as e:
			if e.code == 304:
				# 摸 body 檔，然後載入 cache
				# 摸 body 檔是為了讓 _load() 順延 self.MAX_AGE     的時間
				self.logger.debug("304 Not Modified - Touch cache and load from it")
				os.utime(self.cache_body, None)
				self._loadFromCache()
			else:
				# e.g. 404, 500 ...
				self.logger.error('HTTP Error: %d %s' % (e.code,e.reason))
				self.logger.error('       URL: %s' % self.url)
				self.load_ok = False

	## 存檔 (以後要抽離)
	#
	def _saveFile(self,filename, contents):
		f = open(filename,'w')
		f.write(contents)
		f.close()

	## 讀檔 (以後要抽離)
	#
	def _loadFile(self,filename):
		f = open(filename,'r')
		contents = f.read()
		f.close()
		return contents

	## 從 Cache 取得 Last-Modified, 用在 _loadFromHTTP() 的時間快取驗證
	#
	def _loadLastModified(self):
		# header 載入
		f = open(self.cache_header,'r')
		hdump = f.read()
		f.close()
		header = json.loads(hdump)
		if header.has_key('Last-Modified'):
			return header['Last-Modified']
		else:
			return None

	## 分析 Content-Type, 用在 _loadFromHTTP() 的轉碼處理, 以及後送 parser
	#
	def _parseType(self):
		hval = self.header['Content-Type']

		# 分析 type
		if hval.find('text/html') > -1:
			self.is_html = True
			hval = hval.lower()

		# 分析 charset
		charset_offset = hval.find('charset=')
		if charset_offset > -1:
			self.charset = hval[charset_offset+8:len(hval)]
		else:
			self.charset = 'iso8859_1'
