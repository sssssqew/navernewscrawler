# -*- coding: utf-8 -*- 
from django.shortcuts import render
from django.http import HttpResponse, HttpResponseRedirect
from .forms import KeywordForm
from .models import Keyword
import json
from dateutil.relativedelta import relativedelta
import datetime
import os

import sys
from bs4 import BeautifulSoup
import urllib2
import lxml
import numpy as np 
import multiprocessing
import timeit
import csv
import collections

# 데이터 수집기간 설정 
TERM = 3

# URL 쿼리 설정 
TARGET_URL_BEFORE_QUERY = 'https://search.naver.com/search.naver?where=news&se=0&query='
TARGET_URL_BEFORE_FRONT_DATE = '&ie=utf8&sm=tab_opt&sort=0&photo=0&field=0&reporter_article=&pd=3&ds='
TARGET_URL_BEFORE_BACK_DATE = '&docid=&nso=so%3Ar%2Cp%3Afrom'
TARGET_URL_REST = '%2Ca%3Aall&mynews=0&mson=0&refresh_start=0&related=0'

is_saved = 0

# 검색할 기간의 날짜 생성  
def createDaysForYear(term):
	start_date = datetime.datetime.now() - relativedelta(days=term)
	end_date = datetime.datetime.now() 
	
	days = []
	d = start_date
	while(d.year != end_date.year or d.month != end_date.month or d.day != end_date.day):
		days.append(d)
		d = d + datetime.timedelta(days=1)

	return days

# URL 쿼리 생성 
def createUrlQuery(keword, day):
	front_date = day.strftime('%Y.%m.%d') # URL 앞부분 날짜 포맷
	back_date = day.strftime('%Y%m%d') # URL 뒷부분 날짜 포맷
	query = TARGET_URL_BEFORE_QUERY \
							+ urllib2.quote(keword.encode('utf-8')) \
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

def delete_spaces(words):
	w_list = []
	words = words.split(',')
	for word in words:
		w_list.append(word.strip())
	return w_list

# 조회 페이지 
def index(request):
	global is_saved
	# json dums : string
	# json loads: list
	print "--------------------------------------"
	print "rendering start..."

	isExist = False
	is_saved_alarm = 0

	selected_keywords = []
	context = {}

	# DB 저장 체크 
	if is_saved:
		is_saved_alarm = 1
		is_saved = 0

	if request.method == 'POST':
		selected_keywords = delete_spaces(request.POST['selected_keywords'])
		
	if selected_keywords:
		not_exist_keys = []
		day_list = []

		try:
			start_date_search = datetime.datetime.strptime(request.POST['start_date_search'], "%Y-%m-%d")
		except:
			start_date_search = datetime.datetime.strptime('2012-03-02', "%Y-%m-%d")
		try:
			end_date_search = datetime.datetime.strptime(request.POST['end_date_search'], "%Y-%m-%d")
		except:
			end_date_search = datetime.datetime.now()

		columns = []
		
		# DB 조회 
		for selected_keyword in selected_keywords:
			try:
				key_model = Keyword.objects.get(name=selected_keyword)
				if(key_model):
					print "model exist in DB"
					# print key_model.name (aws에서 완전히 삭제해야 동작함)

				numOfNews = json.loads(key_model.numOfNews)
				np_numOfNews = np.array(numOfNews) # list to np array
				x = np_numOfNews[:, 0] # np array (keyword)
				y = np_numOfNews[:, 1] # np array (date)
				z = np_numOfNews[:, 2] # np array (number of news)
				y_map = np.array(map(lambda p: datetime.datetime.strptime(p, "%Y-%m-%d"), y)) # np array

				condition = np.logical_and(y_map >=  start_date_search, y_map <= end_date_search)
				date = y[np.where(condition)].tolist()
				data = z[np.where(condition)].tolist()

				# print type(date)
				date.insert(0, 'x')
				data.insert(0, selected_keyword)

				columns.append(data) 
				columns.insert(0, date)

				# print columns

				# columns.append(json.loads(key_model.numOfNews))
			except:
				print "model doesn't exist in DB"
				not_exist_keys.append(selected_keyword)

		# DB 존재하는 경우 
		if len(columns) > 1:
			isExist = True
			context = {"columns":json.dumps(columns), "not_keys":not_exist_keys, "isExistData":isExist}
		else:
			context = {"not_keys":not_exist_keys, "isExistData":isExist}
	else:
		# print "sel is not !!"
		context = {"is_saved_alarm":is_saved_alarm, "isExistData":isExist}

	return render(request, 'crawler/search.html', context)


