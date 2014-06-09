#!/usr/bin/python
# -*- coding: utf-8 -*-

# Sample of code to show how to use Crawler
# to crawl LinkedIn profiles
#
# Derive this file to make your own crawler

import getpass
import re
import sys
import time

from Crawler import Crawler
from CrawlConditions import CrawlConditions
from CrawlTarget import CrawlTarget

sleep_time = 15

long_sleep_every = 100 #profiles
long_sleep_time = 38500

max_profiles = 10

# Check sys.argv

if len(sys.argv) != 3:
    print "SYNTAX: ./scan.py <email address> <first profile>"
    exit(1)
try:
    first_profile_id = int(sys.argv[2])
except ValueError:
    print "SYNTAX: ./scan.py <email address> <first profile>"
    print "\t<first profile> must be an integer"
    exit(2)
except TypeError:
    print "SYNTAX: ./scan.py <email address> <first profile>"
    print "\t<first profile> must be an integer"
    exit(3)

# LinkedIn login credentials

login = sys.argv[1]
print "Login: %s" % login
password = getpass.getpass("Password : ")

# Create the Crawler

num_scans = 0
crawler = Crawler(login, password)
crawler.add(sys.argv[2])

# Crawl for profiles with
# profile headline contains 'wonderful company'
#crawler.add_crawl_from_connections(CrawlConditions({"headline": re.compile(r'wonderful company')}))
# profile headline contains 'recruiter', taken into account for depth >= 2
#crawler.add_crawl_from_connections(CrawlConditions({"headline": re.compile(r'recruiter')}, 2))
# ->: means connection
# eg.: A (initial profile) -> AA (accountant for wonderful company) [depth=1] -> AAA (accountant for wonderful company) [depth=2] **IGNORED**
#                          -> AB (accountant for wonderful company) [depth=1] -> ABA (recruiter for wonderful company) [depth=2]  **OK**

# Crawl in order to find someone called Patrick working at 'wonderful company'
crawler.add_target_short_profile(CrawlTarget({"fullname": re.compile(r'patrick'), "headline": re.compile(r'wonderful company')}))
# and someone called Charles whose work location is France
crawler.add_target_full_profile(CrawlTarget({"fullname": re.compile(r'charles'), "fmt_location": re.compile(r'france')}))
# /!\ NO CAPITAL LETTERS

while num_scans < max_profiles and crawler.has_next():
    # In case of big sleep
    if num_scans != 0 and num_scans % long_sleep_every == 0:
        num_loops = long_sleep_time/60
        for i in range(num_loops):
            print "Waiting... %d/%d" % (i, num_loops)
            time.sleep(60)
    
    # Sleep between each profile
    num_scans += 1
    time.sleep(sleep_time)
    
    # Visit next profile
    crawler.visit_next()

    # Check if it finds all targets for short profile
    # and for full profile
    if crawler.has_found_targets_short_profile() and crawler.has_found_targets_full_profile():
        print "\nFound from short profiles: "
        targets_sp = crawler.get_targets_short_profile()
        for t in targets_sp:
            print "*", t.get_target()
        
        print "\nFound from full profiles: "
        targets_fp = crawler.get_targets_full_profile()
        for t in targets_fp:
            print "*", t.get_target()

        exit(0)

