#!/usr/bin/python
#
import sys
import grequests
import time
import codecs
from bs4 import BeautifulSoup
import re
import pprint

chached = [
        ['http://www.spareroom.co.uk/flatshare/london', 'cached1.html', None],
        ['http://www.spareroom.co.uk/flatshare/london/page11', 'cached2.html', None],
        ['http://www.spareroom.co.uk/flatshare/london/page1372', 'cached4.html', None],
        ]

room_out = None
float_out = None
retry_list = []

#
# check if url is cached
#
def get_chached(url):
    for i in range(0,len(chached)):
        if chached[i][0]==url:
            return True,chached[i][2]
    return False,None

#
# load all cached pages and download any new ones
#
def cache_pages():    
    for i in range(0,len(chached)):
        url = chached[i][0]
        fname = chached[i][1]

        try:
            file = codecs.open(fname, 'r',encoding='utf8')
        except IOError:
            file = None

        if not file:
            print 'cache miss'
            req = grequests.get(url)
            res = grequests.map([req])

            r = res[0]
            if r.status_code==200:
                chached[i][2] = r.text
                file = codecs.open(fname,'w',encoding='utf8')
                file.write(r.text)
                file.close()
        else:
            print 'cache hit'
            chached[i][2] = file.read()
            file.close()

#
#
#
def print_res(res, **kwargs):

    print '[%s] %s %s bytes: %r' % (res.status_code, res.url, len(res.text), res.text[:30])
    res.close()

#
# get number of listings from spareroom
#
def get_num_results(soup):
    res = soup.find_all(id='results_header')

    if res:
        if len(res)>1:
            print 'Warning:More than one results header found(using first).'
        r = res[0]
        
        m = re.match(r'\s+Showing\s+\d+\-\d+\s+of\s+(\d+)', res[0].text)
        if m:
            num = m.group(1)
            return num
        else:
            print 'error:match failed.'
            return None
    else:
        print 'Error:No results header found'
    return None

test_txt = """	
	3 bed
	
	
	
	Flat
	
"""

#
#
#
def get_span_text(tag):

    res = tag.text.strip().replace('\n',' ').split()
    out = ''
    for i in range(0,len(res)):
        out = out + ' ' + res[i]
    return out.strip()
#    m = re.match(r'\s*(.+)',tag.text)
#    if m:
#        return m.group(1).strip()
#    print 'Parse error in span text.(%s)' % tag.txt
#    return None

def get_listing_area(content):
    txt = get_span_text(content[0])
    m = re.match(r"([\w\s']+)\s+\(([\w\d]+)\)",txt)
    if m:
        area = m.group(1)
        postcode = m.group(2)
        return (False,area,postcode)
    print 'Parse error(listing_location_content). (%s)' % txt
    return (True,None,None)

def get_listing_avail(soup):
    content = soup.find_all("span", class_="listing_availability")
    available = ''
    if content:
        available = get_span_text(content[0])
    return available


def get_listing_bills(soup):
    content = soup.find_all("span", class_="listing_bills_inc")
    billsinc = ''
    if content:
        billsinc = get_span_text(content[0])
    return billsinc


def get_listing_room(soup):
    content = soup.find_all("a", class_="listing_rooms")
    error = False
    room = False
    single = '0'
    double = '0'
    other = None

    if content:
        room = True
        txt = get_span_text(content[0]).lower()

        # check for 1 single room
        if txt=='single room':
            # 1 single room
            single = '1'
        
        # check for 1 double room
        elif txt=='double room':
            double = '1'
        
        # check for single and double rooms together
        elif '+' in txt:
            m = re.match(r'(\d*)\s*singles*\+(\d*)',txt)
            if m:
                if m.group(1)=='':
                    single = '1'
                else:
                    single = m.group(1)
                if m.group(2)=='':
                    double = '1'
                else:
                    double = m.group(2)
            else:
                print 'parse error(listing_rooms) (%s)' % txt
                error = True
        
        # check for multiple single or double rooms
        elif 'singles' in txt or 'doubles' in txt:
            m = re.match(r'(\d+)\s+(\w+)',txt)
            if m:
                if m.group(2)=='singles':
                    single = m.group(1)
                elif m.group(2)=='doubles':
                    double = m.group(1)
                else:
                    print 'parse error(listing_rooms) (%s)' % txt
                    error = True
            else:
                print 'parse error(listing_rooms) (%s)' % txt
                error = True

        # check for flat/house/studio
        #elif 'Flat' in txt or 'House' in txt or 'flat' in txt:
        else:
            room = False
            other = txt
        
        # unknown listing type (should not get here)
        #else:
        #    print 'error in listing_rooms txt (%s)' % txt
        #    error = True
    else:
        print 'parse error(listing_rooms no content)'
        error = True

    return (error,room,single,double,other)



