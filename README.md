### 몰트 위스키(mod_wsgi) 를 이용한 장고서버 셋팅 -> 가장 손쉬운 셋팅방법

```
...
0. 가상환경 생성 및 필요모듈 설치하기 
1. sudo pip install mod_wsgi-httpd 
2. sudo pip install mod_wsgi 
3. pip freeze 로 전역환경에 설치되었음을 확인하기 
4. settings.py에 INSTALLED_APPS 설정에 'mod_wsgi.server' 추가하기
5. 정적(static)파일 생성하기 
-> python manage.py collectstatic
5. manage.py 파일이 위치한 곳에서 mod_wsgi 실행하기 
-> python manage.py runmodwsgi --setup-only --user sylee --group sylee --s![선택 영역_006.png](https://bitbucket.org/repo/baqqb6g/images/3170664513-%EC%84%A0%ED%83%9D%20%EC%98%81%EC%97%AD_006.png)erver-root=/tmp/mod_wsgi-localhost:8000:1012
6. 아파치 실행 또는 재실행하기 
-> /tmp/mod_wsgi-localhost:8000:1012/apachectl start(restart)

* 아파치 설정파일 변경 : /tmp/mod_wsgi-localhost:8000:1012/httpd.conf
...
```

### 서버셋팅시 참고 사이트 

* [https://github.com/GrahamDumpleton/mod_wsgi](Link URL)
* [http://ggilrong.tistory.com/entry/Django-Apache-%EC%89%AC%EC%9A%B4-%EC%97%B0%EB%8F%99%EB%B0%A9%EB%B2%95-How-to-use-Django-with-Apache-and-modwsgi](Link URL)
* [http://stackoverflow.com/questions/24760872/how-can-run-django-on-centos-using-wsgi](Link URL)

### 에러처리 

```
/tmp/mod_wsgi-localhost:8000:1012/error_log
crontab error 발생시 /var/spool/mail/sylee 에 로그가 찍힌다. (sylee 파일은 다른 이름으로 변경가능)
static files 깨지면 mod_wsgi 리로드 
```


### 서비스 사용법
```
* 파일형식 

인코딩 : EUC-KR
확장자 : CSV
column[0] : 테마(도넛)명
column[1] : 데이터 추출을 위한 연관검색어  


* 하루치 데이터 생성

시작날짜 : 데이터 얻을려는 날짜
끝날짜 : 시작날짜 + 1

* 날짜를 입력하지 않는 경우 

시작날짜 : 디폴트 값
끝날짜 : 어제 날짜 
```

### 몰트 위스키 서버 환경설정 
```
* timeout, process, thread, buffer size 
* multiprocess인 경우
* multiprocess가 아닌 경우
```
![선택 영역_006.png](https://bitbucket.org/repo/baqqb6g/images/1182112754-%EC%84%A0%ED%83%9D%20%EC%98%81%EC%97%AD_006.png)
![선택 영역_007.png](https://bitbucket.org/repo/baqqb6g/images/1590090003-%EC%84%A0%ED%83%9D%20%EC%98%81%EC%97%AD_007.png)
![선택 영역_008.png](https://bitbucket.org/repo/baqqb6g/images/2148294297-%EC%84%A0%ED%83%9D%20%EC%98%81%EC%97%AD_008.png)