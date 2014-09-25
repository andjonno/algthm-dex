"""
result.py
"""

from datetime import datetime


class Result:
    """
    Result is the final output from the indexing process. It encapsulates all found knowledge, indexable on the
    repository. This object can be serialized into a json object by which it is inserted into the database
    making it searchable.
    """

    # serial, is the datastructure holding the object which is sent to the index.
    __serial = dict(
        text=dict(
            readme=None,
            license=None,
            changelog=None,
        ),
        repository=dict(
            name=None,
            url=None,
            languages=dict(
                common=None,
                secondary=list()
            )
        ),
        processed=None
    )

    def __init__(self, name, url):
        self.__serial['repository']['name'] = name
        self.__serial['repository']['url'] = url
        self.__serial['processed'] = datetime.today()

    def set_statistics(self, statistics):
        """
        Takes a repository statistics object, serializable, appropriately binding it to the object.

        :param statistics: RepositoryStatistic
        :return: None
        """
        languages = statistics.get_languages()
        common = statistics.get_common_language()
        self.__serial['repository']['languages']['common'] = common.serialize()
        for language in languages:
            if language.name != common.name:
                self.__serial['repository']['languages']['secondary'].append(language.serialize())

    def set_fulltext(self, readme='', license='', changelog=''):
        """
        Sets full text attributes.

        :param readme: String
        :param license: String
        :param changelog: String
        :return: None
        """
        self.__serial['text']['readme'] = readme
        self.__serial['text']['license'] = license
        self.__serial['text']['changelog'] = changelog

    def serialize(self):
        return self.__serial
