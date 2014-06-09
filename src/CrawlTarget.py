
class CrawlTarget:
    """
    Defines a specific target
    
    For instance, you met someone on a student fair but forgot to take its full name
    you know:
     * first name
     * company name
     * position
    
    You just need to define correctly CrawlTarget in order to find this target
    """

    def __init__(self, conditions):
        """
        conditions is a dict()

        It contains keys that refer to their equivalent key in profile_details
        and compiled regex that will be run when calling check_if_targeted
        """
        self.conditions = conditions
        self.profile_details = None

    def check_if_targeted(self, profile_details):
        for key, value in self.conditions.items():
            try:
                profile_value = profile_details[key]
            except KeyError:
                print "\t\tERROR: No key '%s'" % key
                return False
            if not value.search(unicode(profile_value).lower()):
                return False
        
        print "\t\t** Target FOUND **"
        self.profile_details = profile_details
        return True

    def has_found_target(self):
        return self.profile_details != None

    def get_target(self):
        return self.profile_details

