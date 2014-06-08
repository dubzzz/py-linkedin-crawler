
class CrawlConditions:
    def __init__(self, conditions):
        """
        conditions is a dict()

        It contains keys that refer to their equivalent key in profile_details
        and compiled regex that will be run when calling is_crawlable
        """
        self.conditions = conditions

    def is_crawlable(self, profile_details):
        for key, value in self.conditions.items():
            try:
                profile_value = profile_details[key]
            except KeyError:
                print "\t\tERROR: No key '%s'" % key
                return False
            if not value.search(unicode(profile_value).lower()):
                return False
        return True
            
