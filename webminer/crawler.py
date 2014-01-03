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
import urllib2
from urllib2 import URLError
from webminer.parser import LinkParser

## Crawler
#
class Crawler(object):
	
	# 文件狀態
	is_html = False
	is_utf8 = True
	body    = ''
	header  = {}

	# 流程狀態
	url     = ''      # 目前的 URL
	load_ok = False   # 載入狀況
	cache_body   = '' # body 快取檔
	cache_header = '' # header 快取檔

	# 工具物件
	hashtool  = hashlib.new("md5")             # hash 演算法
	ppout     = pprint.PrettyPrinter(indent=4) # 人性輸出
	logger    = None
	parser    = LinkParser()
	linkstack = []

	# 預設值
	CACHE_ROOT  = os.environ['HOME'] + '/.crawler'
	CROSS_SITE  = False # 是否跨站砍站
	VISIT_DEPTH = 2     # 拜訪深度
	MAX_AGE     = 600   # 強制重新檢查的時間, 測試 304 的時候需要改成 0

	# 建構方法, 只配置 logger
	def __init__(self):
		self.logger = logging.getLogger('Crawler')
		self.logger.setLevel(logging.DEBUG)
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
		self.url = url
		self._load()

		if self.load_ok:
			msg = 'Header Informations:\n' + self.ppout.pformat(self.header)
			self.logger.debug(msg)

		# HTML 分析
		if self.is_html == True:
			self.logger.debug('Parsing for links')
			self.parser.setCurrentURL(url)
			self.parser.feed(self.body)
			self.ppout.pprint(self.parser.inner_res)
			#self.ppout.pprint(self.parser.cross_res)
		else:
			self.logger.debug('Not a HTML')

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
		self.cache_body = '%s/%s.cc' % (cache_path, cache_name)
		self.cache_header = '%s/%s.hc' % (cache_path, cache_name)

		# 自動產生快取路徑 
		#
		# TODO
		# - is file / is link ...
		# - bad privilege
		if not os.path.isdir(cache_path):
			os.makedirs(cache_path)

		# 判別是否直接使用快取 (self.MAX_AGE     之內使用快取)
		use_cache = False
		if os.path.isfile(self.cache_body) and os.path.isfile(self.cache_header):
			mtime = os.path.getmtime(self.cache_body)
			now   = time.time()
			tdiff = now - mtime
			if tdiff <= self.MAX_AGE:
				use_cache = True

		if use_cache:
			self._loadFromCache()
		else:
			self._loadFromHTTP()

		end_time = time.time()
		elapsed = end_time - beg_time

		# dump debug message
		self.logger.debug("==================================================")
		self.logger.debug("              URL: %s" % self.url)
		self.logger.debug("           domain: %s" % domain)
		self.logger.debug("              URI: %s" % uri)
		self.logger.debug("       cache_name: %s" % cache_name)
		self.logger.debug("       cache_path: %s" % cache_path)
		self.logger.debug("  self.cache_body: %s" % self.cache_body)
		self.logger.debug("self.cache_header: %s" % self.cache_header)
		self.logger.debug("        use_cache: %s" % use_cache)
		self.logger.debug("         duration: %f second(s)" % elapsed)
		self.logger.debug("==================================================")

	## 從 Cache 載入文件, _load() 最後階段
	#
	def _loadFromCache(self):
		# TODO: I/O Error

		# header 載入
		f = open(self.cache_header,'r')
		hdump = f.read()
		f.close()
		self.header = json.loads(hdump)
		self._parseType()

		# body 載入
		f = open(self.cache_body,'r')
		self.body = f.read()
		f.close()

		self.logger.debug("Load from cache")
		self.load_ok = True

	## 從 HTTP 載入文件, _load() 最後階段
	#
	def _loadFromHTTP(self):
		try:
			# 使用 urllib2 存取 HTTP
			# TODO: 加上 If-Modified-Since: 以便節省頻寬 ...
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
			# 只有 200 OK 才會繼續, 否則會進入 except

			# header (list > dict)
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
			if not self.is_utf8:
				# TODO: 非 utf8 轉碼, 可以用露天拍賣來測
				pass

			# 結束 HTTP 串流處理，之後是離線作業 (f 為檔案)
			f.close()

			# header 暫存
			hdump = json.dumps(self.header, sort_keys=True, indent=2)
			f = open(self.cache_header,'w')
			f.write(hdump)
			f.close()

			# body 暫存
			f = open(self.cache_body,'w')
			f.write(self.body)
			f.close()

			self.logger.debug("Load from HTTP")
			self.load_ok = True

			# End of 200 OK

		except URLError as e:
			if e.code == 304:
				# 摸 body 檔，然後載入 cache
				# 摸 body 檔是為了讓 _load() 順延 self.MAX_AGE     的時間
				self.logger.debug("304 Not Modified - Touch cache and load from it")
				os.utime(self.cache_body, None)
				self._loadFromCache()
			else:
				self.logger.error('HTTP Error: %d %s' % (e.code,e.reason))
				self.load_ok = False

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
		if hval.find("text/html") > -1:
			self.is_html = True
			hval = hval.lower()
			if hval.find("utf-8") > -1:
				self.is_utf8 = True
