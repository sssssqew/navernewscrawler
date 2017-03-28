# -*- coding: utf-8 -*- 
from .models import Keyword
import datetime
import urllib2
import pytz
from dateutil.relativedelta import relativedelta
import os
from bs4 import BeautifulSoup
import lxml
import multiprocessing
import json

# URL 쿼리 설정 
TARGET_URL_BEFORE_QUERY = 'https://search.naver.com/search.naver?where=news&se=0&query='
TARGET_URL_BEFORE_FRONT_DATE = '&ie=utf8&sm=tab_opt&sort=0&photo=0&field=0&reporter_article=&pd=3&ds='
TARGET_URL_BEFORE_BACK_DATE = '&docid=&nso=so%3Ar%2Cp%3Afrom'
TARGET_URL_REST = '%2Ca%3Aall&mynews=0&mson=0&refresh_start=0&related=0'

# URL 쿼리 생성 
def createUrlQuery(keword, day):
	front_date = day.strftime('%Y.%m.%d') # URL 앞부분 날짜 포맷
	back_date = day.strftime('%Y%m%d') # URL 뒷부분 날짜 포맷
	query = TARGET_URL_BEFORE_QUERY \
							+ urllib2.quote(keword) \
							+ TARGET_URL_BEFORE_FRONT_DATE \
							+ front_date + '&de=' \
							+ front_date + TARGET_URL_BEFORE_BACK_DATE \
							+ back_date + 'to' \
							+ back_date \
							+ TARGET_URL_REST

	return query

# 뉴스 건수 추출 
def getNumberOfNews(query):
	# Connection refused error 해결 
	try:
		# 사람이 검색하는 것처럼 속임 
		user_agent = 'Mozilla/4.0 (compatible; MSIE 5.5; Windows NT)'
		headers = { 'User-Agent' : user_agent }
		r = urllib2.Request(query, headers=headers)
		URL_source_FOR_DATE = urllib2.urlopen(r)
	except Exception as e:
		pass

	soup = BeautifulSoup(URL_source_FOR_DATE, 'lxml', from_encoding='utf-8')

	# 기사 없음 
	if not soup.find('div', 'title_desc all_my'):
		URL_source_FOR_DATE.close()
		return 0

	news_num_for_day = soup.find('div', 'title_desc all_my').select('span')[0].text.split('/')
	news_num_for_day_int = int(filter(lambda x: x.isdigit(), news_num_for_day[1])) # 숫자 추출 
	URL_source_FOR_DATE.close()
	return  news_num_for_day_int

def get_content(url):
	print "searching..."
	num_news = getNumberOfNews(url)
	return num_news


def my_scheduled_job():
	tz = pytz.timezone('Asia/Seoul')
	log_time = datetime.datetime.now(tz=tz).strftime("%Y-%m-%d %H:%M:%S")
	print "log time : " + log_time + "-----> cron job executed !!"

	# keys = ['문재인', '황교안', '안희정', '안철수', '유승민', '이재명']
	# db에 저장된 모든 키워드 메모리로 가져옴 
	keys = Keyword.objects.all()
	today = datetime.datetime.now()

	URLS = []

	# DB 저장 
	for key in keys:
		# URL 리스트 생성 
		url = createUrlQuery(key, today)
		URLS.append(url)

		
	# 데이터 수집 
	pool = multiprocessing.Pool(processes=16)  
	num_news_list = pool.map(get_content, URLS) 
	pool.close()  
	pool.join()

	# print num_news_list

	# DB 저장 
	for i in range(len(keys)):
		today_news = []
		try:
			key_model = Keyword.objects.get(name=keys[i])
			print "model exists"
			print key_model.name.encode('utf-8')
			today_news.append(unicode(keys[i], 'utf-8'))
			today_news.append(today.strftime("%Y-%m-%d"))
			today_news.append(num_news_list[i])
			# print unicode(keys[i], 'utf-8')
			# print type(today.strftime("%Y-%m-%d"))
			# print type(num_news_list[i])
			# print today_news

			numOfNews = json.loads(key_model.numOfNews)
			numOfNews.append(today_news)

			# print numOfNews
			key_model.numOfNews = json.dumps(numOfNews)
			key_model.save(update_fields=['numOfNews'])
			print "update completed !!"

		except:
			print "model does not exist"