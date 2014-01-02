# -.- encoding: utf-8 -.-

import hashlib
import json
import os
import os.path
import pprint
import re
import time
import urllib
import urllib2
from urllib2 import URLError

## 爬蟲
#
# @todo 計時快取設計
#
class Crawler:
	
	# 文件狀態
	is_html = False
	is_utf8 = True
	body    = ''
	header  = {}

	# 流程狀態
	url     = ''      # 目前的 URL
	load_ok = False   # 載入狀況
	max_age = 0     # 強制重新檢查的時間
	cache_body   = '' # body 快取檔
	cache_header = '' # header 快取檔

	# 工具物件
	hashtool = hashlib.new("md5")             # hash 演算法
	ppout    = pprint.PrettyPrinter(indent=4) # 人性輸出

	# 預設快取路徑
	CACHE_ROOT = os.environ['HOME'] + '/.crawler'

	# 建構方法, 無作用
	def __init__(self):
		pass

	# 取得資源
	def fetch(self, url):
		self.url = url
		self._load()

		if self.load_ok:
			self.ppout.pprint(self.header)

		# HTML 分析
		#if self.is_html == True:
		#	parser = HTMLStackParser()
		#	parser.feed(contents)

	## 載入 URL
	#
	# 1. 檢查快取讀寫環境
	# 2. 檢查快取狀態
	# 3. 載入快取 or 實際下載
	#
	def _load(self):
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

		'''
		print("              url: %s" % self.url)
		print("           domain: %s" % domain)
		print("              uri: %s" % uri)
		print("       cache_name: %s" % cache_name)
		print("       cache_path: %s" % cache_path)
		print("  self.cache_body: %s" % self.cache_body)
		print("self.cache_header: %s" % self.cache_header)
		print("==========")
		'''

		# 判別是否直接使用快取 (self.max_age 之內使用快取)
		use_cache = False
		if os.path.isfile(self.cache_body) and os.path.isfile(self.cache_header):
			mtime = os.path.getmtime(self.cache_body)
			now   = time.time()
			tdiff = now - mtime
			if tdiff <= self.max_age:
				use_cache = True

		if use_cache:
			self._loadFromCache()
		else:
			self._loadFromHTTP()

	## 從 Cache 載入文件, _load() 最後階段
	#
	def _loadFromCache(self):
		# TODO: I/O Error

		# header 載入
		f = open(self.cache_header,'r')
		hdump = f.read()
		f.close()
		self.header = json.loads(hdump)

		# body 載入
		f = open(self.cache_body,'r')
		self.body = f.read()
		f.close()

		self.load_ok = True

	## 從 HTTP 載入文件, _load() 最後階段
	#
	def _loadFromHTTP(self):
		try:
			# 使用 urllib2 存取 HTTP
			# TODO: 加上 If-Modified-Since: 以便節省頻寬 ...
			httpreq = urllib2.Request(self.url)

			# HTTP 快取驗證 (快取都正常才做)
			if os.path.isfile(self.cache_body) and os.path.isfile(self.cache_header):
				lastmod = self._loadLastModified()
				if lastmod != None:
					print('啟動時間快取驗證')
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
				if hkey == "Content-Type": self._parseType(hval)

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

			self.load_ok = True
		except URLError as e:
			if e.code == 304:
				# 摸 body 檔，然後載入 cache
				# 摸 body 檔是為了讓 _load() 順延 self.max_age 的時間
				os.utime(self.cache_body, None)
				self._loadFromCache()
			else:
				print('Error: %d %s' % (e.code,e.reason))
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
	def _parseType(self, hval):
		if hval.find("text/html") > -1:
			self.is_html = True
			hval = hval.lower()
			if hval.find("utf-8") > -1:
				self.is_utf8 = True
