from __future__ import print_function
from flask import Flask, request
from flask_restful import reqparse, abort, Api, Resource

import argparse
import json
import os
import random


CHARS = "BCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz123456789"  # 60 unique characters.
UNIQUE_LEN = 6  # 46B unique

app = Flask(__name__)
api = Api(app)
db = None
request_parser = reqparse.RequestParser()

verbose = 0
strict_put = False
authorization_token = ""


def create_unique():
    """
    :return: string very likely to be unique.
    """
    result = ""
    for i in range(UNIQUE_LEN):
        result += random.choice(CHARS)
    return result


def strip_tag(field, tag):
    """
    If 'field' is in the form 'str_tag1_tag2' and tag matches any tag remove it.
    :param field: arbitrary string
    :return: str, bool (indicating if 'tag' was removed)
    """
    s = field.split("_")
    found = False
    if tag in s:
        s.remove(tag)
        found = True
    return "_".join(s), found


def strip_from_end(s, c):
    """
    Remove all 'c' from the end of 's'
    :param s: a string.
    :param c: character or substring to remove
    :return: remainder of 's'
    """
    if c:
        while s.endswith(c):
            s = s[:-len(c)]
    return s


def strip_from_start(s, c):
    """
    Remove all 'c' from the start of 's'
    :param s: a string.
    :param c: character or substring to remove
    :return: remainder of 's'
    """
    if c:
        while s.startswith(c):
            s = s[len(c):]
    return s


def validate_authorization():
    if authorization_token:
        auth = request.headers.get("Authorization", "").split(" ")
        if len(auth) == 2 and auth[0].lower() == "bearer" and auth[1] == authorization_token:
            return  # Success!
        print("Authentication failed: '{}'".format(" ".join(auth)))
        abort(401)


class DataBase(object):
    def __init__(self, file_name=""):
        self._data = {}
        self._file_name = file_name

        self.load_from_disk()

    def load_from_disk(self):
        if self._file_name and os.path.exists(self._file_name):
            with open(self._file_name, "r") as f:
                self._data = json.load(f)
            if verbose:
                print("Loaded data from file", self._file_name, "- records found:", len(self._data))

    def persist_to_disk(self):
        if self._file_name:
            with open(self._file_name, "w") as f:
                json.dump(self._data, f, sort_keys=True, indent=4, separators=(",", ": "))
            if verbose:
                print("Persisted data to file", self._file_name, "- records to store:", len(self._data))

    def throw_if_does_not_exist(self, unique_id):
        if not self.exists(unique_id):
            abort(404, message="Item with id '{}' does not exist.".format(unique_id))

    def all(self):
        return self._data

    def exists(self, unique_id):
        return unique_id in self._data

    def get(self, unique_id):
        self.throw_if_does_not_exist(unique_id)
        return self._data[unique_id]

    def get_field(self, unique_id, field):
        record = self.get(unique_id)
        if field not in record:
            abort(404, message="field '{}' not found!".format(field))
        return record[field]

    def delete(self, unique_id):
        validate_authorization()
        self.throw_if_does_not_exist(unique_id)
        del db.data[unique_id]
        self.persist_to_disk()

    def put(self, unique_id, record, only_update=True):
        validate_authorization()
        if only_update:
            self.throw_if_does_not_exist(unique_id)
        self._data[unique_id] = record
        self.persist_to_disk()

    def post(self, record):
        validate_authorization()
        while True:
            unique_id = create_unique()
            if not self.exists(unique_id):
                self._data[unique_id] = record
                self.persist_to_disk()
                return unique_id


class ItemList(Resource):
    def get(self):
        return db.all()

    def post(self):
        validate_authorization()
        args = request_parser.parse_args()
        unique_id = db.post(args)
        return unique_id, 201


class Item(Resource):
    def get(self, unique_id):
        return db.get(unique_id)

    def delete(self, unique_id):
        db.delete(unique_id)
        return '', 204

    def put(self, unique_id):
        args = request_parser.parse_args()
        db.put(unique_id, args, strict_put)
        return args, 201


class ItemField(Resource):
    def get(self, unique_id, field):
        return db.get_field(unique_id, field)


def main():
    global verbose, strict_put, authorization_token, db
    parser = argparse.ArgumentParser("Simple rest api server")

    parser.add_argument("-v", "--verbose", action="count", default=0,
                        help="Increase output verbosity")
    parser.add_argument("-d", "--debug", action="store_true", default=False,
                        help="Run in debug mode")
    parser.add_argument("-a", "--api", default="/api",
                        help="API root.  Default '%(default)s'")
    parser.add_argument("-f", "--file-name", default="",
                        help="Filename for persistent storage")
    parser.add_argument("-t", "--token", default="",
                        help="Authorization token required for updates")
    parser.add_argument("-s", "--strict-put", action="store_true", default=False,
                        help="Only allow PUT on existing resource")
    parser.add_argument("field", nargs="*", default=["text", "count_optional_int", "help_optional"],
                        help="Fields in API. If empty: 'text count_optional_int help_optional'")

    args = parser.parse_args()

    verbose = args.verbose
    strict_put = args.strict_put
    authorization_token = args.token

    db = DataBase(file_name=args.file_name)

    api_normalized = strip_from_end(strip_from_start(args.api, "/"), "/")
    api.add_resource(ItemList, "/" + api_normalized)
    if len(api_normalized) > 0:
        api_normalized = "/" + api_normalized
    api.add_resource(Item, api_normalized + "/<unique_id>")
    api.add_resource(ItemField, api_normalized + "/<unique_id>/<field>")

    print("Starting API server on", args.api)

    for field in args.field:
        argvars = {}
        field, optional = strip_tag(field, "optional")
        field, required = strip_tag(field, "required")
        field, type_int = strip_tag(field, "int")
        field, type_str = strip_tag(field, "str")
        if type_int:
            argvars["type"] = int
        if not optional:
            argvars["required"] = True
        else:
            if type_int:
                argvars["default"] = 0
            else:
                argvars["default"] = ""

        print("Adding field:", field, ("required" if not optional else "optional"), ("int" if type_int else "str"))
        request_parser.add_argument(field, **argvars)

    app.run(debug=args.debug, host="0.0.0.0", port=5000)

    return 0


if __name__ == '__main__':
    exit(main())
