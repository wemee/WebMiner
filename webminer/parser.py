# for stackparser
from codecs import *
from HTMLParser import HTMLParser

## 堆疊型 HTML 分析器
class HTMLStackParser2(HTMLParser):

	## 除錯設定
	trace_stack = False

	## 不打入堆疊的標籤
	tag_leaf = ["br","hr","input","meta","link","img"]
	
	## 需要取出連結的標籤
	tag_withlink = ["a","img","form","link","script"]

	## 標籤堆疊狀態
	tag_stack = []

	# 各類連結資源
	links   = []
	images  = []
	scripts = []
	forms   = []
	styles  = []

	## 取得屬性值
	# @param string name
	# @param list   attrs
	# @return TODO
	def get_attribute(self, name, attrs):
		for (vname,value) in attrs:
			if vname==name:
				return value
		return None
			
	## 處理開頭標籤
	# @param string tag 標籤
	# @param truple attrs 屬性值
	def handle_starttag(self, begtag, attrs):
		# 連結檢查
		if begtag in self.tag_withlink:
			if begtag=="a" or begtag=="link":
				aname = "href"
			elif begtag=="img" or begtag=="script":
				aname = "src"
			elif begtag=="form":
				aname = "action"
			
			link = self.get_attribute(aname,attrs)
			self.on_link_visited(link, begtag, aname)
		
		# 堆疊深度分析
		if begtag not in self.tag_leaf:
			self.tag_stack.append(begtag)
			self.dump_tag_stack("[+%s]" % (begtag))

	## 處理結尾標籤
	# @param string tag 標籤
	def handle_endtag(self, endtag):
		# 比對標籤對稱性
		toptag = self.tag_stack[len(self.tag_stack)-1]
		if toptag == endtag:
			# 對稱處理
			self.tag_stack.pop()
		else:
			# 不對稱處理
			print("!!! 偵測到不對稱標籤 <%s> </%s>" % (toptag, endtag))

		# 顯示堆疊狀態
		if self.trace_stack:
			self.dump_tag_stack("[-%s]" % (endtag))

	## 顯示標籤堆疊
	# @param string label 開頭記號
	def dump_tag_stack(self, label):
		str = ""
		if len(self.tag_stack) > 0:
			for tag in self.tag_stack:
				if str != "":
					str = str + " > "
				str = str + tag
		else:
			str = "-- empty stack --"
		str = label + " " + str
		print(str)

	## 遇到連結
	# 可能發生連結的屬性有下列情境
	# - <a href="...">
	# - <img src="...">
	# - <form action="...">
	# - <script src="...">
	# - <link href="...">
	#
	# @param string link  連結目標
	# @param string tag   標籤
	# @param string aname 屬性名稱
	def on_link_visited(self, link, tag, aname):
		if self.trace_stack:
			print("訪問到連結屬性: <%s %s=\"%s\"> (未實作)" % (tag, aname, link))
		if link != None:
			if tag =="a":
				self.links.extend(link)