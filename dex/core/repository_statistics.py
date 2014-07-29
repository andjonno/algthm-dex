"""
Reads in a cloc output and generates some statistics from the report. This includes the prominent language in the
code base, how many lines (comment, code, blank),
"""

from yaml import load
from core.repository_statistic import RepositoryStatistic


BLACKLIST = ['header', 'SUM']


class RepositoryStatistics:

    def __init__(self, cloc_location, name=None):

        with open(cloc_location) as f:
            self.output = load(f)

        self.common_language = None
        self.common_language_code = None
        self.common_language_percentage = None
        self.languages = list()
        self.__totals = None
        self.total_code = None
        self.total_lines = None
        self.total_blank = None
        self.total_comments = None
        self.total_files = None
        self.name = name if name else "repository"
        self.__totals = self.output['SUM']

        self.__do_totals()
        self.__common_lang()
        self.__do_lang_stats()

    def __common_lang(self):
        common = None
        count = 0
        for lang in filter(lambda x: x not in BLACKLIST, self.output):
            if self.output[lang]['code'] > count:
                common = lang
                count = self.output[lang]['code']

        self.common_language = common
        self.common_language_code = count
        self.common_language_percentage = round((self.common_language_code / (self.total_code * 1.0))*100, 2)

    def __do_totals(self):
        self.total_code = self.__totals['code']
        self.total_comments = self.__totals['comment']
        self.total_blank = self.__totals['blank']
        self.total_lines = self.total_code + self.total_comments + self.total_blank
        self.total_files = self.__totals['nFiles']

    def __do_lang_stats(self):
        files = None
        code = None
        perc = None
        languages = filter(lambda x: x not in BLACKLIST, self.output)

        for language in languages:
            files = self.output[language]['nFiles']
            code = self.output[language]['code']
            comments = self.output[language]['comment']
            blank = self.output[language]['blank']
            perc = code / (self.total_code * 1.0)
            self.languages.append(RepositoryStatistic(language, files, code, comments, blank, perc))
        self.languages = sorted(self.languages, key=lambda lang: lang.percentage, reverse=True)

    def __str__(self):
        output = "\n\n\033[1;07m{} codebase\033[0m \n".format(self.name)
        fmt = "{0:15} {1:>8} {2:>8} {3:>8} {4:>8} {5:>8}\n"
        bldfmt = "\033[1;34m{0:15}\033[0m \033[1;34m{1:>8}\033[0m \033[1;34m{2:>8}\033[0m \033[1;34m{3:>8}\033[0m " \
                 "\033[1;34m{4:>8}\033[0m \033[1;34m{5:>8}\033[0m\n"
        output += bldfmt.format("language", "code", "comments", "blank", "lines", "%")
        for l in self.languages:
            output += fmt.format(l.language, l.lines, l.comments, l.blank, l.total, round(l.percentage * 100, 2))

        output += "=" * 60 + "\n"

        output += fmt.format(
            "Total",
            self.total_code,
            self.total_comments,
            self.total_blank,
            self.total_lines,
            ""
        )
        output += "\n{}[{}]\n".format(self.name.capitalize(), self.common_language)
        return output