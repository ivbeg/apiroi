#!/usr/bin/env python
# coding: utf8
"""
ROI.ru data extractor
"""
import csv
import json
import os, os.path
from urllib import urlopen, unquote_plus, urlencode
import urllib2
from BeautifulSoup import BeautifulSoup, BeautifulStoneSoup
import time

from urlparse import urljoin
from StringIO import StringIO
from datetime import datetime
from pymongo import Connection

BASE_URL = 'http://roi.ru'
RAW_PATH = 'data/raw'
PETITION_FILEPAT = 'data/raw/petitions/petition_%s.json'
PETITIONS_FILE = 'data/raw/petitions.json'
LIST_URL = 'https://www.roi.ru/poll/?s_f_1=user_f_98=DESC'
LIST_URLPAT = 'https://www.roi.ru/poll/?s_f_1=user_f_98=DESC&page_19=%d'
PAGE_SIZE = 10


MONGO_SERVER = 'localhost'
MONGO_PORT = 27017
MONGO_DB = 'roi'
PETITIONS_COLL = 'petitions'
PETFULL_COLL = 'petitions_full'
VOTEHISTORY_COLL = 'votehistory'
PROBE_COLL = 'probe'

class DataExtractor:
    """Data extractor for ROI"""

    def __init__(self):
        self.conn = Connection(MONGO_SERVER, MONGO_PORT)
        self.db = self.conn[MONGO_DB]
        self.petcoll = self.db[PETITIONS_COLL]
        self.petfullcoll = self.db[PETFULL_COLL]

        pass

    def build_indexes(self):
        self.petcoll.ensure_index('slug', 1)
        self.petcoll.ensure_index('topic', 1)
        self.petcoll.ensure_index('probe_date', 1)
        self.petcoll.ensure_index('votes', 1)

        self.petfullcoll.ensure_index('slug', 1)
        self.petfullcoll.ensure_index('topic', 1)
        self.petfullcoll.ensure_index('probe_date', 1)
        self.petfullcoll.ensure_index('votes', 1)


    def extract_petition(self, url, slug):
        petition = self.petfullcoll.find_one({'slug' : slug})
        if petition is not None:
            print "Petition already processed %s" % slug
            return
        else:
            petition = {}
        u = urllib2.urlopen(url)
        data = u.read()
        soup = BeautifulSoup(data)
#        if not petition:
#            petition = {}
        container = soup.find('div', attrs={'id' : 'container-in'})
        petition['name'] = container.find('h1', recursive=True).text
        petition['uniqid'] = container.find('div', attrs={'class' : 'addr'}).string
        petition['autor_id'] = container.find('input', attrs={'id': 'autor_id'})['value']
        petition['topic_id'] = container.find('input', attrs={'id': 'petitionUrlCat'})['value']
        petition['slug'] = container.find('input', attrs={'id': 'petitionUrlElem'})['value']
        petition['description'] = unicode(container.find('div', attrs={'class' : 'block'}))
        petition['solution']  = unicode(container.find('div', attrs={'class' : 'decision-item'}))
        petition['dateshare'] = container.find('div', attrs={'class' : 'date-share'}).find('div', attrs={'class' : 'date'}).string
        dateend = soup.find('div', attrs={'class' : 'inic-side-info block'}).find('div', attrs={'class' : 'date'}).string
        day, month, year = dateend.split('.')
        petition['end_date'] = datetime(int(year), int(month), int(day))
        petition['start_date'] = datetime(int(year)-1, int(month), int(day))
#        print url
#        voting_tag = soup.find('div', attrs={'class' : 'voting-block voting-solution'}, recursive=True)
        self.petfullcoll.update({'slug' : slug}, petition, upsert=True, safe=True)
        print 'Petition updated: %s' %(slug)
        pass

    def extract_short_petitions_by_page(self, page=1, get_total=False):
        petitions = []
        u = urllib2.urlopen(LIST_URLPAT % page)
        data = u.read()
        soup = BeautifulSoup(data)
        total = 0
        if get_total:
            total = int(soup.find('div', attrs={'class' : 'rs'}).find('span').find('a').string)
        container = soup.find('div', attrs={'id' : 'container-in'})
        alist = container.find('div', attrs={'class': 'blocks2 petitionlist'})
        items = alist.findAll('div', attrs={'class': 'item'}, recursive=True)
        for item in items:
            tag_alink = item.find('div', attrs={'class' : 'link'}).find('a')
            last_url = tag_alink['href']
            rest, topic, slug, blank = last_url.rsplit('/', 3)
            petition = self.petcoll.find_one({'slug' : slug})
            if not petition:
                petition = {}
            petition['votes'] = item.find('div', attrs={'class' : 'hour'}).find('b').string
            petition['name'] = tag_alink.string
            petition['url'] = urljoin(BASE_URL, last_url)
            petition['slug'] = slug
            petition['topic_id'] = topic
            petition['jurisdiction'] = item.findAll('div')[-1]['class'].split()[-1]
            petition['probe_date'] = datetime.now() #.isoformat()
            petition['profile_type'] = 'short'
            self.petcoll.update({'slug' : slug}, petition, upsert=True, safe=True)
            print 'Petition updated: %s' %(slug)
        return petitions, total


    def extract_short_petitions_all(self):
        allpetitions = []
        petitions, total = self.extract_short_petitions_by_page(page=1, get_total=True)
        allpetitions.extend(petitions)
        npages = abs(total / PAGE_SIZE)
        if total % PAGE_SIZE > 0: npages += 1
        print npages
        for page in range(2, npages+1, 1):
            petitions, total = self.extract_short_petitions_by_page(page=page)
            print 'Processes page %d of %d' % (page, npages)
            allpetitions.extend(petitions)


    def extract_full_petitions_all(self):
        nc = self.petcoll.find().count()
        i = 0
        for petition in self.petcoll.find():
            i += 1
            self.extract_petition(petition['url'], petition['slug'])
            print 'Processes petition %d of %d' % (i, nc)

    def merge_petitions(self):
        nc = self.petcoll.find().count()
        i = 0
        all = []
        for petition in self.petcoll.find():
            all.append(petition)

        for p in all:
            full = self.petfullcoll.find_one({'slug' : p['slug']})
            if full.has_key('title'):
                full['name'] = full['title']
                del full['title']
            if full.has_key('topic'):
                full['topic_id'] = full['topic']
                del full['topic']
            p.update(full)
            print p['slug']
            self.petcoll.save(p, safe=True)
        self.petcoll.remove({'dateshare' : {"$exists" : False}}, safe=True)


if __name__ == "__main__":
    ext = DataExtractor()
    ext.build_indexes()
#    ext.extract_short_petitions_all()
    ext.extract_full_petitions_all()
    ext.merge_petitions()


