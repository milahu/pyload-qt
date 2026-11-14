from PySide6.QtCore import (
    Qt,
    QTimer,
)
from PySide6.QtNetwork import (
    QNetworkReply,
)
NetworkError = QNetworkReply.NetworkError


class SessionMixin:

    # https://github.com/pyload/pyload/pull/4643
    # Basic auth in openapi spec
    # Session based authentication is a target for CSRF attacks,
    # so CSRF protection was added.
    # The plan is to implement API key generation and to use it for API access
    # but first I have to fix some bugs.
    # Basic Auth was a quick fix.

    # https://github.com/pyload/pyload/commit/adf33b94e8f4f366e0538c0f9cba95be842c071f
    # deprecate /api/login and /api/logout endpoints

    # pyload/src/pyload/webui/app/helpers.py
    # api_key = flask.request.headers.get("X-API-Key", None)
    # is_authenticated(s)
    # set_session(user_info)

    def login(self):
        def on_csrf_token(csrf_token):
            if csrf_token is None:
                print("error: login failed: got no csrf_token")
                QMessageBox.critical(self, "Login Failed", "Could not login to pyLoad: got no csrf_token")
                return
            self.client.login(
                self.on_login_result,
                username="pyload",
                password="pyload",
                # csrf_token=csrf_token,
            )
        self.client._get_csrf_token(on_csrf_token)

    def on_login_result(self, success):
        if success:
            self.get_config()
            self.refresh_queue()
        else:
            QMessageBox.critical(self, "Login Failed", "Could not login to pyLoad")

    def get_config(self):
        self.client.get_config(self.on_config)

    def on_config(self, config):
        if isinstance(config, NetworkError):
            print("on_config error", config)
            return
        self.config["core"] = config
        # print("on_config", json.dumps(config, indent=2))
        if 0:
            # debug
            p = "pyload_config.json"
            print(f"writing {p}")
            with open(p, "w") as fp:
                fp.write(json.dumps(config, indent=2) + "\n")

    def get_config_value(self, section, category, option):
        section_obj = self.config.get(section)
        if section_obj is None:
            # section was not found in config
            print(f"config: {self.config}")
            raise KeyError(section)
        category_obj = section_obj.get(category)
        if category_obj is None:
            # category was not found in section
            raise KeyError(f"{section}.{category}")
        for item in category_obj["items"]:
            if item["name"] == option:
                return item["value"]
        # option was not found in category
        raise KeyError(f"{section}.{category}.{option}")

    def init_refresh_timer(self):
        self.refresh_timer = timer = QTimer()
        timer.timeout.connect(self.refresh_timer_tick)
        timer.start(self.refresh_interval * 1000)

    def refresh_timer_tick(self):
        self.refresh_bottom_view()

    def refresh_bottom_view(self):
        pid = self.selected_package_pid
        bottom_view_idx = self.get_bottom_view_idx()
        if bottom_view_idx == self.BottomViewIdx.Package:
            self.update_package_package_view()
        elif bottom_view_idx == self.BottomViewIdx.Links:
            if pid:
                self.client.get_package_data(self.on_package_data_received, pid)
        elif bottom_view_idx == self.BottomViewIdx.Downloads:
            self.refresh_package_downloads_view()
        elif bottom_view_idx == self.BottomViewIdx.Files:
            if pid:
                # TODO refactor
                def on_package_data_received(res):
                    self.current_package = res
                    self.update_package_files_view()
                self.client.get_package_data(on_package_data_received, pid)
            else:
                # no package selected
                self.update_package_files_view()

        # TODO refresh status
        """
        http://localhost:8000/json/status
        {
            "pause": false,
            "active": 2,
            "queue": 14194,
            "total": 14859,
            "speed": 55321.0,
            "download": true,
            "reconnect": false,
            "captcha": false,
            "proxy": false
        }
        """
