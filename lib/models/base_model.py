# Base model represents a database record. Provides commonly required 
# database procedures such as deleting, updating and selecting.
#
# All application models should be a subclass of this base_model class.
from lib.db import get_connection
from lib.models.exception import ModelException
from mysql.connector.errors import Error
from conf.logging.logger import logger


logger = logger.get_logger(__name__)


class BaseModel:

    def __init__(self, db_table, properties=dict(), id_col='id'):
        self.connection = None
        self.__id = None
        self.__id_col = id_col
        self.properties = []
        self.changed = False
        self.changes = []

        self.set(properties)
        self.db_table = db_table

    def __del__(self):
        # Close and commit any pending database operations
        if self.connection:
            self.connection.close()

    def __str__(self):
        data = dict()
        for p in self.properties:
            data[p] = self.get(p)
        return "Base Model - {}".format(data)

    #   Add all properties in the given dictionary on the model.
    #       dict(name='Jonathon', age = 23, gender = 'M')
    #   Two arguments eg, (key, value) may also be passed.
    #   Will store the name jonathon, under the property 'name'.
    def set(self, properties=dict(), value=None, no_change=False):
        # if value was given, properties is actual a single key.
        if value:
            self.__add_prop(properties, value, no_change)
        else:
            for (k, v) in properties.iteritems():
                self.__add_prop(k, v, no_change)
        return self

    def get(self, key):
        v = None
        try:
            v = getattr(self, self.__hide(key))
        except:
            pass
        return v

    # Saves the model to the database
    def save(self):
        if self.get(self.__id_col) and self.changed:
            return self.update()
        else:
            sql = "INSERT INTO {} {} VALUES {};".format(
                self.db_table, self.__sql_serialize_properties(), self.__sql_serialize_values())
            cursor = self.__execute(sql, close=False)
            self.__add_prop('id', cursor.lastrowid)
            cursor.close()

            self.__changes_made()

        return self

    # Updates a model in the database, if not exist, the model will be inserted.
    def update(self):
        if self.get(self.__id_col) and self.changed:
            # create sql
            # Serialize properties and keys to form eg,
            # 	name="jonathon",age=23
            pairs = []
            for p in self.changes:
                pairs.append('{}={}'.format(p, self.__sql_encapsulate_type(self.get(p))))
            sql = "UPDATE {} SET {} WHERE {} = {};".format(self.db_table, ', '.join(pairs), self.__id_col, self.get('id'))
            self.__execute(sql)

            self.__changes_made()
            return self
        else:
            # new record, therefore insert
            return self.save()

    # Queries the database with the given id and binds the result to this model.
    def fetch(self):
        if self.get(self.__id_col):
            sql = "SELECT * FROM {} WHERE {} = '{}' LIMIT 1;".format(self.db_table, self.__id_col, self.get(self.__id_col))
            cursor = self.__execute(sql, close=False)
            result = self.__map_column_values(cursor, cursor.fetchone())
            self.set(result, no_change=True)
            cursor.close()
            self.__changes_made()
        else:
            raise ModelException("Cannot perform `fetch` without a model id.")

        return self


    # Adds a property to the model
    def __add_prop(self, key, value, no_change=False):
        """
        Adds property to model. Updates the changes dict.
        If property is already present, check if the value has actually changed. If it has, append to changes otherwise
        if equal it is not an actual change.
        """
        if not no_change and ((key in self.properties and self.get(key) != value) or key not in self.properties):
            self.__commit_changes(key)
        # TODO: update basemodel to allow for sql functions
        setattr(self, self.__hide(key), value)
        self.__update_properties(key)

    def __commit_changes(self, key):
        """
        Adds the key to the changes list. This list is used when updating the database. Also sets the model state to
        'changed'.
        """
        if key not in self.changes:
            self.changes.append(key)
            self.changed = True

    def __changes_made(self):
        self.changed = False
        self.changes = []

    # Returns a key to be private
    def __hide(self, key):
        return '__' + key

    def __update_properties(self, key):
        if key not in self.properties and key != self.__id_col:
            self.properties.append(key)

    """ ----------------------------------------------------------------------------------------------------------------
        SQL HELPERS
    """

    # serialize properties into sql format, eg (name, age, gender)
    def __sql_serialize_properties(self):
        return '(' + ','.join(self.changes) + ')'

    def __sql_serialize_values(self):
        values = []
        for p in self.changes:
            values.append(self.__sql_encapsulate_type(self.get(p)))
        return '(' + ','.join(str(values)) + ')'

    # Depending on the value type, if string it will be encapsulated with \"\"
    def __sql_encapsulate_type(self, value):
        t = type(value)
        if t != int:
            return '"{}"'.format(value)
        else:
            return value

    # Returns a dictionary object of a row object returned from cursor results
    # method for example, `fetchone`
    def __map_column_values(self, cursor, row):
        field_names = [i[0] for i in cursor.description]
        return dict(zip(field_names, row))

    def __close_db_connection(self):
        self.connection.close()
        self.connection = None

    def __execute(self, sql, close=True):
        if not self.connection:
            self.connection = get_connection()
        cursor = self.connection.cursor()
        cursor.execute(sql)

        if close:
            cursor.close()
            self.__close_db_connection()

        return cursor if not close else True