# 검색 페이지 
def store(request):

	is_saved = 0
	start_time = timeit.default_timer()

	if request.method == 'POST':
		# 파일 입력 
		if 'file' in request.FILES:
			keywords = []
			file = request.FILES['file']
			print "-------------------"
			# print request.charset
			csvReader = csv.reader(file)

			for k in csvReader:
				# print k[1].decode('euc-kr') # file encoding에 따라 변경 (aws 에러남)
				keywords.append(k[1].decode('euc-kr'))
			keys = keywords
		# 직접 입력 
		else:
			keywords = request.POST['keywords']
			keys = delete_spaces(keywords)

	# 수집할 검색어 및 날짜 배열 만들기 
	days = createDaysForYear(TERM)
	print days 
	
	# DB 저장 
	for key in keys:
		try:
			key_model = Keyword.objects.get(name=key)
			# print ("\n" + key + '  is already exists in database !!') (aws에서 완전히 삭제해야 동작함)

		except:
			record_data = collections.OrderedDict()
			URLS = []

			# URL 리스트 생성 
			for day in days:
				url = createUrlQuery(key, day)
				URLS.append(url)

			# 데이터 수집 
			pool = multiprocessing.Pool(processes=16)  
			num_news_list = pool.map(get_content, URLS) 
			pool.close()  
			pool.join()   

			record_data[key] = []
			for i in range(len(days)):
				row = []
				row.append(key)
				row.append(days[i].strftime("%Y-%m-%d"))
				row.append(num_news_list[i])
				# print type(key)
				# print type(days[i].strftime("%Y-%m-%d"))
				# print type(num_news_list[i])
				record_data[key].append(row)

			# record_data[key].insert(0, key)

			# 결과 저장 
			key_model = Keyword(
				name=key, 
				numOfNews=json.dumps(record_data[key])
			)
			key_model.publish()
			key_model.save() 
			# print ("\n" + key + '  just saved in database !!') # aws에서 완전히 삭제해야 동작함
			global is_saved
			is_saved = 1

	# 실행시간 표시 
	elapsed = timeit.default_timer() - start_time
	print "------------------------------------------------------------------"
	print "실행시간(s): " + str(round(elapsed , 3)) + ' s'
	print "실행시간(min) : " + str(round(elapsed / 60 , 3)) + ' min'

	return HttpResponseRedirect("/")


def csvWriter(request):
	today = datetime.datetime.now().strftime("%Y-%m-%d")
	# Create the HttpResponse object with the appropriate CSV header.
	response = HttpResponse(content_type='text/csv')
	filename = "navernews_" + today+".csv"
	response['Content-Disposition'] = 'attachment; filename=' + filename
	writer = csv.writer(response)

	if request.method == 'POST':
		# 파일 입력 
		if 'file' in request.FILES:
			selected_keywords = []
			file = request.FILES['file']
			print "-------------------"
			# print request.charset
			csvReader = csv.reader(file)

			for k in csvReader:
				# print k[1].decode('euc-kr') # file encoding에 따라 변경 (aws 에러남)
				selected_keywords.append(k[1].decode('euc-kr'))
			
		# 직접 입력 
		else:
			selected_keywords = delete_spaces(request.POST['selected_keywords'])

	# try: 
	# 	selected_keywords = delete_spaces(request.POST['selected_keywords'])
	# 	print selected_keywords
	# except:
	# 	print "you haven't enter keywords !!"


	if selected_keywords:
		not_exist_keys = []
		try:
			start_date_search = datetime.datetime.strptime(request.POST['start_date_search'], "%Y-%m-%d")
		except:
			start_date_search = datetime.datetime.strptime('2012-03-02', "%Y-%m-%d")
		try:
			end_date_search = datetime.datetime.strptime(request.POST['end_date_search'], "%Y-%m-%d")
		except:
			end_date_search = datetime.datetime.now()


		# DB 조회 
		for selected_keyword in selected_keywords:
			try:
				
				key_model = Keyword.objects.get(name=selected_keyword)
				if(key_model):
					print "model exist in DB"
					# print key_model.name (aws에서 완전히 삭제해야 동작함)
				
				numOfNews = json.loads(key_model.numOfNews)
				np_numOfNews = np.array(numOfNews) # list to np array
				x = np_numOfNews[:, 0] # np array (keyword)
				y = np_numOfNews[:, 1] # np array (date)
				z = np_numOfNews[:, 2] # np array (number of news)
				y_map = np.array(map(lambda p: datetime.datetime.strptime(p, "%Y-%m-%d"), y)) # np array

				condition = np.logical_and(y_map >=  start_date_search, y_map <= end_date_search)
				date = y[np.where(condition)].tolist()
				data = z[np.where(condition)].tolist()

				suffix = u'(뉴)'
				# print type(suffix.encode('euc-kr'))

				for i in range(len(date)):

					writer.writerow([key_model.name.encode('euc-kr')+suffix.encode('euc-kr'), date[i].encode('euc-kr'), data[i].encode('euc-kr'), data[i].encode('euc-kr'), data[i].encode('euc-kr'), data[i].encode('euc-kr')])
					# print type(key_model.name.encode('utf-8'))

			except:
				print "model doesn't exist in DB"
				not_exist_keys.append(selected_keyword)

	return response



