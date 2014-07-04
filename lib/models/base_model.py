# Base model represents a database record. Provides commonly required 
# database procedures such as deleting, updating and selecting.
#
# All application models should be a subclass of this base_model class.
from conf.config_loader import ConfigLoader
from lib.db.commands import connect
from lib.models.exception import ModelException

class BaseModel:

    def __init__(self, db_table, properties=dict()):
        self.connection = None
        self.__id = None

        self.set(properties)
        self.db_table = db_table

    def __del__(self):
        # Close and commit any pending database operations
        if self.connection:
            self.connection.commit()
            self.connection.close()

    def __str__(self):
        data = dict()
        for p in self.properties:
            data[p] = self.get(p)
        return "Base Model - {}".format(data)

    """
    Add all properties in the given dictionary on the model.
    dict(
      name='Jonathon',
    	age = 23,
    	gender = 'M'
    )
    Two arguments eg, (key, value) may also be passed.
    Will store the name jonathon, under the property 'name'.
    """
    def set(self, properties=dict(), value=None):
        # if value was given,
        if value:
            self.__add_prop(properties, value)
        else:
            for (k, v) in properties.iteritems():
                self.__add_prop(k, v)
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
        if self.get('id'):
            return self.update()
        else:
            sql = "INSERT INTO {} {} VALUES {};".format(
                self.db_table, self.__sql_serialize_properties(), self.__sql_serialize_values())
            cursor = self.__execute(sql, close=False)
            self.__add_prop('id', cursor.lastrowid)
            cursor.close()


        return self

    # Updates a model in the database, if not exist, the model will be inserted.
    def update(self):
        if self.get('id'):
            # create sql
            # Serialize properties and keys to form eg,
            # 	name="jonathon",age=23
            pairs = []
            for p in self.properties:
                pairs.append('{}={}'.format(p, self.__sql_encapsulate_type(self.get(p))))
            sql = "UPDATE {} SET {} WHERE id = {};".format(self.db_table, ', '.join(pairs), self.get('id'))
            self.__execute(sql)

            return self
        else:
            # new record, therefore insert
            return self.save()

    # Queries the database with the given id and binds the result to this model.
    def fetch(self):
        if self.get('id'):
            sql = "SELECT * FROM {} WHERE id = {} LIMIT 1;".format(self.db_table, self.get('id'))
            cursor = self.__execute(sql, close=False)
            result = self.__map_column_values(cursor, cursor.fetchone())
            self.set(result)
            cursor.close()
        else:
            raise ModelException("Cannot perform `fetch` without a model id.")

        return self


    # Adds a property to the model
    def __add_prop(self, key, value):
        setattr(self, self.__hide(key), value)
        self.__update_properties(key)

    # Returns a key to be private
    def __hide(self, key):
        return '__' + key

    def __update_properties(self, key):
        if key not in self.properties:
            self.properties.append(key)

    """ ----------------------------------------------------------------------------------------------------------------
        SQL HELPERS
    """

    # serialize properties into sql format, eg (name, age, gender)
    def __sql_serialize_properties(self):
        return '(' + ','.join(self.properties) + ')'

    def __sql_serialize_values(self):
        values = []
        for p in self.properties:
            values.append(self.__sql_encapsulate_type(self.get(p)))
        print values
        return '(' + ','.join(str(values)) + ')'

    # Depending on the value type, if string it will be encapsulated with \"\"
    def __sql_encapsulate_type(self, value):
        if type(value) == str or type(value) == unicode:
            return '"{}"'.format(value)
        else:
            return value

    # Returns a dictionary object of a row object returned from cursor results
    # method for example, `fetchone`
    def __map_column_values(self, cursor, row):
        field_names = [i[0] for i in cursor.description]
        return dict(zip(field_names, row))

    def __execute(self, sql, close=True):
        if not self.connection:
            self.connection = connect()

        cursor = self.connection.cursor()
        cursor.execute(sql)
        self.connection.commit()
        if close:
            cursor.close()

        return cursor if not close else True
