# Optimize Packages Table

**User:** Anonymous  
**Created:** 2026/11/14 18:17:04  
**Updated:** 2026/11/14 18:21:45  
**Exported:** 2026/11/14 18:23:38  
**Link:** [<https://chatgpt.com/c/6af8978f-7f84-83eb-9d16-ad6f9e6a2c39>](https://chatgpt.com/c/6af8978f-7f84-83eb-9d16-ad6f9e6a2c39)

## Prompt:

11/14/2026, 6:17:26 PM

help me optimize my pyside6 gui app "pyload-qt"

currently the packages table is loading too slow. it takes about 16 seconds to render about 30K table rows:

    $ ./pyload_qt.sh
    on_queue_and_collector_received: received data: dt=1.02 N=33376
    on_queue_and_collector_received: filled table: dt=16.35 N=33376

generally, i want to refactor the packages table to a "SQL view". i know that Qt has some SQL classes, and i want to use them to render different views of the packages table, implementing sorting, filtering, searching, incremental updates, ...

currently, i am creating the Qt table item widgets directly from the package data from the pyLoad backend, but that approach is not scalable, both in terms of performance (rendering large tables is too slow) and in terms of features (implementing complex data-processing features from scratch is a waste of time if i can delegate most of the work to existing Qt SQL functions)

`https://github.com/milahu/pyload-qt/blob/main/src/pyload_qt/ui/packages.py`

``` python
import os
import re
import json
import time

from PySide6.QtCore import (
    Qt,
)
from PySide6.QtWidgets import (
    QAbstractItemView,
    QMessageBox,
    QTableWidget,
    QTableWidgetItem,
)

from .sort_key_table_widget_item import SortKeyTableWidgetItem

class PackagesMixin:

    def create_packages_table(self):
        table = QTableWidget()
        column_labels = []

        num_cols = 5

        # the package ID is useful for debugging
        self.packages_table_has_package_id_column = False
        # self.packages_table_has_package_id_column = True

        if self.packages_table_has_package_id_column:
            num_cols += 1

        # workaround: table.setColumnWidth works only if we call table.setColumnCount before
        table.setColumnCount(num_cols)

        col = 0

        # Position
        column_labels.append("Pos")
        # default column width is 100
        # NOTE leave room for vertical scrollbar
        table.setColumnWidth(col, 10) # Pos "12345"
        package_position_col = col
        col += 1

        if self.packages_table_has_package_id_column:
            # Package ID = "PID"
            column_labels.append("ID")
            table.setColumnWidth(col, 20)
            col += 1

        # Package Name
        column_labels.append("Package")
        table.setColumnWidth(col, 640)
        col += 1

        # Status: "Active" | "Paused"
        column_labels.append("Status")
        table.setColumnWidth(col, 150)
        col += 1

        # Progress "12.3%"
        column_labels.append("Progress")
        table.setColumnWidth(col, 70)
        col += 1

        # Size "1000.00 MiB"
        column_labels.append("Size")
        table.setColumnWidth(col, 90)
        col += 1

        # table.setColumnCount(len(column_labels))
        assert len(column_labels) == num_cols
        table.setHorizontalHeaderLabels(column_labels)
        # table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        table.setSelectionBehavior(QTableWidget.SelectRows)
        # table.setSelectionMode(QTableWidget.SingleSelection)
        table.itemSelectionChanged.connect(self.on_package_selected)
        table.itemDoubleClicked.connect(self.on_package_doubleclicked)
        table.setSortingEnabled(True)
        table.verticalHeader().setVisible(False)
        # "Pos" is short for "Position"
        table.horizontalHeaderItem(package_position_col).setToolTip("Position")
        # sort by package position
        table.sortItems(package_position_col, Qt.AscendingOrder)
        table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        # TODO filter by search expression (regex?)
        # TODO select multiple packages -> rightclick -> remove / ...
        table.setContextMenuPolicy(Qt.CustomContextMenu)
        table.customContextMenuRequested.connect(self.show_packages_context_menu)
        return table

    def packages_table_set_status_filter(self, status_id):
        table = self.packages_table
        max_status_id = 5
        if not (0 <= status_id <= max_status_id):
            raise ValueError(f"bad status_id {status_id}")
        # FIXME this conflicts with on_package_filter_change
        if status_id == 0: # all
            for row_idx in range(table.rowCount()):
                table.setRowHidden(row_idx, False)
        else:
            for row_idx in range(table.rowCount()):
                package_queue_col_idx = 2 # Status: Queue or Collector
                package_progress_col_idx = 3 # Progress
                hidden = False
                if status_id in (1, 2):
                    package_queue_item = table.item(row_idx, package_queue_col_idx)
                    if package_queue_item is None:
                        continue
                    package_queue = package_queue_item.data(Qt.UserRole)
                    if status_id == 1: # active aka "pyload queue"
                        hidden = not(package_queue)
                    elif status_id == 2: # paused aka "pyload collector"
                        hidden = package_queue
                if status_id in (3, 4, 5):
                    package_progress_item = table.item(row_idx, package_progress_col_idx)
                    if package_progress_item is None:
                        continue
                    package_progress = package_progress_item.data(Qt.UserRole)
                    if status_id == 3: # complete
                        hidden = (package_progress < 1)
                    elif status_id == 4: # partial
                        hidden = (package_progress in (0, 1))
                    elif status_id == 5: # empty
                        hidden = (package_progress > 0)
                table.setRowHidden(row_idx, hidden)

    def on_package_filter_change(self):
        filter_text = self.package_filter_input.text().strip()
        print("on_package_filter_change", repr(filter_text))
        table = self.packages_table
        if not filter_text:
            # show all rows
            for row_idx in range(table.rowCount()):
                table.setRowHidden(row_idx, False)
        # https://stackoverflow.com/a/6785516/10440128
        regex = re.compile(filter_text, re.I)
        for row_idx in range(table.rowCount()):
            col_idx = 1
            package_name = table.item(row_idx, col_idx).text()
            table.setRowHidden(row_idx, not(bool(regex.search(package_name))))

    def reload_packages_table(self):
        return self.refresh_queue()

    def refresh_queue(self):
        if 1:
            # debug timings
            self.t1_refresh_queue = time.time()
        self.client.get_queue_and_collector(self.on_queue_and_collector_received)

    def on_queue_and_collector_received(self, queue_data):
        # FIXME preserve the previous sort order
        # https://stackoverflow.com/questions/11826257
        if hasattr(self, "t1_refresh_queue"):
            # debug timings
            t1 = self.t1_refresh_queue
            t2 = time.time()
            print(f"on_queue_and_collector_received: received data: dt={t2 - t1:.2f} N={len(queue_data)}")
            t1 = time.time()
        if 0:
            # debug: limit queue size to get faster UI
            queue_data = queue_data[:100]
        self.debug_pid = None
        if self.debug_pid:
            for pkg in queue_data:
                if pkg["pid"] == self.debug_pid:
                    print(f"on_queue_received pkg {self.debug_pid} = {json.dumps(pkg, indent=2)}")
                    break
        self.queue_data_cache = queue_data
        if queue_data is None:
            QMessageBox.warning(self, "Error", "Could not fetch queue")
            return

        table = self.packages_table
        table.clearContents()
        self.packages_table.setRowCount(len(queue_data))
        for row, package in enumerate(queue_data):
            col = 0

            # Position
            position_item = SortKeyTableWidgetItem(str(row + 1), (row + 1))
            # package_id is stored in cell 0
            position_item.setData(Qt.UserRole, package["pid"])  # Store package ID
            self.packages_table.setItem(row, col, position_item)
            col += 1

            if self.packages_table_has_package_id_column:
                # Package ID = "PID"
                package_id = package["pid"] # package ID
                package_id_text = str(package_id)
                package_id_item = SortKeyTableWidgetItem(package_id_text, package_id)
                self.packages_table.setItem(row, col, package_id_item)
                col += 1

            # Name
            name_item = QTableWidgetItem(package["name"])
            self.packages_table.setItem(row, col, name_item)
            col += 1

            # Status: Queue or Collector
            status_str = "Active" if package["queue"] else "Paused"
            item = QTableWidgetItem(status_str)
            item.setData(Qt.UserRole, package["queue"])
            self.packages_table.setItem(row, col, item)
            col += 1

            # Progress
            if package["sizetotal"] > 0:
                progress = (package["linksdone"] / package["linkstotal"])
                progress_text = f"{(progress * 100):.1f}%"
            else:
                progress = 0
                progress_text = "0.0%"
            # self.packages_table.setItem(row, 1, QTableWidgetItem(progress_text))
            progress_item = SortKeyTableWidgetItem(progress_text, progress)
            progress_item.setData(Qt.UserRole, progress)
            self.packages_table.setItem(row, col, progress_item)
            col += 1

            # Size
            size = package["sizetotal"]
            size_mb = package["sizetotal"] / (1024 * 1024)
            size_text = f"{size_mb:.2f} MB"
            # self.packages_table.setItem(row, 2, QTableWidgetItem(size_text))
            size_item = SortKeyTableWidgetItem(size_text, size)
            self.packages_table.setItem(row, col, size_item)
            col += 1

        if hasattr(self, "t1_refresh_queue"):
            # debug timings
            t2 = time.time()
            print(f"on_queue_and_collector_received: filled table: dt={t2 - t1:.2f} N={len(queue_data)}")

    def on_package_selected(self):
        selected_items = self.packages_table.selectedItems()
        if not selected_items:
            return

        # Get package ID from the first column of selected row
        pid = self.packages_table.item(selected_items[0].row(), 0).data(Qt.UserRole)
        assert pid # TODO can this be None?
        self.selected_package_pid = pid
        self.refresh_bottom_view()

    def on_package_doubleclicked(self):
        selected_items = self.packages_table.selectedItems()
        if not selected_items:
            return
        if not self.client.is_localhost: return

        storage_folder = self.get_config_value("core", "general", "storage_folder")

        def on_package_data_received(package_data):
            # print(f"on_package_doubleclicked package_data {package_data}")
            folder_path = os.path.join(storage_folder, package_data["folder"])
            if not os.path.exists(folder_path):
                print(f"missing folder_path {folder_path!r}")
                return
            args = [
                "xdg-open",
                folder_path,
            ]
            subprocess.Popen(args)

        pid = self.packages_table.item(selected_items[0].row(), 0).data(Qt.UserRole)
        assert pid # TODO can this be None?
        self.client.get_package_data(on_package_data_received, pid)
```

## Response:

11/14/2026, 6:17:41 PM

> **Searched 5 websites**
>
> Worked for 29s

Your instinct to move away from `QTableWidget` is correct. For 33,376 packages, **16 seconds is far too slow**, and the current architecture will make sorting, filtering, searching, and incremental updates unnecessarily expensive.

I would refactor `pyload-qt` around **`QTableView` + `QSqlQueryModel` + SQLite**, with a small synchronization layer between the pyLoad backend and the database.

There is also a simpler alternative, `QAbstractTableModel`, which may actually be faster for your current workload. I'll compare both approaches, then show how I'd implement the SQL-based version.

## 1. Why your current table is slow

Your current code creates at least five `QTableWidgetItem` objects per package:

<box gap={1}>
  <grid columns={3} gap={2}>
    <grid-item>
      <box background="surface-secondary" radius="lg" padding={3} align="center" gap={1}>
        <title size="xl" color="default" tabularNums>33,376</title>
        <caption>Packages</caption>
      </box>
    </grid-item>
    <grid-item>
      <box background="surface-secondary" radius="lg" padding={3} align="center" gap={1}>
        <title size="xl" color="default" tabularNums>166,880</title>
        <caption>Table items</caption>
      </box>
    </grid-item>
    <grid-item>
      <box background="surface-secondary" radius="lg" padding={3} align="center" gap={1}>
        <title size="xl" color="default" tabularNums>16.35s</title>
        <caption>Population time</caption>
      </box>
    </grid-item>
  </grid>
</box>

Each `setItem()` call crosses the Python/C++ boundary, updates Qt's internal item storage, and may trigger model notifications, sorting, or view updates.

Your code also enables sorting before inserting the rows:

This is especially problematic. With sorting enabled, inserting items into the current sort column can cause rows to move while you're populating them.

### Immediate performance fix

Before doing a larger refactor, try disabling sorting and UI updates during population:

This may substantially improve the current implementation, although the actual speedup needs benchmarking.

However, I wouldn't stop there. Your feature requirements justify a model/view refactor.

## 2. Choosing the architecture

Qt offers several approaches:

| Architecture | Performance | SQL features | Complexity |
|----|----|----|----|
| `QTableWidget` | Poor for large updates | None | Low |
| `QTableView` + `QAbstractTableModel` | Excellent for in-memory data | Manual filtering/sorting | Medium |
| `QTableView` + `QSortFilterProxyModel` | Good | Qt-based filtering/sorting | Medium |
| `QTableView` + `QSqlTableModel` | Good | SQL-backed table, editable | Medium |
| `QTableView` + `QSqlQueryModel` | Good | Custom SQL queries and views | Medium |

**For your SQL-view idea, I'd choose `QSqlQueryModel`.**

`QSqlTableModel` is designed primarily for working with a single SQL table. `QSqlQueryModel` lets you use custom SQL queries, joins, calculated columns, and SQLite views.

One important distinction: `QSqlQueryModel` doesn't automatically provide a complete SQL filtering or incremental-update engine. You'll need a small layer to construct queries, refresh results, and synchronize the backend.

The intended data flow would be:

<box border radius="xl" padding={3} gap={2}>
  <box background="surface-secondary" radius="md" padding={3} align="center" gap={1}>
    **pyLoad backend**

    <text color="secondary" size="xs">JSON packages via API</text>

  </box>
  <row justify="center" align="center" gap={2}>
    <icon name="arrow-down" color="secondary"/>
    <text color="secondary" size="xs">Batch UPSERT / DELETE</text>
  </row>
  <box border radius="md" padding={3} align="center" gap={1}>
    **SQLite database**

    <text color="secondary" size="xs">packages table + indexes + SQL views</text>

  </box>
  <row justify="center" align="center" gap={2}>
    <icon name="arrow-down" color="secondary"/>
    <text color="secondary" size="xs">SELECT / WHERE / ORDER BY</text>
  </row>
  <box background="surface-secondary" radius="md" padding={3} align="center" gap={1}>
    **QSqlQueryModel**

    <text color="secondary" size="xs">Qt model exposing query results</text>

  </box>
  <row justify="center" align="center">
    <icon name="arrow-down" color="secondary"/>
  </row>
  <box border radius="md" padding={3} align="center" gap={1}>
    **QTableView**

    <text color="secondary" size="xs">Virtualized presentation, selection, context menu</text>

  </box>
</box>

The big advantage is that you can express features as queries rather than loops over GUI rows.

For example:

SQLite handles the filtering and sorting, while Qt handles the visible table cells.

## 3. A practical SQL-backed implementation

I'd start with an in-memory SQLite database. You don't need persistence because pyLoad is already the authoritative data source.

Using `:memory:` also avoids filesystem overhead.

### Step 1 - Create the database

Create `src/pyload_qt/ui/packages_database.py`:

<CodeBlock language="python" editable>
from PySide6.QtSql import QSqlDatabase, QSqlQuery

class PackagesDatabase:  
def **init**(self):  
self.db = QSqlDatabase.addDatabase(  
"QSQLITE", "packages"  
)  
self.db.setDatabaseName(":memory:")

        if not self.db.open():
            raise RuntimeError(
                self.db.lastError().text()
            )

        self.execute("""
            CREATE TABLE packages (
                pid INTEGER PRIMARY KEY,
                position INTEGER NOT NULL,
                name TEXT NOT NULL,
                queue INTEGER NOT NULL,
                linksdone INTEGER NOT NULL,
                linkstotal INTEGER NOT NULL,
                sizetotal INTEGER NOT NULL
            )
        """)

        self.execute("""
            CREATE INDEX packages_name_idx
            ON packages(name COLLATE NOCASE)
        """)

        self.execute("""
            CREATE VIEW packages_view AS
            SELECT
                position,
                pid,
                name,
                CASE WHEN queue = 1
                    THEN 'Active'
                    ELSE 'Paused'
                END AS status,
                CASE WHEN linkstotal > 0
                    THEN 100.0 * linksdone / linkstotal
                    ELSE 0.0
                END AS progress,
                sizetotal / 1048576.0 AS size_mb,
                queue,
                sizetotal
            FROM packages
        """)

    def execute(self, sql):
        query = QSqlQuery(self.db)
        if not query.exec(sql):
            raise RuntimeError(
                query.lastError().text()
            )
        return query

    def sync(self, packages):
        """Replace snapshot atomically, preserving PIDs."""
        if not self.db.transaction():
            raise RuntimeError(
                self.db.lastError().text()
            )

        try:
            self.execute("DELETE FROM packages")

            query = QSqlQuery(self.db)
            query.prepare("""
                INSERT INTO packages (
                    pid, position, name, queue,
                    linksdone, linkstotal, sizetotal
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """)

            for position, pkg in enumerate(packages, 1):
                values = (
                    pkg["pid"],
                    position,
                    pkg["name"],
                    int(pkg["queue"]),
                    pkg["linksdone"],
                    pkg["linkstotal"],
                    pkg["sizetotal"],
                )

                for i, value in enumerate(values):
                    query.bindValue(i, value)

                if not query.exec():
                    raise RuntimeError(
                        query.lastError().text()
                    )

            if not self.db.commit():
                raise RuntimeError(
                    self.db.lastError().text()
                )

        except Exception:
            self.db.rollback()
            raise

</CodeBlock>

This initial implementation deliberately uses a full snapshot replacement to keep synchronization simple.

Even though it still performs 33,376 inserts, these are prepared SQL operations inside one transaction, rather than 166,880 individual GUI item insertions.

The next optimization would be to replace this with an incremental `UPSERT` strategy.

### Step 2 - Create a SQL query model

Create `src/pyload_qt/ui/packages_model.py`:

<CodeBlock language="python" editable>
from PySide6.QtCore import Qt
from PySide6.QtSql import QSqlQuery, QSqlQueryModel

class PackagesModel(QSqlQueryModel):  
COLUMNS = (  
"position",  
"name",  
"status",  
"progress",  
"size_mb",  
)

    HEADERS = (
        "Pos",
        "Package",
        "Status",
        "Progress",
        "Size",
    )

    SORT_COLUMNS = (
        "position",
        "name COLLATE NOCASE",
        "status",
        "progress",
        "sizetotal",
    )

    def __init__(self, db, parent=None):
        super().__init__(parent)
        self.db = db
        self.search_text = ""
        self.status_filter = 0
        self.sort_column = 0
        self.sort_order = Qt.AscendingOrder
        self.refresh()

    def refresh(self):
        conditions = []
        params = []

        if self.search_text:
            conditions.append(
                "instr(lower(name), lower(?)) > 0"
            )
            params.append(self.search_text)

        filters = {
            1: "queue = 1",
            2: "queue = 0",
            3: "progress >= 100",
            4: "progress > 0 AND progress < 100",
            5: "progress = 0",
        }

        if self.status_filter in filters:
            conditions.append(
                filters[self.status_filter]
            )

        where = (
            "WHERE " + " AND ".join(conditions)
            if conditions else ""
        )

        direction = (
            "DESC"
            if self.sort_order == Qt.DescendingOrder
            else "ASC"
        )

        order_by = self.SORT_COLUMNS[
            self.sort_column
        ]

        sql = f"""
            SELECT
                position, name, status,
                progress, size_mb, pid
            FROM packages_view
            {where}
            ORDER BY {order_by} {direction}, pid ASC
        """

        query = QSqlQuery(self.db)

        if not query.prepare(sql):
            raise RuntimeError(
                query.lastError().text()
            )

        for value in params:
            query.addBindValue(value)

        if not query.exec():
            raise RuntimeError(
                query.lastError().text()
            )

        self.setQuery(query)

        if self.lastError().isValid():
            raise RuntimeError(
                self.lastError().text()
            )

        for col, label in enumerate(self.HEADERS):
            self.setHeaderData(
                col, Qt.Horizontal, label
            )

    def sort(self, column, order):
        if not 0 <= column < len(self.COLUMNS):
            return

        self.sort_column = column
        self.sort_order = order
        self.refresh()

    def set_search(self, text):
        if text == self.search_text:
            return
        self.search_text = text
        self.refresh()

    def set_status_filter(self, status_id):
        if status_id not in range(6):
            raise ValueError(status_id)
        self.status_filter = status_id
        self.refresh()

    def data(self, index, role=Qt.DisplayRole):
        if not index.isValid():
            return None

        if role == Qt.DisplayRole:
            if index.column() == 3:
                value = super().data(index, role)
                return f"{float(value):.1f}%"

            if index.column() == 4:
                value = super().data(index, role)
                return f"{float(value):.2f} MiB"

        return super().data(index, role)

    def package_id(self, row):
        # Hidden sixth query column
        index = self.index(row, 5)
        return self.data(index, Qt.DisplayRole)

</CodeBlock>

A few important details:

- The `pid` is included as a hidden sixth column, so you can retrieve it regardless of sorting.
- Numeric sorting happens in SQL, not on formatted strings.
- Search and status filters are combined with `AND`, fixing the conflict between your two existing filtering methods.
- SQL sorting uses an allowlist of column expressions, not user-provided SQL.
- `QSqlQueryModel` can fetch query results incrementally with SQLite, although this is not the same as incremental synchronization of package changes. \<Cite refs={\["turn540443search0","turn540443search2"\]}/\>

### Step 3 - Replace `QTableWidget` with `QTableView`

Your `create_packages_table()` becomes much smaller:

<CodeBlock language="python" editable>
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QAbstractItemView,
    QTableView,
)

