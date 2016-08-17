# -*- coding: utf-8 -*-

import re
from datetime import datetime
from flask import Flask, request, Response, jsonify

app = Flask(__name__)


class MockResponse(Response):

    def __init__(self, path, method, keyword=None, regular=None, **kwargs):
        super(MockResponse, self).__init__(**kwargs)

        self.path = path
        self.method = method.upper()
        self.keyword = keyword
        self.regular = regular

    @property
    def id(self):
        return self.path + " | " + self.method


class ResponsePicker(object):

    def __init__(self, response, mode=0):
        self.responses = [response]
        self.mode = mode

    @property
    def id(self):
        return self.responses[0].id

    def receive(self, response):
        if response.id != self.id:
            raise ValueError("only receive instance of MockResponse with same id")
        self.responses.append(response)

    def handle(self, request):
        app.logger.info(request.data)
        if self.mode == 0:
            return self.responses[0]
        elif self.mode == 1:  # keyword mode
            for response in self.responses:
                if response.keyword in request.data:
                    return response
            return
        elif self.mode == 2:  # regular mode
            for response in self.responses:
                p = re.search(response.regular, request.data)
                if p.group():
                    return response
            return
        else:
            return

    @classmethod
    def create_instance(cls, responses, mode=0):
        first_response = responses[0]
        inst = cls(first_response, mode)
        for response in responses[1:]:
            inst.receive(response)
        return inst


class ResponsePool(object):

    def __init__(self):
        self.pool = dict()

    def register(self, picker):
        if not isinstance(picker, ResponsePicker):
            raise ValueError
        self.pool[picker.id] = picker

    def get_by_id(self, rid, request):
        picker = self.pool.get(rid, None)
        if not picker:
            return
        return picker.handle(request)


pool = ResponsePool()
default_response = MockResponse("/", "GET", response="Welcome to mocker!")
default_picker = ResponsePicker(default_response)
pool.register(default_picker)


@app.route('/', defaults={'path': ''}, methods=['GET', 'POST', 'UPDATE', 'PATCH', 'OPTIONS'])
@app.route('/<path:path>', methods=['GET', 'POST', 'UPDATE', 'PATCH', 'OPTIONS'])
def main(path):
    rid = "/" + path + " | " + request.method.upper()
    app.logger.info(rid)
    response = pool.get_by_id(rid, request)
    if response is None:
        return default_response
    return response


@app.route("/create", methods=["POST"])
def create_mocked_response():
    """request body:
    {
      "path": "/echo",
      "method": "post",
      "mode": 1,
      "responses": [
        {
          "content": "{\"hello\": \"world\"}",
          "content_type": "application/json",
          "status_code": 200,
          "keyword": "world",
          "regular": null
        },
        {
          "content": "{\"foo\": \"bar\"}",
          "status_code": 200,
          "keyword": "foo",
          "regular": null,
          "headers": {
            "Auth": "1000000"
          }
        }
      ]
    }
    """
    app.logger.debug(request.data)
    rules = request.get_json()
    app.logger.info(rules)
    try:
        path, method, mode, responses = rules['path'], rules['method'], int(rules['mode']), rules['responses']
    except KeyError:
        return jsonify(msg="required field missing")
    except TypeError:
        return jsonify(msg="invalid request")
    else:
        if not responses:
            return jsonify(msg="empty response")

        if generate_response_from_request(path, method, mode, responses):
            return jsonify(msg="ok")
        else:
            return jsonify(msg="unknown error")


@app.route("/import", methods=['POST'])
def import_settings():
    settings = request.get_json()
    if not settings.get("data", None):
        return jsonify(msg="import failed")

    for rule in settings['data']:
        try:
            path, method, mode, responses = rule['path'], rule['method'], rule['mode'], rule['responses']
        except KeyError:
            return jsonify(msg="required field missing")
        except TypeError:
            return jsonify(msg="invalid request")
        else:
            generate_response_from_request(path, method, mode, responses)
    return jsonify(msg="ok")


@app.route("/export", methods=["GET"])
def export_settings():
    settings = {"date": datetime.now(), "data": []}

    for _, picker in pool.pool.iteritems():
        mode = picker.mode
        path = None
        method = None
        item = {"mode": mode, "path": path, "method": method, "responses": []}
        for response in picker.responses:
            if not item['path']:
                item['path'] = response.path
            if not item['method']:
                item['method'] = response.method
            resp = dict(
                keyword=response.keyword,
                regular=response.regular,
                content=response.response,
                status_code=response.status_code,
                content_type=response.content_type,
                headers={k: v for k, v in response.headers.items()})
            item['responses'].append(resp)
        settings['data'].append(item)
    return jsonify(settings)


def generate_response_from_request(path, method, mode, responses):
    mocked_responses = []
    for response in responses:
        headers = response.pop("headers", None)
        content = response.pop("content", "hello world")
        status_code = response.pop("status_code", 200)
        mocked_response = MockResponse(path, method, response=content, status=status_code, **response)
        if headers and isinstance(headers, dict):
            for k, v in headers.iteritems():
                mocked_response.headers[k] = v
        mocked_responses.append(mocked_response)

    picker = ResponsePicker.create_instance(mocked_responses, mode)
    pool.register(picker)
    return True


if __name__ == "__main__":
    import argparse

    args = argparse.ArgumentParser()
    args.add_argument("--host", dest="host", default="0.0.0.0", type=str, action="store")
    args.add_argument("--port", dest="port", default=8888, type=int, action="store")

    opts = args.parse_known_args()

    try:
        from gevent.wsgi import WSGIServer
    except ImportError:
        app.run(opts.host, port=opts.port)
    else:
        http_server = WSGIServer("{}:{}".format(opts.host, opts.port), app)
        http_server.serve_forever()
