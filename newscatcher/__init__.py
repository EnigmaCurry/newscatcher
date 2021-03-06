__version__ = '0.2.0'

# Retrieve and analyze
# 24/7 streams of news data
import sqlite3
#import requests
import feedparser
import pkg_resources
from tldextract import extract

DB_FILE = pkg_resources.resource_filename('newscatcher', 'data/package_rss.db')


class Query:
    # Query class used to build subsequent sql queries
    def __init__(self):
        self.params = {'website': None, 'topic': None}

    def build_conditional(self, field, sql_field):
        # single conditional build
        field = field.lower()
        sql_field = sql_field.lower()

        if self.params[field] != None:
            conditional = "{} = '{}'".format(sql_field, self.params[field])
            return conditional
        return

    def build_where(self):
        # returning the conditional from paramters
        # the post "WHERE"
        conditionals = []

        conv = {'topic': 'topic_unified', 'website': 'clean_url'}

        for field in conv.keys():
            cond = self.build_conditional(field, conv[field])
            if cond != None:
                conditionals.append(cond)

        if conditionals == []:
            return

        conditionals[0] = 'WHERE ' + conditionals[0]
        conditionals = ''' AND '.join([x for x in conditionals if x != None])
		+ ' ORDER BY IFNULL(Globalrank,999999);'''

        return conditionals

    def build_sql(self):
        # build sql on user qeury
        db = sqlite3.connect(DB_FILE, isolation_level=None)
        sql = 'SELECT rss_url from rss_main ' + self.build_where()

        db.close()
        return sql


def clean_url(dirty_url):
    # website.com
    dirty_url = dirty_url.lower()
    o = extract(dirty_url)
    return o.domain + '.' + o.suffix


class Newscatcher:
    # search engine
    def build_sql(self):
        if self.topic is None:
            sql = '''SELECT rss_url from rss_main 
					 WHERE clean_url = '{}';'''
            sql = sql.format(self.url)
            return sql

    def __init__(self, website, topic=None):
        # init with given params
        self.website = website.lower()
        self.url = clean_url(self.website)
        self.topic = topic

    def get_headlines(self, n=None):
        if self.topic is None:
            sql = '''SELECT rss_url,topic_unified, language, clean_country from rss_main 
					 WHERE clean_url = '{}' AND main = 1;'''
            sql = sql.format(self.url)
        else:
            sql = '''SELECT rss_url, topic_unified, language, clean_country from rss_main 
					 WHERE clean_url = '{}' AND topic_unified = '{}';'''
            sql = sql.format(self.url, self.topic)

        db = sqlite3.connect(DB_FILE, isolation_level=None)

        try:
            rss_endpoint, topic, language, country = db.execute(sql).fetchone()
            feed = feedparser.parse(rss_endpoint)
        except:
            if self.topic is not None:
                sql = '''SELECT rss_url from rss_main 
					 WHERE clean_url = '{}';'''
                sql = sql.format(self.url)

                if len(db.execute(sql).fetchall()) > 0:
                    db.close()
                    raise AssertionError(f'Topic is not supported: {self.topic}')
                else:
                    raise AssertionError(f'Website is not supported: {self.website}')
                    db.close()
            else:
                raise AssertionError(f'Website is not supported: {self.website}')

        if feed['entries'] == []:
            db.close()
            raise AssertionError('\nNo headlines found check internet connection or query parameters\n')

        title_list = []
        for article in feed['entries']:
            if 'title' in article:
                title_list.append(article['title'])
            if n != None:
                if len(title_list) == n:
                    break

        return title_list

    def print_headlines(self, n=None):
        headlines = self.get_headlines(n)

        i = 1
        for headline in headlines:
            if i < 10:
                print(str(i) + '.   |  ' + headline)
                i += 1
            elif i in list(range(10, 100)):
                print(str(i) + '.  |  ' + headline)
                i += 1
            else:
                print(str(i) + '. |  ' + headline)
                i += 1

    def get_news(self, n=None):
        # return results based on current stream
        if self.topic is None:
            sql = '''SELECT rss_url,topic_unified, language, clean_country from rss_main 
					 WHERE clean_url = '{}' AND main = 1;'''
            sql = sql.format(self.url)
        else:
            sql = '''SELECT rss_url, topic_unified, language, clean_country from rss_main 
					 WHERE clean_url = '{}' AND topic_unified = '{}';'''
            sql = sql.format(self.url, self.topic)

        db = sqlite3.connect(DB_FILE, isolation_level=None)

        try:
            rss_endpoint, topic, language, country = db.execute(sql).fetchone()
            feed = feedparser.parse(rss_endpoint)
        except:
            if self.topic is not None:
                sql = '''SELECT rss_url from rss_main 
					 WHERE clean_url = '{}';'''
                sql = sql.format(self.url)

                if len(db.execute(sql).fetchall()) > 0:
                    db.close()
                    raise AssertionError(f'Topic is not supported: {self.topic}')
                else:
                    db.close()
                    raise AssertionError(f'Website is not supported: {self.website}')
            else:
                raise AssertionError(f'Website is not supported: {self.website}')

        if feed['entries'] == []:
            db.close()
            raise AssertionError('\nNo results found check internet connection or query parameters\n')
            return

        if n == None or len(feed['entries']) <= n:
            articles = feed['entries']  # ['summary']#[0].keys()
        else:
            articles = feed['entries'][:n]

        db.close()
        return {'url': self.url, 'topic': topic,
                'language': language, 'country': country, 'articles': articles}


