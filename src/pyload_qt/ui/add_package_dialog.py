from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QPlainTextEdit,
    QDialog,
    QVBoxLayout,
)


class AddPackageDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Add Package")
        self.setModal(True)
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)

        # Package name
        name_layout = QHBoxLayout()
        name_layout.addWidget(QLabel("Package Name:"))
        self.package_name_input = QLineEdit()
        name_layout.addWidget(self.package_name_input)
        layout.addLayout(name_layout)

        # Links input
        layout.addWidget(QLabel("Links (one per line or space separated):"))
        self.links_input = QPlainTextEdit()
        layout.addWidget(self.links_input)

        # Package password
        password_layout = QHBoxLayout()
        password_layout.addWidget(QLabel("Password:"))
        self.package_password_input = QLineEdit()
        password_layout.addWidget(self.package_password_input)
        layout.addLayout(password_layout)

        # Buttons
        button_layout = QHBoxLayout()
        self.add_button = QPushButton("Add Package")
        self.add_button.clicked.connect(self.accept)
        button_layout.addWidget(self.add_button)
        layout.addLayout(button_layout)

    def get_package_data(self):
        name = self.package_name_input.text().strip()
        links_text = self.links_input.toPlainText().strip()
        url_pattern = re.compile(r'https?://[^\s<>"]+|www\.[^\s<>"]+')
        links = url_pattern.findall(links_text)
        password = self.package_password_input.text().strip()
        return name, links, password
