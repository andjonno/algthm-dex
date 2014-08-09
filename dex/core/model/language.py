"""
Statistics for a repository.
"""

class Language:

    name = None
    files = None
    lines = None
    comments = None
    blank = None
    total = None
    percentage = None

    def __init__(self, name, files, lines, comments, blank, percentage):
        self.name = name
        self.files = files
        self.lines = lines
        self.comments = comments
        self.blank = blank
        self.total = self.lines + self.comments + self.blank
        self.percentage = percentage

    def serialize(self):
        return dict(
            language=self.name,
            files=self.files,
            lines=self.lines,
            comments=self.comments,
            blank=self.blank,
            total=self.total,
            percentage=self.percentage,
        )

    def __str__(self):
        return "{} : files {}, lines {}, codebase - {}%".format(self.name, self.lines, round(self.percentage, 2))
