from PySide6.QtCore import (
    Qt,
)
from PySide6.QtWidgets import (
    QWidget,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QButtonGroup,
    QStackedWidget,
)


class EmptyObject(object):
     pass


class BottomViewMixin:

    def create_bottom_view(self):
        self.bottom_view_stack = stack = QStackedWidget()
        for view_name in self.bottom_view_names:
            if view_name == "Package":
                self.package_package_view = view = self.create_package_package_view()
            elif view_name == "Links":
                self.package_links_table = view = self.create_package_links_view()
            elif view_name == "Downloads":
                self.package_downloads_view = view = self.create_package_downloads_view()
            elif view_name == "Files":
                self.package_files_view = view = self.create_package_files_view()
            stack.addWidget(view)
        stack.setCurrentIndex(self.default_bottom_view_idx)
        return stack

    def get_bottom_view_idx(self):
        return self.bottom_view_stack.currentIndex()

    def set_bottom_view_idx(self, bottom_view_idx):
        self.bottom_view_stack.setCurrentIndex(bottom_view_idx)
        self.refresh_bottom_view()

    def create_package_package_view(self):
        label = QLabel("")
        label.setTextInteractionFlags(Qt.TextSelectableByMouse)
        return label

    def update_package_package_view(self):
        selected_items = self.packages_table.selectedItems()
        if not selected_items:
            self.package_package_view.setText("")
            return
        def on_package_data_received(package_data):
            self.current_package = package_data
            # if not self.current_package:
            #     self.package_package_view.setText("")
            #     return
            p = self.current_package
            text = "\n".join([
                f"package id: {p['pid']}",
                f"folder: {p['folder']}",
                f"password: {p['password']}",
                f"links: {len(p['links'])}",
            ])
            # self.package_package_view.setText(json.dumps(self.current_package, indent=2))
            self.package_package_view.setText(text)
        pid = self.packages_table.item(selected_items[0].row(), 0).data(Qt.UserRole)
        assert pid # TODO can this be None?
        self.client.get_package_data(on_package_data_received, pid)

    def create_bottom_view_button_group(self, main_layout):
        self.bottom_view_button_group = group = QButtonGroup(self)
        widget = QWidget()
        layout = QHBoxLayout(widget)
        self.bottom_view_button_list = []

        bottom_view_id_enum_args = []

        def add_button(idx, name):
            button = QPushButton(name, self)
            group.addButton(button)
            layout.addWidget(button)
            # button.clicked.connect(lambda b=button: self.toggle_bottom_view(b)) # b == True ?!
            # button.clicked.connect(lambda i=button_idx: self.toggle_bottom_view(i)) # i == True ?!
            button.clicked.connect(lambda: self.toggle_bottom_view(idx))
            button.setCheckable(True)
            self.bottom_view_button_list.append(button)
            bottom_view_id_enum_args.append((idx, name))
            return button

        button_idx = -1

        for name in self.bottom_view_names:
            button_idx += 1
            button = add_button(button_idx, name)
            if name == self.default_bottom_view_name:
                # this button is checked
                button.setChecked(True)
                self.bottom_button_checked_id = group.id(button)
                self.bottom_button_checked_button = button
                self.bottom_view_idx = button_idx

        assert self.bottom_view_idx

        self.BottomViewIdx = EmptyObject()
        for idx, name in bottom_view_id_enum_args:
            setattr(self.BottomViewIdx, name, idx)
        assert self.BottomViewIdx.Links

        main_layout.addWidget(widget)

    def toggle_bottom_view(self, clicked_button_idx):
        clicked_button = self.bottom_view_button_list[clicked_button_idx]
        if clicked_button_idx == self.bottom_view_idx:
            self.bottom_view_button_group.setExclusive(False)
            clicked_button.setChecked(False)
            self.bottom_view_idx = None
            self.bottom_view.hide()
        else:
            clicked_button.setChecked(True)
            self.bottom_view_button_group.setExclusive(True)
            self.bottom_view_idx = clicked_button_idx
            self.bottom_view.show()
            self.set_bottom_view_idx(clicked_button_idx)
