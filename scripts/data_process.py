#!/usr/bin/env python
# coding: utf8
"""
ROI.ru data processor
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
from bson import json_util
BASE_URL = 'http://roi.ru'
RAW_PATH = 'data/raw'
REFINED_PATH = 'data/refined'

MONGO_SERVER = 'localhost'
MONGO_PORT = 27017
MONGO_DB = 'roi'
PETITIONS_COLL = 'petitions'
PETFULL_COLL = 'petitions_full'
VOTEHISTORY_COLL = 'votehistory'
PROBE_COLL = 'probe'

class DataProcessor:
    """Data processor for ROI"""

    def __init__(self):
        self.conn = Connection(MONGO_SERVER, MONGO_PORT)
        self.db = self.conn[MONGO_DB]
        self.petcoll = self.db[PETITIONS_COLL]
        self.probecoll = self.db[PROBE_COLL]
        pass

    def calc_votes_stats_by_field(self, fieldname):
        items = {}
        for p in self.petcoll.find():
            key = p[fieldname]
            value = int(p['votes'])
            v = items.get(key, 0)
            items[key] = v + value
        return items

    def _save_stats(self, filename, data):
        items = []
        for k, v in data.items():
            items.append({'key': k, 'value': v})
        self.save_as_json(filename, items)

    def save_as_json(self, filename, items):
        f = open(filename, 'w')
        json.dump(items, f, indent=4,  default=json_util.default)
        f.close()

    def calc_votes_stats(self):
        self._save_stats(REFINED_PATH + '/autor_stats.json' , self.calc_votes_stats_by_field('autor_id'))
        self._save_stats(REFINED_PATH + '/topic_stats.json' , self.calc_votes_stats_by_field('topic_id'))
        self._save_stats(REFINED_PATH + '/jurisdiction_stats.json' , self.calc_votes_stats_by_field('jurisdiction'))
        self._save_stats(REFINED_PATH + '/vote_throttle_stats.json' , self.calc_votes_throttle())
        self._save_stats(REFINED_PATH + '/vote_predict_stats.json' , self.calc_votes_predict())
        self.save_as_json(REFINED_PATH + '/vote_predict_by_probe.json' , self.calc_votes_by_probe())

    def calc_votes_throttle(self):
        items = {}
        for p in self.petcoll.find():
            delta = p['probe_date'] - p['start_date']
            seconds = delta.total_seconds()
            value = int(p['votes'])
            items[p['url']] = float(value * 100.0 / seconds)
        return items

    def calc_votes_predict(self):
        items = {}
        for p in self.petcoll.find():
            delta = p['probe_date'] - p['start_date']
            seconds = delta.total_seconds()
            value = int(p['votes'])
            throttle = float(value * 100.0 / seconds)
            delta2 = p['end_date'] - p['probe_date']
            seconds2 = delta2.total_seconds()
            votes2 = (throttle / 100.0) * seconds2
            items[p['url']] = votes2 + value
        return items

    def calc_votes_by_probe(self):
        items = []
        for p in self.petcoll.find():
            num = self.probecoll.find({'slug': p['slug']}).count()
            if num < 2:
                continue
            for v in self.probecoll.find({'slug': p['slug']}):
                print v
            print '---'
            first = self.probecoll.find({'slug': p['slug']}).sort('probe_date', -1)[0]
            last = self.probecoll.find({'slug': p['slug']}).sort('probe_date', 1)[0]
            timedelta = first['probe_date'] - last['probe_date']
            votedelta = int(first['votes']) - int(last['votes'])
            seconds = timedelta.total_seconds()

            if seconds == 0: continue
            throttle = float(votedelta) / seconds
            daythrottle = throttle * 60*60*24
            timedelta2 = p['end_date'] - first['probe_date']
            seconds2 = timedelta2.total_seconds()
            votes2 = throttle  * seconds2
            predict = int(p['votes']) + votes2
            print 'Predict', predict, 'added', votes2

            items.append({'slug' : p['slug'], 'name' : p['name'], 'url' : p['url'], 'throttle' : daythrottle, 'votes' : p['votes'], 'predicted' : predict})
        return items

if __name__ == "__main__":
    ext = DataProcessor()
    ext.calc_votes_stats()