from .packages_database import PackagesDatabase  
from .packages_model import PackagesModel

def create_packages_table(self):  
self.packages_database = PackagesDatabase()

    self.packages_model = PackagesModel(
        self.packages_database.db, self
    )

    table = QTableView()
    table.setModel(self.packages_model)

    table.setColumnHidden(5, True)

    for col, width in enumerate(
        (60, 640, 150, 90, 100)
    ):
        table.setColumnWidth(col, width)

    table.setSelectionBehavior(
        QAbstractItemView.SelectRows
    )
    table.setSelectionMode(
        QAbstractItemView.ExtendedSelection
    )
    table.setEditTriggers(
        QAbstractItemView.NoEditTriggers
    )

    table.setSortingEnabled(True)
    table.verticalHeader().hide()

    table.selectionModel().selectionChanged.connect(
        self.on_package_selected
    )
    table.doubleClicked.connect(
        self.on_package_doubleclicked
    )

    table.setContextMenuPolicy(
        Qt.CustomContextMenu
    )
    table.customContextMenuRequested.connect(
        self.show_packages_context_menu
    )

    return table

</CodeBlock>

And the callback that previously populated thousands of items becomes:

No `setRowCount()`, no `setItem()`, and no manual creation of cell objects.

### Step 4 - Connect filtering and searching

