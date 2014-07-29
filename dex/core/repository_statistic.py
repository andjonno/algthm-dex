"""
Statistics for a repository.
"""

class RepositoryStatistic:

    language = None
    files = None
    lines = None
    comments = None
    blank = None
    total = None
    percentage = None

    def __init__(self, language, files, lines, comments, blank, percentage):
        self.language = language
        self.files = files
        self.lines = lines
        self.comments = comments
        self.blank = blank
        self.total = self.lines + self.comments + self.blank
        self.percentage = percentage

    def __str__(self):
        return "{} : files {}, lines {}, codebase - {}%".format(self.language, self.lines, round(self.percentage, 2))
