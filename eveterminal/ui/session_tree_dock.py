"""
Dockable Session Manager Tree Sidebar.
Renders hierarchical folders and saved sessions matching SecureCRT's Connect Dialog.
"""

from typing import Dict, Any, Callable, Optional

try:
    from PyQt6.QtWidgets import QDockWidget, QTreeWidget, QTreeWidgetItem, QVBoxLayout, QWidget, QLineEdit, QPushButton
    from PyQt6.QtCore import Qt, pyqtSignal
    QT_API = "PyQt6"
except ImportError:
    try:
        from PySide6.QtWidgets import QDockWidget, QTreeWidget, QTreeWidgetItem, QVBoxLayout, QWidget, QLineEdit, QPushButton
        from PySide6.QtCore import Qt, Signal as pyqtSignal
        QT_API = "PySide6"
    except ImportError:
        QDockWidget = object
        QT_API = None


class SessionTreeDock(QDockWidget if QT_API else object):
    """Session Manager sidebar dock widget."""

    session_selected = pyqtSignal(str, dict) if QT_API else None

    def __init__(self, sessions: Dict[str, Dict[str, Any]], parent=None):
        if not QT_API:
            return
        super().__init__("Session Manager", parent)
        self.setAllowedAreas(Qt.DockWidgetArea.LeftDockWidgetArea | Qt.DockWidgetArea.RightDockWidgetArea)

        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(4, 4, 4, 4)

        # Filter box
        self.search_box = QLineEdit()
        self.search_box.setPlaceholderText("Filter sessions...")
        self.search_box.textChanged.connect(self._filter_tree)
        layout.addWidget(self.search_box)

        # Tree widget
        self.tree = QTreeWidget()
        self.tree.setHeaderHidden(True)
        self.tree.itemDoubleClicked.connect(self._on_item_double_clicked)
        layout.addWidget(self.tree)

        self.setWidget(container)
        self.sessions = sessions
        self.populate_tree()

    def populate_tree(self) -> None:
        if not QT_API:
            return
        self.tree.clear()

        # Build folder hierarchy
        root_nodes: Dict[str, QTreeWidgetItem] = {}

        for session_name, config in sorted(self.sessions.items()):
            parts = session_name.split("/")
            parent_item = self.tree.invisibleRootItem()

            current_path = ""
            for part in parts[:-1]:
                current_path = f"{current_path}/{part}" if current_path else part
                if current_path not in root_nodes:
                    folder_item = QTreeWidgetItem(parent_item, [part])
                    folder_item.setData(0, Qt.ItemDataRole.UserRole, {"is_folder": True})
                    root_nodes[current_path] = folder_item
                    parent_item = folder_item
                else:
                    parent_item = root_nodes[current_path]

            leaf_name = parts[-1]
            leaf_item = QTreeWidgetItem(parent_item, [leaf_name])
            leaf_item.setData(0, Qt.ItemDataRole.UserRole, {"is_folder": False, "name": session_name, "config": config})

        self.tree.expandAll()

    def _on_item_double_clicked(self, item: QTreeWidgetItem, column: int) -> None:
        data = item.data(0, Qt.ItemDataRole.UserRole)
        if data and not data.get("is_folder"):
            session_name = data.get("name")
            config = data.get("config", {})
            if self.session_selected:
                self.session_selected.emit(session_name, config)

    def _filter_tree(self, text: str) -> None:
        text = text.lower()
        iterator = QTreeWidgetItem(self.tree.invisibleRootItem())
        # Traverse and filter
        def filter_item(item: QTreeWidgetItem) -> bool:
            match = text in item.text(0).lower()
            child_matches = False
            for i in range(item.childCount()):
                if filter_item(item.child(i)):
                    child_matches = True
            item.setHidden(not (match or child_matches))
            if match or child_matches:
                item.setExpanded(True)
            return match or child_matches

        for i in range(self.tree.topLevelItemCount()):
            filter_item(self.tree.topLevelItem(i))
