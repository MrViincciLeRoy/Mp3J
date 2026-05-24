import requests


class BaseMusicClient:
    def __init__(self, search_size_per_source=10, strict_limit_search_size_per_page=True, disable_print=False, **kwargs):
        self.search_size_per_source = search_size_per_source
        self.search_size_per_page = search_size_per_source
        self.strict_limit_search_size_per_page = strict_limit_search_size_per_page
        self.disable_print = disable_print
        self.session = None

    def _initsession(self):
        self.session = requests.Session()

    def get(self, url, **kwargs):
        return self.session.get(url, **kwargs)