def describe_url(website):
    # return newscatcher fields that correspond to the url
    website = website.lower()
    website = clean_url(website)
    db = sqlite3.connect(DB_FILE, isolation_level=None)

    sql = "SELECT clean_url, language, clean_country, topic_unified, rss_url from rss_main WHERE clean_url = '{}' and main == 1 ".format(
        website)
    results = db.execute(sql).fetchone()
    if results is None:
        raise AssertionError(f"No url in database for: {website}")
    main = results[-1]

    if main == None or len(main) == 0:
        raise AssertionError(f'Website not supported: {website}')

    sql = "SELECT DISTINCT topic_unified from rss_main WHERE clean_url == '{}'".format(website)
    topics = db.execute(sql).fetchall()
    topics = [x[0] for x in topics]

    ret = {'url': results[0], 'language': results[1], 'country': results[2], 'main_topic': main, 'topics': topics, 'rss_url': results[4] }

    return ret


def urls(topic=None, language=None, country=None):
    # return urls that matches users parameters
    if language != None:
        language = language.lower()

    if country != None:
        country = country.upper()

    if topic != None:
        topic = topic.lower()

    db = sqlite3.connect(DB_FILE, isolation_level=None)
    quick_q = Query()
    inp = {'topic': topic, 'language': language, 'country': country}
    for x in inp.keys():
        quick_q.params[x] = inp[x]

    conditionals = []
    conv = {'topic': 'topic_unified', 'website': 'clean_url',
            'country': 'clean_country', 'language': 'language'}

    for field in conv.keys():
        try:
            cond = quick_q.build_conditional(field, conv[field])
        except:
            cond = None

        if cond != None:
            conditionals.append(cond)

    sql = ''

    if conditionals == []:
        sql = 'SELECT clean_url from rss_main '
    else:
        conditionals[0] = ' WHERE ' + conditionals[0]
        conditionals = ' AND '.join([x for x in conditionals if x is not None])
        conditionals += ' AND main = 1 ORDER BY IFNULL(Globalrank,999999);'
        sql = 'SELECT DISTINCT clean_url from rss_main' + conditionals

    ret = db.execute(sql).fetchall()
    if len(ret) == 0:
        raise AssertionError('\nNo websites found for given parameters\n')

    db.close()
    return [x[0] for x in ret]

def add_url(url, rss_url, topic="news", language="en", country="US", main=True):
    db = sqlite3.connect(DB_FILE, isolation_level=None)
    main = 1 if main else 0
    sql = f'INSERT INTO rss_main (clean_url, language, topic_unified, main, clean_country, rss_url, GlobalRank) VALUES ("{url}", "{language}", "{topic}", {main}, "{country}", "{rss_url}", 0)'
    db.execute(sql)

def remove_url(url, topic=None):
    db = sqlite3.connect(DB_FILE, isolation_level=None)
    sql = f'DELETE FROM rss_main WHERE clean_url="{url}"'
    if topic:
        sql += f' and topic_unified="{topic}"'
    db.execute(sql)