Your old filter functions can become:

``` python
def packages_table_set_status_filter(self, status_id):
    self.packages_model.set_status_filter(status_id)

def on_package_filter_change(self):
    self.packages_model.set_search(
        self.package_filter_input.text().strip()
    )
```

I'd also debounce the search input, so that SQL queries aren't executed on every keystroke:

Remove the old direct `textChanged` connection if one exists.

The sample implements case-insensitive substring search rather than regex search. If regex compatibility is important, you can register a SQLite `REGEXP` function or implement a more advanced search language later.

### Step 5 - Adapt package selection

With `QTableView`, use selected model rows instead of `selectedItems()`.

``` python
def get_selected_package_pid(self):
    rows = self.packages_table.selectionModel().selectedRows()

    if not rows:
        return None

    return self.packages_model.package_id(rows[0].row())

def on_package_selected(self, *args):
    pid = self.get_selected_package_pid()

    if pid is None:
        return

    self.selected_package_pid = pid
    self.refresh_bottom_view()
```

For double-clicking:

Your context menu implementation will also need to switch from `QTableWidget` item APIs to model indexes.

## 4. Incremental updates: the next optimization

The initial implementation still deletes and reinserts every package on refresh.

That's acceptable for a first benchmark, but it isn't ideal if pyLoad sends frequent updates.

