import sys
sys.path.insert(0, 'mongo-python-driver/test/high_availability')

import ha_tools

import tornado.ioloop
import tornado.web
import tornado.template as template

import uuid
import json

class RsHandler(tornado.web.RequestHandler):
    # Reply tpls extension
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

    def message(self, message):
        self.write(self._template.load('message' + self._ext).generate(message=message))

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

            try:
                # start RS and get its' params
                res = ha_tools.start_replica_set(members)
            except:
                raise tornado.httpserver._BadRequestException(
                    "Couldn't start RS!"
                )

            rs_uri, rs_name = res
            rs_id = uuid.uuid4()

            self.write(self._template.load(op + self._ext).generate(rs_id=rs_id, rs_uri=rs_uri, rs_name=rs_name))

        # Stop rs
        elif op == 'stop':
            try:
                ha_tools.kill_all_members()
            except:
                raise tornado.httpserver._BadRequestException(
                    "Couldn't stop RS!"
                )

        # Get primary
        elif op == 'get_primary':
            request = self._parse_json(self.request.body)
            rs_id = request['rs']['id']

            rs_primary_uri = ha_tools.get_primary()

            self.write(self._template.load(op + self._ext).generate(rs_id=rs_id, rs_primary_uri=rs_primary_uri))

        # Get secondaries
        elif op == 'get_secondaries':
            request = self._parse_json(self.request.body)
            rs_id = request['rs']['id']

            rs_secondaries_uris = ha_tools.get_secondaries()

            self.write(self._template.load(op + self._ext).generate(rs_id=rs_id, rs_secondaries_uris=rs_secondaries_uris))

        # Kill primary
        elif op == 'kill_primary':
            request = self._parse_json(self.request.body)
            rs_id = request['rs']['id']

            rs_killed_primary_uri = ha_tools.kill_primary()

            self.write(self._template.load(op + self._ext).generate(rs_id=rs_id, rs_killed_primary_uri=rs_killed_primary_uri))

        # Kill secondary
        elif op == 'kill_secondary':
            request = self._parse_json(self.request.body)
            rs_id = request['rs']['id']

            rs_killed_secondary_uri = ha_tools.kill_secondary()

            self.write(self._template.load(op + self._ext).generate(rs_id=rs_id, rs_killed_secondary_uri=rs_killed_secondary_uri))

        # Kill all secondaries
        elif op == 'kill_all_secondaries':
            request = self._parse_json(self.request.body)
            rs_id = request['rs']['id']

            rs_killed_secondaries_uris = ha_tools.kill_all_secondaries()

            self.write(self._template.load(op + self._ext).generate(rs_id=rs_id, rs_killed_secondaries_uris=rs_killed_secondaries_uris))

application = tornado.web.Application([
    (r"/rs/([_a-z]*)", RsHandler)
])

if __name__ == "__main__":
    application.listen(8888)
    tornado.ioloop.IOLoop.instance().start()
