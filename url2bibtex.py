#!/usr/bin/env python

import requests
import sys
import datetime

def getWaybackData(url):
    """
    Get data from the wayback machine at archive.org
    if feasible.

    :param url: URL to check
    :type url: str
    :returns: dict
    """
    if 0 == len(url):
        return {}

    p = {'url': stripSchema(url)}
    r = requests.get('https://archive.org/wayback/available', params=p)
    if 200 == r.status_code:
        wb = r.json()
        try:
            wb = wb['archived_snapshots']
            if 0 == len(wb):
                return {}
            wb = wb['closest']
            if not wb['available']:
                return {}
            if '200' != wb['status']:
                return {}
            return {
                'url': wb['url'],
                'timestamp': wb['timestamp']
            }
        except KeyError:
            return {}
    return {}

def getWikipediaData(url):
    """
    Get data from the wikipedia if applicable.

    :param url: URL to check
    :type url: str
    :returns: dict
    """
    from bs4 import BeautifulSoup

    if 0 == len(url):
        return {}
    r = requests.get(url)
    if 200 == r.status_code:
        soup = BeautifulSoup(r.text)
        quotepath = ''
        historpath = ''
        for a in soup.find_all("a"):
            if 'href' in a.attrs:
                if '/w/index.php?title=Special:CiteThisPage' == a['href'][:39]:
                    quotepath = a['href']
                if '&action=history' == a['href'][-15:]:
                    historypath = a['href']

        chunks = r.url.split('/')
        citeurl = chunks[0] + '//' + chunks[2] + quotepath
        citeurl = citeurl.replace('Special:CiteThisPage&page=', '')
        citeurl = citeurl.replace('&id=', '&oldid=')
        chunks = r.url.split('/')
        historyurl = chunks[0] + '//' + chunks[2] + historypath

        year = ''
        r = requests.get(historyurl)
        if 200 == r.status_code:
            soup = BeautifulSoup(r.text)
            hdate = soup.find("a", class_='mw-changeslist-date')
            year = str(hdate).split('">')[1].split(' ')[3][:4]
        return {'url': citeurl, 'author': 'Wikipedia', 'year': year}
    return {}

def bibtex(urldata):
    """
    Create an array with all the data for the bibTex file.

    :param urldata: all the data collected
    :type urldata: dict
    :returns: list
    """
    bibtex = []
    url = stripSchema(urldata['url']).replace('.', '_')
    if '/' == url[-1]:
        url = url[:-1]
    bibtex.append('@ONLINE{' + url + ':' + urldata['year'] + ':Online')
    bibtex.append('\tauthor = {},')
    if 'title' in urldata.keys():
        bibtex.append('\ttitle = {' + urldata['title'] + '},')
    bibtex.append('\tmonth = jun,')
    bibtex.append('\tyear = {' + urldata['year'] + '},')
    bibtex.append('\turl = {' + urldata['url'] + '},')
    bibtex.append('\turldate = {' + urldata['urldate'] + '}')
    if 'snapshot url' in urldata.keys():
        bibtex[-1] += ','
        bibtex.append('\tnote = {Internet Archive Wayback Machine: \url{' \
                      + urldata['snapshot url'] + '}, as of ' \
                      + urldata['snapshot date'] + '}')
    bibtex.append('}')
    return bibtex

def stripSchema(url):
    """
    Strip the schema from the given URL.

    :param url: URL to strip
    :type url: str
    :return: str
    """
    if 'https' == url[:5]:
        return url[8:]
    if 'http' == url[:4]:
        return url[7:]
    return url

def getTitle(url):
    """
    Get the title of a website.

    :param url: URL to query
    :type url: str
    :returns: str
    """
    from bs4 import BeautifulSoup

    try:
        r = requests.get(url)
    except requests.exceptions.MissingSchema:
        try:
            r = requests.get('http://' + url)
        except requests.exceptions.MissingSchema:
            try:
                r = requests.get('https://' + url)
            except requests.exceptions.MissingSchema:
                return ''
    if 200 != r.status_code:
        return ''
    soup = BeautifulSoup(r.text)
    t = soup.find_all("title")
    if 1 == len(t):
        return str(t[0]).replace('<title>', '').replace('</title>', '')
    soup.find_all("p", "title")
    if 1 == len(t):
        return str(t[0]).replace('<p class="title">', '').replace('</p>', '')
    return ''

testurl = sys.argv[1]
if 'http' != testurl[:4]:
    print("did you forget 'http(s)'?")
    sys.exit(3)

urldata = {'url': testurl,
           'urldate': str(datetime.date.today()),
           'year': str(datetime.date.today().year)}
wbdata = getWaybackData(sys.argv[1])
if 0 != len(wbdata):
    # create ISO timestamp string
    datestring = wbdata['timestamp'][:4] \
                 + '-' + wbdata['timestamp'][4:6] \
                 + '-' + wbdata['timestamp'][6:8] \
                 + 'T' + wbdata['timestamp'][8:10] \
                 + ':' + wbdata['timestamp'][10:12] \
                 + ':' + wbdata['timestamp'][12:14]
    urldata['snapshot date'] = datestring
    urldata['snapshot url'] = wbdata['url']

if -1 != urldata['url'].find('wikipedia.org'):
    wpdata = getWikipediaData(urldata['url'])
    urldata['author'] = wpdata['author']
    urldata['url'] = wpdata['url']
    urldata['year'] = wpdata['year']

title = getTitle(urldata['url'])
if 0 != len(title):
    urldata['title'] = title.replace(',', '{,}')

for line in bibtex(urldata):
    print(line)
