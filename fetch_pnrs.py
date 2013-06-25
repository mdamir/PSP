import sys
import json
import urllib2
from time import time,sleep
from pymongo import *
import datetime

MONGO_IP = 'localhost:27017,localhost:27018,localhost:27019'
con = ReplicaSetConnection(MONGO_IP, replicaSet="rs1", read_preference=ReadPreference.SECONDARY)
#con = Connection('localhost',27017)
db = con['PSP']
col = db['pnr_details']
col_processed = db['pnr_processed']
# Create indices
#col.ensure_index("pnr")
#col_processed.ensure_index("pnr")

class Get_pnrs:
    URL = 'http://pnrapi.alagu.net/api/v1.0/pnr/'
    SECONDS_IN_HOUR = 3600
    def __init__(self):
        pass

    def get_json_response(self,pnr):
        # Wait if current time is between 11:30pm and 12:30am
        current_time = datetime.datetime.time(datetime.datetime.now())
        if current_time > datetime.time(23,29):
            print 'Current time is: ',str(current_time),'.All train queries down now, hence sleeping for one and half hour...'
            sleep(self.SECONDS_IN_HOUR * 1.5)
            print 'Woke up now'
            print 'Now the time is: ',datetime.datetime.time(datetime.datetime.now())
        url = self.URL + str(pnr)
        req = self.add_requests_to_url(url)
        try:
            url_response = urllib2.urlopen(req)
        except urllib2.URLError:
            print 'No net connection...Will resume when the net connection works again'
            self.wait_until_no_net()
            url_response = urllib2.urlopen(req)
        except:
            print 'Following error encountered while processing pnr: ',pnr
            print "Unexpected error:", sys.exc_info()[0]
            #raise
            return {} # No response from api
        response = url_response.read()
        json_response = json.loads(response)
        return json_response

    def add_requests_to_url(self,url):
        url = url.encode('utf-8')
        user_agent = "Mozilla/5.0 (Macintosh; U; Intel Mac OS X 10_6_7; en-us) AppleWebKit/533.21.1 (KHTML, like Gecko) Version/5.0.5 Safari/533.21.1"
        hdrs = {
                'Host': url.replace('http://',''),
                'User-Agent' : user_agent,
                'Accept-Encoding' : 'gzip',
                'Connection': 'keep-alive',
                'Keep-Alive':'115',
                }
        req = urllib2.Request(url, None, {'User-Agent' : user_agent,})
        return req
        
    def wait_until_no_net(self):
        test_url = 'http://pnrapi.alagu.net/api/v1.0/pnr/2510407794'
        sleeping_time = 60 # one minute
        max_sleeping_time = self.SECONDS_IN_HOUR * 4 # 4 hours
        no_net = True
        while no_net:
            print "current time is: ", str(datetime.datetime.time(datetime.datetime.now()))
            print "sleeping for ",sleeping_time,' seconds...'
            sleep(sleeping_time)
            print "Woke up at: ", str(datetime.datetime.time(datetime.datetime.now()))
            req = self.add_requests_to_url(test_url)
            no_net = False
            try:
                url_response = urllib2.urlopen(req)
            except urllib2.URLError:
                no_net = True
                sleeping_time *= 2
                if sleeping_time >= max_sleeping_time:
                    sleeping_time = self.SECONDS_IN_HOUR
            if not no_net:
                return


    def test_pnr_api(self):
        valid_pnr = 2510407794
        resp = self.get_json_response(valid_pnr)
        if "status" in resp and resp["status"] == "OK" and "data" in resp and resp["data"]:
            print 'Response for valid pnr query is: '
            print resp
            resp = self.decorate(resp)
            print 'decorated response is: '
            print resp

    def generate_pnrs_and_store_results(self):
        # define some metrics to get some stats
        pnrs_processed_before = 0
        total_pnrs_processed = 0
        valid_pnrs_count = 0
        start_time = time()
        already_processed = False
        # Get some pnrs for which few numbers are hidden (from http://pnr.net.in and http://indiarailinfo.com/pnr )
        last_7 = ['9218236','7799747','0407796']
        first_3 = ['251','652','612','642']
        #first_3 = ['456','251','843','281','661','224','861','811','831','652','224','271','466','244','425','480','234','271','642','612','821','415','214','871','470']
        #for i in reversed(range(1,407795)): 
        for i in range(422629,10000000): 
            for prefix in first_3:
                suffix = str(i).zfill(7)
                pnr_no = prefix + suffix
                #try:
                #    already_processed = col_processed.find_one({'pnr':pnr_no})
                #except:
                #    print 'cannot find any entry hence going to next'
                #if already_processed:
                #        pnrs_processed_before += 1
                #        continue
                total_pnrs_processed += 1
                try:
                    resp = self.get_json_response(pnr_no)
                    # Check if pnr is valid
                    if "status" in resp and resp["status"] == "OK" and "data" in resp and resp["data"]:
                        valid_pnrs_count += 1
                        decorated_resp = self.decorate(resp)
                        # Insert this pnr into journey only if the journey date has not passed
                        if decorated_resp["days_left"] > 0:
                            col.insert(decorated_resp)
                        col_processed.insert({'pnr':pnr_no,'valid':True})
                    else:
                        col_processed.insert({'pnr':pnr_no,'valid':False})
                except:
                    #raise
                    print 'exception occurred while processing pnr: ',pnr_no
                if total_pnrs_processed % 10 == 0:
                    print 'total pnrs processed is: ',total_pnrs_processed,' and valid pnrs are: ',valid_pnrs_count
        print 'Processed all of them...'
        print 'total pnrs processed is: ',total_pnrs_processed,' and valid pnrs are: ',valid_pnrs_count

    def decorate(self,json):
        json = json["data"]
        dt = json["travel_date"]["date"].strip()
        splitted_date = dt.split('-')
        travel_date = datetime.date(int(splitted_date[2]), int(splitted_date[1]), int(splitted_date[0]))
        days_remaining = (travel_date - datetime.date.today()).days
        json["travel_date"] = str(travel_date)
        json['days_left'] = days_remaining
        json['pnr'] = json['pnr_number']
        del json['alight']
        del json['board']
        del json['pnr_number']
        current_time = str(datetime.datetime.now())
        json["last_checked"] = current_time
        return json

                
if __name__ == "__main__":
    pnr_response = Get_pnrs()
    pnr_response.generate_pnrs_and_store_results()
    #pnr_response.test_pnr_api()
