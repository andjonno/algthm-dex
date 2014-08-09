"""
Reads in a cloc output and generates some statistics from the report. This includes the prominent language in the
code base, how many lines (comment, code, blank),
"""

from yaml import load
from core.model.language import Language


BLACKLIST = ['header', 'SUM']


class Languages:

    def __init__(self, cloc_location, name=None):

        with open(cloc_location) as f:
            self.output = load(f)

        self.common = None
        self.languages = list()
        self.total_code = None
        self.total_lines = None
        self.total_blank = None
        self.total_comments = None
        self.total_files = None
        self.name = name

        self.__totals()
        self.__common_language()
        self.__statistics()

    def get_common_language(self):
        return self.common

    def get_languages(self):
        return self.languages

    def __common_language(self):
        name = None
        count = 0
        for lang in filter(lambda x: x not in BLACKLIST, self.output):
            if self.output[lang]['code'] > count:
                name = lang
                common = self.output[lang]
                count = self.output[lang]['code']

        self.common = Language(name, common['nFiles'], common['code'], common['comment'], common['blank'],
                               common['code'] / (self.total_code * 1.0))

    def __totals(self):
        self.totals = self.output['SUM']
        self.total_code = self.totals['code']
        self.total_comments = self.totals['comment']
        self.total_blank = self.totals['blank']
        self.total_lines = self.total_code + self.total_comments + self.total_blank
        self.total_files = self.totals['nFiles']

    def __statistics(self):
        files = None
        lines = None
        percent = None
        languages = filter(lambda x: x not in BLACKLIST, self.output)

        for language in languages:
            files = self.output[language]['nFiles']
            lines = self.output[language]['code']
            comments = self.output[language]['comment']
            blank = self.output[language]['blank']
            percent = lines / (self.total_code * 1.0)
            self.languages.append(Language(language, files, lines, comments, blank, percent))
        self.languages = sorted(self.languages, key=lambda lang: lang.percentage, reverse=True)