def get_listing_price(soup):
    content = soup.find_all("a", class_="listing_price")
    error = False
    multi = False
    price = '0'
    higherprice = '0'
    lowerprice = '0'
    period = ''

    if content:
        txt = get_span_text(content[0])
        
        # check if price is a range
        if "-" in txt:
            m = re.match(ur'\xA3(\d+)-(\d+)(\w+)',txt,re.UNICODE)
            if m:
                multi = True
                lowerprice = m.group(1)
                higherprice = m.group(2)
                period = m.group(3)
                if period=='pw':
                    higherprice = str(int(higherprice)*52/12)
                    lowerprice = str(int(lowerprice)*52/12)
                    period = 'pcm'
            else:
                print "parse error(listing_price)."
                error = True

        # price has single value
        else:
            m = re.match(ur'\xA3(\d+)\s*(\w+)',txt,re.UNICODE)
            if m:
                price = m.group(1)
                period = m.group(2)
                if period=='pw':
                    price = str(int(price)*52/12)
                    period = 'pcm'
                lowerprice = higherprice = price
            else:
                print "parse error(listing_price)."
                error = True
    else:
        print 'parse error(listing_price).'
        error = True

    return (error,multi,price,higherprice,lowerprice,period)


def open_output():
    global room_out, flat_out
    room_out = codecs.open('rooms.csv','w','utf-8')
    room_out.write(u'ID,AREA,POSTCODE,SINGLE,DOUBLE,BILLS,PRICE\n')

    flat_out = codecs.open('flats.csv','w','utf-8')
    flat_out.write(u'ID,AREA,POSTCODE,TYPE,PRICE\n')

def close_output():
    global room_out, flat_out
    if room_out != None:
        room_out.close()
        room_out = None
    if flat_out != None:
        flat_out.close()
        flat_out = None
#
#
#
def output_room(listing_id,area,postcode,single,double,price,billsinc):
    if billsinc=="Bills inc.":
        billsinc="Yes"
    else:
        billsinc="No"
    room_out.write(u'%s, "%s", %s, %s, %s, %s, %s\n' % (listing_id,area,postcode,single,double,billsinc,price))


def output_flat(listing_id,area,postcode,name,price):
    flat_out.write(u'%s, "%s", %s, "%s", %s' % (listing_id,area,postcode,name,price))

total_singles = 0
total_doubles = 0