Eventually, I'd use SQLite `UPSERT`:

For full snapshots, you also need to remove packages that no longer exist. A good approach is to assign a generation number to each synchronization, mark incoming packages with that generation, then delete rows belonging to older generations.

This gives you efficient database synchronization without having to reconstruct the entire SQLite table.

There is an important limitation, though:

**Incrementally updating SQLite does not automatically incrementally update `QSqlQueryModel`.**

Calling `setQuery()` again resets the model's result set. That can disturb selection, scroll position, and the current row.

For a first version, preserve the selected package IDs before refreshing, then restore selection afterward. For a more advanced version, consider a custom `QAbstractTableModel` that emits `dataChanged()`, `beginInsertRows()`, and `beginRemoveRows()` for targeted updates.

## 5. A few issues worth fixing during the refactor

Your existing code has some unrelated correctness problems:

- **Column indexes:** Your status filter assumes that Status is column 2 and Progress is column 3. Enabling the optional PID column shifts these indexes.
- **Progress calculation:** You check `sizetotal > 0` but divide by `linkstotal`. Check `linkstotal > 0` instead to prevent division by zero.
- **Search regex:** `re.compile()` can raise `re.error` for an incomplete expression, such as `[`.
- **Null data:** `len(queue_data)` is called before checking whether `queue_data is None`.
- **Missing import:** Your double-click handler uses `subprocess.Popen()` without importing `subprocess` in the provided file.
- **Selection:** Replacing or requerying the model can cause selection changes. Avoid unnecessary bottom-view refreshes while synchronizing.

