from datetime import datetime


class Sector:
    """
    A sector represents a duration in time. When sampling a repository, samples
    are extracted from the repository in fixed increments of time. A sample
    is dependent on a set resolution, currently this resolution is 1 week, or
    604,800 seconds to be exact.

    A sector provides a definite time duration rather than relying on a loose
    model of a timestamp and the current resolution.

    Objects can be associated with a sector, e.g. Commit objects are time bound
    and therefore are tied to a sector.
    """
    def __init__(self, start, end):
        if not start or not end:
            raise ValueError('Sector requires a start and end time.')

        self.__objects = []
        self.__start = start
        self.__end = end

    def duration(self):
        return self.__start - self.__end

    def includes(self, query):
        """
        Given query timestamp, returns true iff lies within the sector.
        :param query:
        :return: boolean
        """
        return self.__start >= query > self.__end

    def add_object(self, _object, time):
        """
        Adds the given object to the sector. The object is associated with a time.
        To simplify, a time is passed in to get the objects timestamp.
        :param _object:
        :param time:
        :return: None
        """
        if self.includes(time):
            self.__objects.append(_object)
            return True
        return False

    def get_objects(self):
        return self.__objects

    def __str__(self):
        return "Sector [{} -> {}]".format(datetime.fromtimestamp(self.__start), datetime.fromtimestamp(self.__end))

    def __dict__(self):
        return [o.__dict__() for o in self.__objects]