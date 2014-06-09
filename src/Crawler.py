import sys
import json
import re
import requests
from collections import deque

class Crawler:
    # Static attributes
    PROFILE_URL = "https://www.linkedin.com/profile/view?id={id}"
    CONTACTS_PER_PROFILE = 10
    PROFILE_CONTACTS = "https://www.linkedin.com/profile/profile-v2-connections?id={id}&offset={offset}&count={per_profile}&distance=0&type=INITIAL"
    
    def __init__(self, login, password):
        # Open login page in order to avoid CSRF problems
        print("Opening sign in page...")
        login_page_info = requests.get("https://www.linkedin.com/uas/login?goback=&trk=hb_signin")
        login_page = login_page_info.text.replace("\n", " ")
        
        # Find the form
        m = re.search(r"<form action=\"https://www.linkedin.com/uas/login-submit\" method=\"POST\" name=\"login\" novalidate=\"novalidate\" id=\"login\" class=\"ajax-form\" data-jsenabled=\"check\">(?P<content>.*)</form>", login_page)
        if not m:
            raise Exception("Missing login form")
        inputs = re.findall(r"<input [^>]*name=\"(?P<name>[^\"]*)\" [^>]*value=\"(?P<value>[^\"]*)\"[^>]*>", m.group(1))
        
        # Find relevant fields details
        values = dict()
        for input_field in inputs:
            name = input_field[0]
            value = input_field[1]
            values[name] = value
        
        # Add login/password in the fields
        values["session_key"] = login
        values["session_password"] = password

        # Log in
        print "\nSigning in..."
        login_info = requests.post("https://www.linkedin.com/uas/login-submit", params=values, cookies=login_page_info.cookies)
        
        # Save cookies for next calls
        self.cookies = login_info.cookies
        self.already_asked = set()
        self.already_tested = set()
        self.to_be_tested = deque()
        self.crawl_from_connections_conditions = list()
        self.targets_full_profile = list()
        self.targets_short_profile = list()
    
    def add_to_be_tested(self, profile_details):
        """
        Add a profile in self.to_be_tested
        Perform checks before adding anything
        """
        if profile_details["id"] not in self.already_asked:
            # Check Crawl from connections conditions
            for condition in self.crawl_from_connections_conditions:
                if not condition.is_crawlable(profile_details):
                    return False

            # Update targets
            for target in self.targets_short_profile:
                target.check_if_targeted(profile_details)
            
            # This profile is correct, and added to 'to_be_tested' queue
            print "\t\t>", profile_details["details"]
            self.already_asked.add(profile_details["id"])
            self.to_be_tested.append(profile_details)
            return True
        else:
            return False
    
    def add(self, profile_id):
        """
        Add a profile in self.to_be_tested
        Perform checks before adding anything
        """
        return self.add_to_be_tested({"id": int(profile_id), "details": "N.A.", "depth": 0})
    
    def add_crawl_from_connections(self, condition):
        """
        Add a condition to verify when adding new profile to be crawled for data
        eg.: you only want to deal with profiles from company X
        eg.: you only want to deal with profiles of people with an A in their full name
        
        /!\ does not apply to profiles already in self.to_be_tested
        """
        self.crawl_from_connections_conditions.append(condition)
    
    def add_target_full_profile(self, target):
        """
        You are looking for someone you met on a fair. You know the company, the first name.
        Try to find its LinkedIn profile with this feature
        
        full profile requires to go on the person's profile
        """
        self.targets_full_profile.append(target)
    
    def add_target_short_profile(self, target):
        """
        Same as add_target_full_profile

        Does not need full profile but just some details: headline, fullname..
        """
        self.targets_short_profile.append(target)

    def has_next(self):
        """ Return True if it has at least one remaining profile id in self.to_be_tested """
        return True if self.to_be_tested else False
    
    def has_found_targets_full_profile(self):
        for target in self.targets_full_profile:
            if not target.has_found_target():
                return False
        return True
    
    def has_found_targets_short_profile(self):
        for target in self.targets_short_profile:
            if not target.has_found_target():
                return False
        return True

    def get_targets_full_profile(self):
        return self.targets_full_profile

    def get_targets_short_profile(self):
        return self.targets_short_profile

    def visit_next(self):
        """ Crawl the webpages corresponding to the next profile """
        
        new_contacts = 0

        # Visit profile webpage
        # Visited profile should receive a notification
        
        # Get id
        current = self.to_be_tested.popleft() # Remove in chronological order
        print "\n[%d/%d] Scanning %s - %s..." % (len(self.already_tested)+1, len(self.already_asked), current["id"], current["details"])
        self.already_tested.add(current["id"])

        # HTTP request and update cookies for next calls
        print "\tOpening profile: %s" % Crawler.PROFILE_URL.format(id=current["id"])
        contact_profile_info = requests.get(Crawler.PROFILE_URL.format(id=current["id"]), cookies=self.cookies)
        self.cookies = contact_profile_info.cookies
        
        # Retrieve profile details

        current = self.get_profile_details(current, contact_profile_info)
        
        # Update targets
        for target in self.targets_full_profile:
            target.check_if_targeted(current)

        # Retrive its contacts from JSON files
        
        new_contacts += self.get_next_contacts(current)
        print "\t%d new contacts" % new_contacts
    
    def get_profile_details(self, current, profile_webpage):
        # Find and analyse every json data included into the profile webpage
        # it contains data concerning current user details, endorsers..
        #with open("profile.html", "w+") as f:
        #    f.write(profile_webpage.text.encode("utf-8"))
        jsons_current_info = re.findall(r"(?P<json>\{[^}^{]*\})", profile_webpage.text.encode("utf-8"))
        json_objects = list()

        for js_current in jsons_current_info:
            try:
                json_objects.append(json.loads(js_current))
            except ValueError, e: # Invalid syntax
                #print "\tERROR > JSON from profile: Invalid syntax"
                continue
        
        del jsons_current_info
        
        # More user details
        for js_tmp in json_objects:
            # Check if the current JSON contains an user id
            try:
                memberID = int(js_tmp["memberID"])
            except KeyError:
                continue
            except ValueError: # for int(.)
                continue
            except TypeError: # for int(.)
                continue
            
            # Check if this user id is the one in current
            if memberID != current["id"]:
                continue
            
            # Add details to current user
            for key, value in js_tmp.items():
                if key not in current:
                    current[key] = value
                    #print "\t- %s: %s" % (unicode(key), unicode(value))
        
        # Companies and Schools
        for js_tmp in json_objects:
            if "title_highlight" in js_tmp and "companyName" in js_tmp:
                if "startdate_my" in js_tmp:
                    if "enddate_my" in js_tmp:
                        print "\t> Worked as '%s' for '%s', from %s until %s" % (js_tmp["title_highlight"], js_tmp["companyName"], js_tmp["startdate_my"], js_tmp["enddate_my"])
                    else:
                        print "\t> Worked as '%s' for '%s', from %s until <undefined>" % (js_tmp["title_highlight"], js_tmp["companyName"], js_tmp["startdate_my"])
                else:
                        print "\t> Worked as '%s' for '%s'" % (js_tmp["title_highlight"], js_tmp["companyName"])
            elif "educationId" in js_tmp and "schoolName" in js_tmp:
                print "\t> Studied at %s" % js_tmp["schoolName"]
        
        try:
            print "\tScanning <%s> profile" % current["fullname"]
        except KeyError:
            pass
        
        return current

    def get_next_contacts(self, current):
        """
        Retrieve contacts for current from LinkedIn JSON files
        Called by visit_next()
        """
        
        offset = 0
        new_contacts = 0
        current_contacts = []
        num_contacts_in_last_query = Crawler.CONTACTS_PER_PROFILE
        while num_contacts_in_last_query == Crawler.CONTACTS_PER_PROFILE:
            # HTTP request and update cookies for next calls
            print "\tGetting contacts list: %s" % Crawler.PROFILE_CONTACTS.format(id=current["id"], per_profile=Crawler.CONTACTS_PER_PROFILE, offset=offset)
            contact_contacts_info = requests.get(Crawler.PROFILE_CONTACTS.format(id=current["id"], per_profile=Crawler.CONTACTS_PER_PROFILE, offset=offset), cookies=self.cookies)
            self.cookies = contact_contacts_info.cookies

            # Update offset
            offset += Crawler.CONTACTS_PER_PROFILE
            
            print "\tParsing data"
            json_content = json.loads(contact_contacts_info.text.replace("\\\"", "")) # Quick trick to avoid problems with &quot;
            try:
                possible_new_contacts = json_content["content"]["connections"]["connections"]
            except KeyError, e:
                print "\tERROR > JSON file: no such content.connections.connections"
                #print "\tERROR > %s" % contact_contacts_info.text.encode('utf-8')
                break
            except ValueError, e:
                print "\tERROR > JSON file: no such content.connections.connections"
                #print "\tERROR > %s" % contact_contacts_info.text.encode('utf-8')
                break
            
            num_contacts_in_last_query = len(possible_new_contacts)

            for sub_contact in possible_new_contacts:
                # Get data from relevant fields
                # On failure: continue to next contact
                try:
                    headline = unicode(sub_contact["headline"]) # JSON can output: integers, None, strings, doubles..
                    memberID = int(sub_contact["memberID"])
                    distance = int(sub_contact["distance"])
                    full_name = unicode(sub_contact["fmt__full_name"])
                except KeyError, e:
                    print "\tERROR > JSON file: contact details - %s" % e
                    #print "\tERROR > %s" % sub_contact.encode('utf-8')
                    continue
                except ValueError, e:
                    print "\tERROR > JSON file: contact details - %s" % e
                    #print "\tERROR > %s" % sub_contact.encode('utf-8')
                    continue
                except TypeError, e:
                    print "\tERROR > JSON file: contact details - %s" % e
                    #print "\tERROR > %s" % sub_contact.encode('utf-8')
                    continue

                # Try to add the contact to the list to be tested
                if self.add_to_be_tested({"id": memberID, "details": "%s [%s][distance=%d]" % (full_name, headline.lower(), distance), "fullname": full_name, "headline": headline, "depth": current["depth"] +1}):
                    new_contacts += 1
        return new_contacts

