import os
import re
import json

import urllib.parse

from PySide6.QtCore import (
    # Qt,
    QUrl,
)
from PySide6.QtNetwork import (
    QNetworkAccessManager,
    QNetworkRequest,
    QNetworkReply,
)

class PyLoadClient:
    def __init__(self):
        self.manager = QNetworkAccessManager()
        # FIXME by default, the pyload server runs with ipv6
        # but with webui.develop=True in ~/.pyload/settings/pyload.cfg it runs with ipv4
        self.base_url = "http://localhost:8000" # ipv4: login fails with NetworkError.ConnectionRefusedError
        self.base_url = "http://127.0.0.1:8000" # ipv4: login fails with NetworkError.ConnectionRefusedError
        self.base_url = "http://[::1]:8000" # ipv6
        self.is_localhost = True
        self.session_cookie = None
        self.csrf_token = None
        self.func_cache = {}

    # https://stackoverflow.com/questions/13194180/dynamic-method-generation-in-python
    def __getattr__(self, name):
        # print(f"getattr {name}")
        try:
            return self.func_cache[name]
        except KeyError:
            pass
        # print(f"creating function {name}")
        # def func(self, *args, **kwargs, callback): # ?
        # def func(self, *args, callback=None, **kwargs): # ?
        # def func(*args, callback=None, **kwargs): # ?
        # def func(self, callback, *args, **kwargs):
        def func(callback, *args, **kwargs):
            # print(f"PyLoadClient.{name}: callback={callback} args={args} kwargs={kwargs}")
            if not callable(callback):
                raise ValueError("callback must be a function")
            if name in ("status", "links"):
                api_dir = "json"
            elif name in ("login", "logout"):
                # https://github.com/pyload/pyload/commit/adf33b94e8f4f366e0538c0f9cba95be842c071f
                # deprecate /api/login and /api/logout endpoints
                api_dir = ""
            else:
                api_dir = "api"
            post_methods = (
                "login",
                "push_to_queue",
                "pull_from_queue",
                "restart_failed",
                "delete_packages",
                "add_package",
                "set_config_value",
                "set_config_values",
                "set_package_data",
                "unpause_server",
                "pause_server",
                "stop_all_downloads",
                "order_packages",
            )
            if name in post_methods or name.startswith("set_") or name.startswith("add_"):
                # method = "post"
                is_get = False
            else:
                # method = "get"
                is_get = True
            # print(f"func: name={name} is_get={is_get}")
            url = f"{self.base_url}/{os.path.join(api_dir, name)}"
            is_get_csrf_token = False
            is_login = False
            if name == "_get_csrf_token":
                is_get_csrf_token = True
                is_get = True
                url = f"{self.base_url}/login"
            elif name == "login":
                is_login = True
            if args:
                url += "/" + ",".join(map(str, args))
            # send csrf_token with all requests
            if self.csrf_token and not "csrf_token" in kwargs:
                kwargs["csrf_token"] = self.csrf_token
            if kwargs and is_get:
                kwargs_json = dict()
                for key, val in kwargs.items():
                    kwargs_json[key] = json.dumps(val, separators=(",", ":"))
                url += "?" + urllib.parse.urlencode(kwargs_json)
            elif kwargs and not is_get:
                post_data = urllib.parse.urlencode(kwargs).encode()
            # print(f"client.{name}: url = {url!r}")
            request = QNetworkRequest(QUrl(url))
            if self.session_cookie:
                request.setRawHeader(b"Cookie", self.session_cookie.encode())
            if is_get:
                reply = self.manager.get(request)
            else:
                request.setHeader(
                    QNetworkRequest.ContentTypeHeader, "application/x-www-form-urlencoded"
                )
                if 0:
                    # debug
                    print(f"PyLoadClient.{name}: url={url} post_data={post_data}")
                reply = self.manager.post(request, post_data)
            def handle_reply():
                if reply.error() == QNetworkReply.NoError:
                    data_str = reply.readAll().data().decode()
                    data = None
                    if is_get_csrf_token:
                        # if data_str.startswith("<!DOCTYPE html>"):
                        regex = r'<meta name="csrf-token" content="([^"]+)"'
                        match = re.search(regex, data_str)
                        if match:
                            data = match.group(1)
                            self.csrf_token = data
                    elif is_login:
                        # data = not ("<title>Login - pyLoad" in data_str)
                        data = ("<title>pyLoad - Dashboard</title>" in data_str)
                    else:
                        data = json.loads(data_str)
                    if callback: callback(data)
                else:
                    # TODO also print response body with the server exception
                    error_message = reply.readAll().data().decode()
                    if error_message:
                        error_message = f": {error_message}"
                    print(f"{name} reply.error: {reply.error()}{error_message}")
                    # consumers should check the result with
                    # isinstance(result, QNetworkReply.NetworkError)
                    if callback: callback(reply.error())
                reply.deleteLater()
            reply.finished.connect(handle_reply)
        func.__name__ = name
        self.func_cache[name] = func
        return func