#
#
#
def parse_page(soup):
    global total_doubles,total_singles

    res = soup.find_all("li", class_="listing_result")
    for i in range(0,len(res)):
        error = False
        soup = res[i]

        # area and postcode
        #
        content = soup.find_all("span", class_="listing_location_content")
        if content:
            error,area,postcode = get_listing_area(content)
        else:
            # skip past ads
            continue
        
        # listing id
        #
        txt = soup.attrs['data-href'].split('/')[-1]
        if txt.startswith('fad_click'):
            m = re.search(r'fad_id\=(\d+)',txt)
            if m:
                listing_id = m.group(1)
            else:
                print 'parse error(data_href) (%s)' % txt
        elif txt.startswith('javascript'):
            listing_id = 'not available'
        else:
            listing_id = txt

        # availablity
        #
        available = get_listing_avail(soup)

        # bills inc
        #
        billsinc = get_listing_bills(soup)

        # get room(s) type
        #
        error,room,single,double,other = get_listing_room(soup)
        
        # get price
        #
        error,multi,price,higherprice,lowerprice,period = get_listing_price(soup)

        if room:
            s = int(single)
            d = int(double)
            total_doubles+=d
            total_singles+=s
            if multi or s+d>1:

                #print "singles=%s, doubles=%s" % (single,double)
                if s+d==2:
                    # 2 single rooms
                    if s==2:
                        output_room(listing_id,area,postcode,'1','0',lowerprice,billsinc)
                        output_room(listing_id,area,postcode,'1','0',higherprice,billsinc)
                        #print '%s(%s) id(%s) Single(1) - Double(0) %s %s %s pcm' % (area,postcode,listing_id,billsinc,available,lowerprice)
                        #print '%s(%s) id(%s) Single(1) - Double(0) %s %s %s pcm' % (area,postcode,listing_id,billsinc,available,higherprice)

                    # 1 single & 1 doub;e
                    elif s==1:
                        output_room(listing_id,area,postcode,'1','0',lowerprice,billsinc)
                        output_room(listing_id,area,postcode,'0','1',higherprice,billsinc)
                        #print '%s(%s) id(%s) Single(1) - Double(0) %s %s %s pcm' % (area,postcode,listing_id,billsinc,available,lowerprice)
                        #print '%s(%s) id(%s) Single(0) - Double(1) %s %s %s pcm' % (area,postcode,listing_id,billsinc,available,higherprice)

                    # 2 doubles
                    else:
                        output_room(listing_id,area,postcode,'0','1',lowerprice,billsinc)
                        output_room(listing_id,area,postcode,'0','1',higherprice,billsinc)
                        #print '%s(%s) id(%s) Single(0) - Double(1) %s %s %s pcm' % (area,postcode,listing_id,billsinc,available,lowerprice)
                        #print '%s(%s) id(%s) Single(0) - Double(1) %s %s %s pcm' % (area,postcode,listing_id,billsinc,available,higherprice)

                # 1 single and x doubles
                elif s==1:
                    output_room(listing_id,area,postcode,'1','0',lowerprice,billsinc)
                    #print '%s(%s) id(%s) Single(1) - Double(0) %s %s %s pcm' % (area,postcode,listing_id,billsinc,available,lowerprice)
                    for i in range(0,d):
                        output_room(listing_id,area,postcode,'0','1',higherprice,billsinc)
                        #print '%s(%s) id(%s) Single(0) - Double(1) %s %s %s pcm' % (area,postcode,listing_id,billsinc,available,higherprice)

                # 0 singles & x doubles
                elif s==0:
                    output_room(listing_id,area,postcode,'0','1',lowerprice,billsinc)
                    #print '%s(%s) id(%s) Single(0) - Double(1) %s %s %s pcm' % (area,postcode,listing_id,billsinc,available,lowerprice)
                    for i in range(0,d-1):
                        output_room(listing_id,area,postcode,'0','1',higherprice,billsinc)
                        #print '%s(%s) id(%s) Single(0) - Double(1) %s %s %s pcm' % (area,postcode,listing_id,billsinc,available,higherprice)

                # x single 0 doubles
                elif d==0:
                    output_room(listing_id,area,postcode,'1','0',lowerprice,billsinc)
                    #print '%s(%s) id(%s) Single(1) - Double(0) %s %s %s pcm' % (area,postcode,listing_id,billsinc,available,lowerprice)
                    for i in range(0,s-1):
                        output_room(listing_id,area,postcode,'1','0',higherprice,billsinc)
                        #print '%s(%s) id(%s) Single(1) - Double(0) %s %s %s pcm' % (area,postcode,listing_id,billsinc,available,higherprice)
                    
                # x single & x doubles
                else:
                    for i in range(0,s):
                        output_room(listing_id,area,postcode,'1','0',lowerprice,billsinc)
                        #print '%s(%s) id(%s) Single(1) - Double(0) %s %s %s pcm' % (area,postcode,listing_id,billsinc,available,lowerprice)
                    for i in range(0,d):
                        output_room(listing_id,area,postcode,'0','1',higherprice,billsinc)
                        #print '%s(%s) id(%s) Single(0) - Double(1) %s %s %s pcm' % (area,postcode,listing_id,billsinc,available,higherprice)
            
            # one room single or double
            else:
                if int(single)+int(double)>1:
                    print "too many rooms, single=%s, double=%s in listing id=%s" % (single,double,listing_id)
                output_room(listing_id,area,postcode,single,double,price,billsinc)
                #print '%s(%s) id(%s) Single(%s) - Double(%s) %s %s %spcm' % (area,postcode,listing_id,single,double,billsinc,available,price)
        else:
            output_flat(listing_id,area,postcode,other,price)
            #print '%s(%s) id(%s) %s %s %s %spcm' % (area,postcode,listing_id,other,billsinc,available,price)




#
#
#
def parse_response(res, **kwargs):

    print '[%s] %s %s bytes' % (res.status_code, res.url, len(res.text))
    if res.status_code==200:
        content = res.text
        res.close()
        soup = BeautifulSoup(content)
        parse_page(soup)
    elif res.status_code==503:
        retry_list.append(res.url)


def load():

    t0 = time.time()

#    urls = [
#        'http://www.spareroom.co.uk/flatshare/london/page6', 
#    ]

    urls = []
    for i in range(1,1380):
        urls.append('http://www.spareroom.co.uk/flatshare/london/page%s' % str(i))

    rs = (grequests.get(u, stream=False,hooks={'response':parse_response}) for u in urls)
    res = grequests.map(rs,stream=False,size=75)


    for i in range(0,10):
        if len(retry_list)==0:
            break
        print "retry %d pages attempt number %d" % (len(retry_list),i)
        time.sleep(25+i*3)
        rs = (grequests.get(u, stream=False,hooks={'response':parse_response}) for u in retry_list)
        retry_list = []
        res = grequests.map(rs,stream=False,size=25)
    
    
    t1 = time.time()
    print '%d pages parsed in %f secs' % (len(urls),(t1-t0))
    print 'doubles:%d, singles:%s' % (total_doubles,total_singles)

def test():

    cache_pages()
    isc, c = get_chached('http://www.spareroom.co.uk/flatshare/london/page1372')
    if isc:
        soup = BeautifulSoup(c)

        print get_num_results(soup)
        parse_page(soup)

open_output()
#load()
test()

close_output()
