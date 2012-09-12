Dependencies:

* [mongoDB](http://www.mongodb.org/)
* [Tornado](http://www.tornadoweb.org/)

    pip install tornado

* Latest [PyMongo](https://github.com/mongodb/mongo-python-driver)

    pip install pymongo

Ensure that no mongod or mongos are not running.

Run this code as:

    python main.py

This is a draft example of PyMongo HA tests:<br>
https://github.com/MblKiTA/mongo-python-driver/blob/rest_api/test/high_availability/test_ha_rest.py
