import json

from PySide6.QtWidgets import (
    QDialog,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QTreeWidget,
    QTreeWidgetItem,
    QTableWidget,
    QTableWidgetItem,
    QPushButton,
    QLabel,
    QLineEdit,
    QCheckBox,
    QComboBox,
    QFileDialog,
    QMessageBox,
    QHeaderView,
    QAbstractItemView,
    QToolButton,
)
from PySide6.QtGui import (
    QIntValidator,
)
from PySide6.QtCore import (
    Qt,
    QSize,
    QTimer,
)

class AppSettingsDialog(QDialog):
    """
    Settings dialog for pyLoad UI.

    - parent_pyload_ui: instance of PyLoadUI (main window)
    - uses parent_pyload_ui.client for get_config / get_plugin_config / set_config_value
    """
    def __init__(self, parent_pyload_ui):
        super().__init__(parent=parent_pyload_ui)
        self.pyload_ui = parent_pyload_ui
        self.client = self.pyload_ui.client
        self.setWindowTitle("App Settings")
        self.resize(800, 600)
        self.pending_changes = {}  # keys: (section, category, option) -> new_value (string)
        self._current_section = None  # 'core' or 'plugin'
        self._current_category = None  # e.g. 'general' or 'AlfadfileNet'
        self.config = {
            "core": {}, # aka "general"
            "plugins": {},
            "accounts": {},
            "users": {},
        }
        self._init_ui()
        self.client.get_config(self.on_core_config)

    def on_core_config(self, config: dict):
        # FIXME handle errors
        section = "core"
        # print(f"{section} config:", json.dumps(config, indent=2))
        self.config[section] = config or {}
        self._populate_tree()
        self._tree_select_section(section)

    def on_plugins_config(self, config: dict):
        # FIXME handle errors
        section = "plugins"
        # print(f"{section} config:", json.dumps(config, indent=2))
        self.config[section] = config or {}
        self._populate_tree(section)

    def on_accounts_config(self, config: dict):
        # FIXME handle errors
        # TODO allow adding new accounts
        section = "accounts"
        # print(f"{section} config:", json.dumps(config, indent=2))
        assert type(config) == list
        for account in config:
            category = account["type"] + " " + account["login"]
            category_dict = {
                "name": category,
                # "description": "some description",
                "items": [
                    {
                        "name": "type",
                        "description": "type",
                        "value": account["type"],
                        "type": "str",
                        "readonly": True,
                    },
                    {
                        "name": "login",
                        "description": "Username",
                        "value": account["login"],
                        "type": "str",
                    },
                    {
                        "name": "password",
                        "description": "Password",
                        "value": "***", # TODO allow changes
                        "type": "password",
                    },
                    {
                        "name": "validuntil",
                        "description": "validuntil",
                        "value": account["validuntil"],
                        "type": "str", # TODO datetime or None
                        "readonly": True,
                    },
                    {
                        "name": "options",
                        "description": "options",
                        "value": json.dumps(account["options"]),
                        "type": "str",
                    },
                    {
                        "name": "valid",
                        "description": "valid",
                        "value": account["valid"],
                        "type": "bool",
                        "readonly": True,
                    },
                    {
                        "name": "trafficleft",
                        "description": "trafficleft",
                        "value": account["trafficleft"],
                        "type": "int",
                        "readonly": True,
                    },
                    {
                        "name": "premium",
                        "description": "premium",
                        "value": account["premium"],
                        "type": "bool",
                        "readonly": True,
                    },
                    {
                        "name": "delete",
                        "description": "delete",
                        "value": False,
                        "type": "bool",
                        "readonly": True, # TODO allow changes
                    },
                ],
            }
            self.config[section][category] = category_dict
        self._populate_tree(section)

    def on_users_config(self, config: dict):
        # FIXME handle errors
        # TODO allow adding new users
        section = "users"
        # print(f"{section} config:", json.dumps(config, indent=2))
        self.config[section] = {}
        for user in config.values():
            category = user["name"]
            category_dict = {
                "name": category,
                # "description": "some description",
                "items": [
                    {
                        "name": "id",
                        "description": "id",
                        "value": user["id"],
                        "type": "int",
                        "readonly": True,
                    },
                    {
                        "name": "name",
                        "description": "name",
                        "value": user["name"],
                        "type": "str",
                        "readonly": True,
                    },
                    {
                        "name": "password",
                        "description": "password",
                        "value": "***", # TODO allow changes
                        "type": "password",
                    },
                    {
                        "name": "email",
                        "description": "email",
                        "value": user["email"],
                        "type": "str",
                    },
                    {
                        "name": "role",
                        "description": "role",
                        "value": user["role"],
                        "type": "int", # TODO role=0 means admin?
                        "readonly": True, # TODO allow changes
                    },
                    {
                        # FIXME add one config item per permission bit
                        "name": "permission",
                        "description": "permission",
                        "value": user["permission"],
                        "type": "int",
                        "readonly": True, # TODO allow changes
                    },
                    {
                        "name": "template", # TODO what?
                        "description": "template",
                        "value": user["template"],
                        "type": "str",
                        "readonly": True, # TODO allow changes?
                    },
                    {
                        "name": "delete",
                        "description": "delete",
                        "value": False,
                        "type": "bool",
                        "readonly": True, # TODO allow changes
                    },
                ],
            }
            self.config[section][category] = category_dict
        self._populate_tree(section)

    def _init_ui(self):
        main_layout = QHBoxLayout(self)

        # Left: Tree + optional filter
        left_widget = QWidget()
        left_layout = QVBoxLayout(left_widget)
        # Filter (placeholder; search implementation can be added later)
        filter_layout = QHBoxLayout()
        filter_label = QLabel("Filter:")
        self.filter_input = QLineEdit()
        self.filter_input.setPlaceholderText("Search keys (not implemented yet)...")
        filter_layout.addWidget(filter_label)
        filter_layout.addWidget(self.filter_input)
        left_layout.addLayout(filter_layout)

        self.tree = QTreeWidget()
        self.tree.setHeaderHidden(True)
        self.tree.setIndentation(12)
        left_layout.addWidget(self.tree)

        self.tree.itemClicked.connect(self.on_tree_item_clicked)
        self.tree.itemExpanded.connect(self.on_tree_item_expanded)

        main_layout.addWidget(left_widget, 1)

        # Right: table with description + value widget
        right_widget = QWidget()
        right_layout = QVBoxLayout(right_widget)

        self.table = QTableWidget(0, 2)
        self.table.setHorizontalHeaderLabels(["Description", "Value"])
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        right_layout.addWidget(self.table)

        # Bottom buttons
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()

        self.ok_btn = QPushButton("OK")
        self.apply_btn = QPushButton("Apply")
        self.cancel_btn = QPushButton("Cancel")
        btn_layout.addWidget(self.ok_btn)
        btn_layout.addWidget(self.apply_btn)
        btn_layout.addWidget(self.cancel_btn)

        self.ok_btn.clicked.connect(self.on_ok)
        self.apply_btn.clicked.connect(self.on_apply)
        self.cancel_btn.clicked.connect(self.reject)

        right_layout.addLayout(btn_layout)

        main_layout.addWidget(right_widget, 2)

    def _populate_tree(self, section=None):
        populate_section = section
        if populate_section is None:
            # populate all sections
            self.tree.clear()
        for section_idx, section in enumerate(self.config.keys()):
            if populate_section:
                # section already exists in tree
                section_root = self.tree.topLevelItem(section_idx)
                # section_root.clear()
                while section_root.childCount() > 0:
                    child = section_root.child(0)
                    section_root.removeChild(child)
                    del child
            else:
                # add section to tree
                section_root = QTreeWidgetItem(self.tree, [section])
                section_root.setData(0, Qt.UserRole, (section, None))
            for category in self.config[section].keys():
                category_dict = self.config[section][category]
                # print(f"section={section} category={category} category_dict={category_dict}")
                node = QTreeWidgetItem(section_root, [category_dict.get("name", category)])
                node.setData(0, Qt.UserRole, (section, category))
                # FIXME recurse
            if len(self.config[section]) == 0:
                dummy_node = QTreeWidgetItem(section_root, ["(loading...)"])
                category = True
                dummy_node.setData(0, Qt.UserRole, (section, category))
                section_root.setExpanded(False)  # collapse

    def _tree_select_section(self, section):
        section_idx = list(self.config.keys()).index(section)
        # auto-select first category if available
        section_root = self.tree.topLevelItem(section_idx)
        if section_root and section_root.childCount() > 0:
            sel_item = section_root.child(0)
            self.tree.setCurrentItem(sel_item)
            self.on_tree_item_clicked(sel_item, 0)

    def on_tree_item_clicked(self, item, column):
        section, category = item.data(0, Qt.UserRole)
        if category is None:
            # section root node clicked → clear table
            self.table.setRowCount(0)
            self._current_section = None
            self._current_category = None
            return

        self._current_section = section
        self._current_category = category
        items = self.config[section][category].get("items", [])
        self._populate_table(items)

    def on_tree_item_expanded(self, item):
        section, category = item.data(0, Qt.UserRole)
        assert category is None # only top-level items should be expandable
        # print(f"on_tree_item_expanded item={item} section={section} category={category}")
        if len(self.config[section]) > 0:
            # section has been loaded already
            return
        # load section
        # print(f"loading section {section}")
        if section == "plugins":
            return self.client.get_plugin_config(self.on_plugins_config)
        if section == "accounts":
            return self.client.get_accounts(self.on_accounts_config)
        if section == "users":
            return self.client.get_all_userdata(self.on_users_config)

    def _populate_table(self, items):
        """Populate the right-hand table with description + widget per item."""
        self.table.clearContents()
        self.table.setRowCount(0)
        for idx, it in enumerate(items):
            name = it.get("name")
            desc = it.get("description", name)
            value = it.get("value", "")
            type_str = it.get("type", "str")
            readonly = it.get("readonly", False)

            self.table.insertRow(idx)
            desc_item = QTableWidgetItem(desc)
            desc_item.setFlags(desc_item.flags() ^ Qt.ItemIsEditable)
            # attach metadata to description item so we can find option name later
            desc_item.setData(Qt.UserRole, {"option": name, "type": type_str})
            self.table.setItem(idx, 0, desc_item)

            on_value_changed = None
            if not readonly:
                on_value_changed = self._make_on_value_changed(self._current_section, self._current_category, name)

            widget = self._create_value_widget(type_str, value, on_value_changed)
            self.table.setCellWidget(idx, 1, widget)

        # Resize value column to reasonable width
        self.table.horizontalHeader().resizeSections(QHeaderView.ResizeMode.Stretch)

    def _create_value_widget(self, type_str, value, on_change_callable):
        """
        Create widget appropriate for the type and set initial value.
        on_change_callable(new_value) will be called when the user changes it.
        """
        lower = type_str.lower() if isinstance(type_str, str) else "str"
        # enums are indicated with semicolons: e.g. "debug;trace;stack" or "en;"
        if ";" in type_str:
            choices = [c for c in type_str.split(";") if c != ""]
            combo = QComboBox()
            combo.addItems(choices)
            # try to set current index to the matching value
            try:
                idx = choices.index(value)
                combo.setCurrentIndex(idx)
            except ValueError:
                # fallback: if value not in choices, add it then select
                if value and value not in choices:
                    combo.addItem(str(value))
                    combo.setCurrentIndex(combo.count() - 1)
            if on_change_callable:
                combo.currentTextChanged.connect(lambda v: on_change_callable(str(v)))
            else:
                combo.setReadOnly(True)
            return combo

        if lower == "bool":
            cb = QCheckBox()
            cb.setChecked(str(value).lower() in ("1", "true", "yes", "on", "t"))
            if on_change_callable:
                cb.stateChanged.connect(lambda s: on_change_callable("True" if s == Qt.Checked else "False"))
            else:
                # cb.setReadOnly(True)
                # cb.setEnabled(False) # gray
                cb.setAttribute(Qt.WA_TransparentForMouseEvents, True)
                cb.setFocusPolicy(Qt.NoFocus)
            return cb

        if lower == "int":
            le = QLineEdit()
            le.setText(str(value))
            le.setValidator(QIntValidator())
            # on editingFinished, validate and call
            if on_change_callable:
                le.editingFinished.connect(lambda le=le: on_change_callable(le.text()))
            else:
                le.setReadOnly(True)
            return le

        if lower == "folder":
            # composite widget: QLineEdit + browse button
            container = QWidget()
            h = QHBoxLayout(container)
            h.setContentsMargins(0, 0, 0, 0)
            le = QLineEdit()
            le.setText(str(value))
            btn = QToolButton()
            btn.setText("…")
            btn.setFixedWidth(28)
            if on_change_callable:
                def browse():
                    selected = QFileDialog.getExistingDirectory(self, "Select folder", le.text() or "/")
                    if selected:
                        le.setText(selected)
                        on_change_callable(selected)
                btn.clicked.connect(browse)
                le.editingFinished.connect(lambda le=le: on_change_callable(le.text()))
            else:
                le.setReadOnly(True)
            h.addWidget(le)
            h.addWidget(btn)
            return container

        # default: string
        le = QLineEdit()
        le.setText(str(value))
        if on_change_callable:
            le.editingFinished.connect(lambda le=le: on_change_callable(le.text()))
        else:
            le.setReadOnly(True)
        return le

    def _make_on_value_changed(self, section, category, option):
        """
        Return a function that stores the pending change.
        section: 'core' | 'plugin'
        category: e.g. 'general' or plugin name
        option: option name inside the category
        """
        def on_change(new_value):
            # Normalize to string (client seems to use strings in your examples)
            s = str(new_value)
            key = (section, category, option)
            self.pending_changes[key] = s
            # Visual hint: mark row with an asterisk in description
            for row in range(self.table.rowCount()):
                desc_item = self.table.item(row, 0)
                if desc_item:
                    meta = desc_item.data(Qt.UserRole)
                    if meta and meta.get("option") == option:
                        base_text = desc_item.text()
                        if not base_text.endswith(" *"):
                            desc_item.setText(base_text + " *")
                        return
        return on_change

    def _validate_changes(self):
        """Validate pending changes before sending. Returns (ok, errmsg)."""
        # We will validate basic types: int must be int; others are strings/booleans.
        for (section, category, option), value in list(self.pending_changes.items()):
            # fetch type info from loaded configs
            type_str = None
            # TODO handle section == "accounts"
            if section not in ("core", "plugins"): continue
            cfg = self.config.get(section, {}).get(category, {})
            for it in cfg.get("items", []):
                if it.get("name") == option:
                    type_str = it.get("type", "str")
                    break
            if type_str is None:
                return False, f"Unknown option {option} in {category}"
            if ";" in type_str:
                # enum: check value is one of allowed
                choices = [c for c in type_str.split(";") if c != ""]
                if value not in choices:
                    return False, f"Invalid value for {option}: {value}. Allowed: {choices}"
            elif type_str.lower() == "int":
                try:
                    int(value)
                except Exception:
                    return False, f"Invalid integer for {option}: {value}"
            elif type_str.lower() == "bool":
                if value not in ("True", "False", "1", "0", "true", "false"):
                    return False, f"Invalid boolean for {option}: {value}"
            # folder/str no strict validation here
        return True, ""

    def on_apply(self):
        """Apply pending changes by calling client.set_config_value for each changed option."""
        if not self.pending_changes:
            QMessageBox.information(self, "No changes", "There are no changes to apply.")
            return
        ok, errmsg = self._validate_changes()
        if not ok:
            QMessageBox.warning(self, "Validation failed", errmsg)
            return

        errors = []
        # apply all pending changes
        # We attempt all and collect failures rather than stopping at first
        for (section, category, option), value in list(self.pending_changes.items()):
            section_name = "core" if section == "core" else "plugin"
            try:
                # call client.set_config_value(category, option, value, section)
                # note: in your spec, section can be "core" or "plugin"
                self.client.set_config_value(category, option, value, section_name)
                # remove pending change on success
                del self.pending_changes[(section, category, option)]
                # Also update our in-memory copy so UI reflects current values
                cfg = self.config.get(section, {})
                if category in cfg:
                    for it in cfg[category]["items"]:
                        if it.get("name") == option:
                            it["value"] = value
                            break
            except Exception as e:
                errors.append(f"{category}/{option}: {e}")

        if errors:
            QMessageBox.critical(self, "Apply failed", "Some settings failed to apply:\n" + "\n".join(errors))
        else:
            QMessageBox.information(self, "Applied", "Settings applied successfully.")
            # refresh UI to remove asterisks
            current_item = self.tree.currentItem()
            if current_item:
                self.on_tree_item_clicked(current_item, 0)

    def on_ok(self):
        """Apply and close if successful."""
        if self.pending_changes:
            self.on_apply()
            # if after apply there are still pending changes, don't close
            if self.pending_changes:
                return
        self.accept()