Also, avoid calling `resizeColumnsToContents()` on a large table. It can trigger expensive measurements across many rows.

## 6. What performance should you expect?

I would benchmark the SQL implementation in three separate phases.

<box border radius="lg" padding={3} gap={2}>
  <text weight="medium" size="sm">Suggested performance measurements</text>
  <text color="secondary" size="xs">Illustrative targets, not measured results</text>
  <table>
    <table-row><table-cell>Backend fetch</table-cell><table-cell align="end">Current: ~1.02s</table-cell></table-row>
    <table-row><table-cell>SQLite synchronization</table-cell><table-cell align="end">Measure separately</table-cell></table-row>
    <table-row><table-cell>SQL query/model refresh</table-cell><table-cell align="end">Measure separately</table-cell></table-row>
    <table-row><table-cell>First visible paint</table-cell><table-cell align="end">Measure separately</table-cell></table-row>
  </table>
</box>

Your current 16.35-second measurement covers population of the widget, not necessarily the complete painting of every row.

The new architecture should eliminate much of that overhead, but I wouldn't promise a particular speedup before measuring it.

One subtlety: `QSqlQueryModel` can fetch rows incrementally, so the first paint may finish before all 33,376 rows have been fetched. This is useful for responsiveness, but your benchmark should distinguish initial display from complete result-set loading.

