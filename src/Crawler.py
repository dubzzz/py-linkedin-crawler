import sys
import json
import re
import requests
from collections import deque

class Crawler:
    # Static attributes
    DEPTH_FIRST_SEARCH = 0
    BREADTH_FIRST_SEARCH = 1
    RANDOM_SEARCH = 2
    PROFILE_URL = "https://www.linkedin.com/profile/view?id={id}"
    CONTACTS_PER_PROFILE = 10
    PROFILE_CONTACTS = "https://www.linkedin.com/profile/profile-v2-connections?id={id}&offset={offset}&count={per_profile}&distance=0&type=INITIAL"
    
    def __init__(self, login, password):
        # Open login page in order to avoid CSRF problems
        print("Openning sign in page...")
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
    
    def add_to_be_tested(self, profile_details):
        """
        Add a profile in self.to_be_tested
        Perform checks before adding anything
        """
        if profile_details["id"] not in self.already_asked:
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
        return self.add_to_be_tested({"id": int(profile_id), "details": "N.A."})

    def has_next(self):
        """ Return True if it has at least one remaining profile id in self.to_be_tested """
        return True if self.to_be_tested else False

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

        # Retrive its contacts from JSON files
        
        new_contacts += self.get_next_contacts(current)
        print "\t%d new contacts" % new_contacts

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
                if self.add_to_be_tested({"id": memberID, "details": "%s [%s][distance=%d]" % (full_name, headline.lower(), distance)}):
                    new_contacts += 1
        return new_contacts

