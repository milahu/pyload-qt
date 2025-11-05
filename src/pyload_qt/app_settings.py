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
        self.config = {}
        self._init_ui()
        self.client.get_core_and_plugins_config(self.on_config)
        # self.client.get_core_and_plugins_and_accounts_config(self.on_config)

    def on_config(self, config: dict):
        """Called when client returns combined core+plugins config."""
        # FIXME handle errors
        self.config = config or {}
        self._populate_tree()

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

    def _populate_tree(self):
        self.tree.clear()
        # section = "core", "plugins"
        for section in sorted(self.config.keys()):
            section_root = QTreeWidgetItem(self.tree, [section])
            section_root.setData(0, Qt.UserRole, (section, None))
            for category_key in sorted(self.config[section].keys()):
                category = self.config[section][category_key]
                node = QTreeWidgetItem(section_root, [category.get("name", category_key)])
                node.setData(0, Qt.UserRole, (section, category_key))

        self.tree.expandAll()

        # auto-select first category if available
        first_section = self.tree.topLevelItem(0)
        if first_section and first_section.childCount() > 0:
            sel_item = first_section.child(0)
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

    def _populate_table(self, items):
        """Populate the right-hand table with description + widget per item."""
        self.table.clearContents()
        self.table.setRowCount(0)
        for idx, it in enumerate(items):
            name = it.get("name")
            desc = it.get("description", name)
            value = it.get("value", "")
            type_str = it.get("type", "str")

            self.table.insertRow(idx)
            desc_item = QTableWidgetItem(desc)
            desc_item.setFlags(desc_item.flags() ^ Qt.ItemIsEditable)
            # attach metadata to description item so we can find option name later
            desc_item.setData(Qt.UserRole, {"option": name, "type": type_str})
            self.table.setItem(idx, 0, desc_item)

            widget = self._create_value_widget(type_str, value, self._make_on_value_changed(self._current_section, self._current_category, name))
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
            combo.currentTextChanged.connect(lambda v: on_change_callable(str(v)))
            return combo

        if lower == "bool":
            cb = QCheckBox()
            cb.setChecked(str(value).lower() in ("1", "true", "yes", "on", "t"))
            cb.stateChanged.connect(lambda s: on_change_callable("True" if s == Qt.Checked else "False"))
            return cb

        if lower == "int":
            le = QLineEdit()
            le.setText(str(value))
            le.setValidator(QIntValidator())
            # on editingFinished, validate and call
            le.editingFinished.connect(lambda le=le: on_change_callable(le.text()))
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
            def browse():
                selected = QFileDialog.getExistingDirectory(self, "Select folder", le.text() or "/")
                if selected:
                    le.setText(selected)
                    on_change_callable(selected)
            btn.clicked.connect(browse)
            le.editingFinished.connect(lambda le=le: on_change_callable(le.text()))
            h.addWidget(le)
            h.addWidget(btn)
            return container

        # default: string
        le = QLineEdit()
        le.setText(str(value))
        le.editingFinished.connect(lambda le=le: on_change_callable(le.text()))
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
