import sys, time, random

# Import pymongo
sys.path.insert(0, 'mongo-python-driver')
from pymongo import ReplicaSetConnection

# Import HA Tools
sys.path.insert(0, 'mongo-python-driver/test/high_availability')
import ha_tools

import tornado.ioloop
import tornado.web
import tornado.template as template

import uuid
import json


new_repl_id = -1

def get_new_repl_id():
    global new_repl_id
    new_repl_id += 1
    return new_repl_id

rs = []

class RsHandler(tornado.web.RequestHandler):
    # Reply's tpls extension
    _ext =  ".json"
    # Init template loader with 'tpl' dir
    _template = template.Loader('tpl')

    def _parse_json(self, data):
        try:
            json_data = json.loads(data)
        except ValueError:
            raise tornado.httpserver._BadRequestException(
                "Invalid JSON structure."
            )

        if type(json_data) != dict:
            raise tornado.httpserver._BadRequestException(
                "We only accept key value objects!"
            )

        return json_data

    def _get_index(self, seq, attribute, value):
        return next(index for (index, d) in enumerate(seq) if d[attribute] == value)

    def message(self, message):
        self.write(self._template.load('message' + self._ext).generate(message=message))

    def error(self, message):
        raise tornado.httpserver._BadRequestException(
            message
        )

    def get(self):
        """ Respond to a GET
        """
        self.write('GET')

    def post(self, op):
        """ Respond to a POST
        """
        # Start RS
        if op == 'start':
            request = self._parse_json(self.request.body)
            members = request['members']

            rs_id = uuid.uuid4()
            rs_name = 'repl' + str(get_new_repl_id())

            try:
                # start RS and get its' params
                res = ha_tools.start_replica_set(members, rs_name=rs_name)
            except:
                self.error("Couldn't start RS!")

            # Let's gather all the info about RS and save it
            rs_uri, rs_name, nodes, arbiters = res

            # Try to connect to new RS
            try:
                for _ in range(1 * 60 / 2):
                    time.sleep(2)

                    try:
                        c = ReplicaSetConnection(rs_uri, replicaSet=rs_name)
                    except:
                        pass
            except:
                self.error("Couldn't connect to the new RS: " + rs_uri + ", " + rs_name)

            secondaries_uris = []

            for secondary in c.secondaries:
                secondaries_uris.append('%s:%d' % (secondary))

            rs_t = {}

            rs_t['id'] = str(rs_id)
            rs_t['name'] = rs_name
            rs_t['primary'] = rs_uri
            rs_t['secondaries'] = secondaries_uris
            rs_t['nodes'] = nodes
            rs_t['arbiters'] = arbiters

            rs.append(rs_t)

            self.write(self._template.load(op + self._ext).generate(rs_id=rs_id, rs_uri=rs_uri, rs_name=rs_name))

        # FIXME: Some checks should be implemented

        # Stop rs
        elif op == 'stop':
            request = self._parse_json(self.request.body)
            rs_id = request['rs']['id']

            found_index = self._get_index(rs, 'id', rs_id)

            try:
                ha_tools.kill_members(rs[found_index]['nodes'].keys(), 2, rs[found_index]['nodes'])
                rs_t = rs.pop(found_index)
            except:
                self.error("Couldn't stop RS!")

            rs_id = rs_t['id']

            self.write(self._template.load(op + self._ext).generate(rs_id=rs_id))

        # Get primary
        elif op == 'get_primary':
            request = self._parse_json(self.request.body)
            rs_id = request['rs']['id']

            found_index = self._get_index(rs, 'id', rs_id)
            rs_primary_uri = rs[found_index]['primary']

            self.write(self._template.load(op + self._ext).generate(rs_id=rs_id, rs_primary_uri=rs_primary_uri))

        # Get secondaries
        elif op == 'get_secondaries':
            request = self._parse_json(self.request.body)
            rs_id = request['rs']['id']

            found_index = self._get_index(rs, 'id', rs_id)
            rs_secondaries_uris = rs[found_index]['secondaries']

            self.write(self._template.load(op + self._ext).generate(rs_id=rs_id, rs_secondaries_uris=rs_secondaries_uris))

        # Get the arbiters
        elif op == 'get_arbiters':
            request = self._parse_json(self.request.body)
            rs_id = request['rs']['id']

            found_index = self._get_index(rs, 'id', rs_id)
            rs_arbiters_uris = rs[found_index]['arbiters']

            self.write(self._template.load(op + self._ext).generate(rs_id=rs_id, rs_arbiters_uris=rs_arbiters_uris))

        # Kill the primary
        elif op == 'kill_primary':
            request = self._parse_json(self.request.body)
            rs_id = request['rs']['id']

            found_index = self._get_index(rs, 'id', rs_id)

            try:
                rs_primary_uri = rs[found_index]['primary']
                ha_tools.kill_members([rs_primary_uri], 2, rs[found_index]['nodes'])
                del rs[found_index]['primary']
            except:
                self.error("No primary found for this RS!")

            self.write(self._template.load(op + self._ext).generate(rs_id=rs_id, rs_killed_primary_uri=rs_primary_uri))

        # Kill the secondary
        elif op == 'kill_secondary':
            request = self._parse_json(self.request.body)
            rs_id = request['rs']['id']

            try:
                found_index = self._get_index(rs, 'id', rs_id)
            except:
                self.error("No secondaries found for this RS!")

            rs_secondaries_uris = rs[found_index]['secondaries']

            try:
                # Get a random secondary for this RS

                # Get a random index first
                rs_secondary_uri_index = random.randrange( len(rs_secondaries_uris) )
                # Pop out the element by this random index
                rs_secondary_uri = rs[found_index]['secondaries'].pop(rs_secondary_uri_index)

                ha_tools.kill_members([rs_secondary_uri], 2, rs[found_index]['nodes'])
                del rs[found_index]['nodes'][rs_secondary_uri]
            except:
                self.error("No secondaries found for this RS!")

            self.write(self._template.load(op + self._ext).generate(rs_id=rs_id, rs_killed_secondary_uri=rs_secondary_uri))

        # Kill all the secondaries
        elif op == 'kill_all_secondaries':
            request = self._parse_json(self.request.body)
            rs_id = request['rs']['id']

            found_index = self._get_index(rs, 'id', rs_id)

            try:
                rs_secondaries_uris = rs[found_index]['secondaries']
                ha_tools.kill_members(rs_secondaries_uris, 2, rs[found_index]['nodes'])
                del rs[found_index]['secondaries']
            except:
                self.error("No secondaries found for this RS!")

            self.write(self._template.load(op + self._ext).generate(rs_id=rs_id, rs_killed_secondaries_uris=rs_secondaries_uris))



application = tornado.web.Application([
    (r"/rs/([_a-z]*)", RsHandler)
])

if __name__ == "__main__":
    application.listen(8888)
    tornado.ioloop.IOLoop.instance().start()