## 7. My suggested implementation order

<box gap={3}>
  <row align="start" gap={3}>
    <icon name="check-circle" color="success" size="lg"/>
    <box flex="1" gap={1}>
      **Phase 1 - Quick benchmark**

      Disable sorting and UI updates around your existing population loop. Measure how much time this saves before changing architecture.
    </box>

  </row>
  <divider color="subtle"/>
  <row align="start" gap={3}>
    <icon name="database" color="secondary" size="lg"/>
    <box flex="1" gap={1}>
      **Phase 2 - SQL model/view migration**

      Implement `QTableView`, SQLite, and `QSqlQueryModel`. Preserve existing selection and double-click functionality.
    </box>

  </row>
  <divider color="subtle"/>
  <row align="start" gap={3}>
    <icon name="search" color="secondary" size="lg"/>
    <box flex="1" gap={1}>
      **Phase 3 - Query features**

      Implement combined status filters, searching, SQL sorting, and additional package views.
    </box>

  </row>
  <divider color="subtle"/>
  <row align="start" gap={3}>
    <icon name="refresh-cw" color="secondary" size="lg"/>
    <box flex="1" gap={1}>
      **Phase 4 - Incremental synchronization**

      Add `UPSERT`, deletion detection, and selection restoration. Benchmark frequent refreshes.
    </box>

  </row>
</box>

### One architectural decision I'd reconsider

If SQLite is only going to mirror the 33,376 packages already held in `self.queue_data_cache`, you may not need a database at all.

A custom `QAbstractTableModel` backed by a Python list, combined with `QSortFilterProxyModel`, is often the simplest and most efficient approach for this amount of data. Qt's model/view architecture already solves the expensive item-per-cell problem. \<Cite refs={\["turn540443search8","turn540443search2"\]}/\>

SQL becomes particularly attractive when you want complex queries, joins, aggregation, saved views, or database-backed filtering.

**My recommendation:** Start with the SQL implementation above if rich SQL queries are a central part of your roadmap. Otherwise, benchmark a list-backed `QAbstractTableModel` against it before committing to SQLite.

One question that will determine the best long-term architecture: **Does pyLoad always send the complete list of ~33K packages on refresh, or can it also send individual package-change events (added, removed, progress changed)?**

That distinction matters a lot for designing truly incremental updates.

## Response:

11/14/2026, 6:17:56 PM

------------------------------------------------------------------------

Powered by [ChatGPT Exporter](https://www.chatgptexporter.com)
