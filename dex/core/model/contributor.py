

class Contributor(object):
    """
    Repository Contributor.
    """

    def __init__(self, name, email, count=0):
        self.name = name
        self.email = email
        self.count = count

    def get_name(self):
        return self.name

    def get_email(self):
        return self.email

    def set_count(self, count):
        self.count = count

    def get_count(self):
        return self.count

    def inc_count(self):
        self.count += 1

    def __str__(self):
        return "Contributor [{} <{}>]".format(self.name, self.email)