# src/ui/main_window_ui.py
# 修正:
# - QAbstractItemView import 追加
# - _create_download_tab: download_listのSelectionModeをExtendedSelectionに設定して複数選択を許可

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLineEdit, QPushButton, QTextEdit,
    QLabel, QListWidget, QFrame, QSplitter, QTabWidget, QToolButton, QMenu,
    QComboBox, QAbstractItemView
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QAction

from src.icon import get_app_icon

class MainWindowUI:
    def __init__(self, main_window):
        self.main_window = main_window
        main_window.setWindowIcon(get_app_icon())
        main_window.resize(1100, 700)

    def setup_ui(self):
        central = QWidget()
        self.main_window.setCentralWidget(central)
        root = QVBoxLayout(central); root.setContentsMargins(0, 0, 0, 0); root.setSpacing(0)
        self._create_header(root)
        self._create_input_bar(root)
        self._create_tabs(root)

    def _create_header(self, root_layout):
        header = QFrame(objectName="AppHeader")
        layout = QHBoxLayout(header); layout.setContentsMargins(16, 10, 16, 10); layout.setSpacing(8)
        self.app_title = QLabel("TVerダウンローダー (TVer Downloader)", objectName="AppTitle")
        self.about_button = QPushButton("情報", objectName="InfoButton")
        self.settings_button = QPushButton("設定", objectName="PrimaryButton")
        self.on_top_btn = QToolButton(objectName="OnTopButton", toolTip="常に上")
        self.on_top_btn.setCheckable(True)
        self.on_top_btn.setFixedSize(28, 28)
        layout.addWidget(self.app_title); layout.addStretch(1)
        layout.addWidget(self.settings_button)
        layout.addWidget(self.about_button)
        layout.addWidget(self.on_top_btn)
        root_layout.addWidget(header)

    def _create_input_bar(self, root_layout):
        input_bar = QFrame(objectName="InputBar")
        layout = QHBoxLayout(input_bar); layout.setContentsMargins(16, 12, 16, 12); layout.setSpacing(10)
        self.url_input = QLineEdit(placeholderText="TVer 動画のURLを貼り付ける", objectName="UrlInput")
        self.bulk_button = QPushButton("複数追加", objectName="OrangeButton")
        self.add_button = QPushButton("ダウンロード", objectName="AccentButton")
        layout.addWidget(self.url_input, 1); layout.addWidget(self.bulk_button); layout.addWidget(self.add_button)
        root_layout.addWidget(input_bar)

    def _create_tabs(self, root_layout):
        self.tabs = QTabWidget(objectName="MainTabs")
        self._create_download_tab()
        self._create_history_tab()
        self._create_favorites_tab()
        root_layout.addWidget(self.tabs, 1)

    def _create_download_tab(self):
        tab = QWidget(objectName="DownloadTab"); layout = QVBoxLayout(tab)
        layout.setContentsMargins(12, 12, 12, 12); layout.setSpacing(8)
        splitter = QSplitter(Qt.Orientation.Horizontal, objectName="MainSplitter")
        left_pane = QFrame(objectName="LeftPane"); left_layout = QVBoxLayout(left_pane)
        left_layout.setContentsMargins(8, 8, 8, 8); row = QHBoxLayout()
        self.queue_label = QLabel("ダウンロード一覧", objectName="PaneTitle")
        self.clear_completed_button = QPushButton("完了した項目の削除", objectName="GhostButton")
        self.queue_count_label = QLabel("0 待機 / 0 進行", objectName="PaneSubtitle")
        row.addWidget(self.queue_label); row.addStretch(1)
        row.addWidget(self.clear_completed_button)
        row.addWidget(self.queue_count_label)
        left_layout.addLayout(row)
        self.download_list = QListWidget(objectName="DownloadList")
        self.download_list.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        # --- 複数選択モードの設定 ---
        self.download_list.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        left_layout.addWidget(self.download_list, 1)
        right_pane = QFrame(objectName="RightPane"); right_layout = QVBoxLayout(right_pane)
        right_layout.setContentsMargins(8, 8, 8, 8); row_log = QHBoxLayout()
        self.log_title = QLabel("ログ", objectName="PaneTitle")
        self.clear_log_button = QPushButton("削除", objectName="GhostButton")
        row_log.addWidget(self.log_title); row_log.addStretch(1); row_log.addWidget(self.clear_log_button)
        self.log_output = QTextEdit(objectName="LogOutput", readOnly=True)
        right_layout.addLayout(row_log); right_layout.addWidget(self.log_output, 1)
        splitter.addWidget(left_pane); splitter.addWidget(right_pane); splitter.setSizes([640, 480])
        layout.addWidget(splitter, 1); self.tabs.addTab(tab, "ダウンロード")

    def _create_history_tab(self):
        tab = QWidget(objectName="HistoryTab")
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(8)
        top_controls = QHBoxLayout()
        self.history_title = QLabel("ダウンロード履歴", objectName="PaneTitle")
        self.history_sort_combo = QComboBox()
        self.history_sort_combo.addItem("ダウンロード 最新順")
        self.history_sort_combo.addItem("タイトル 昇順")
        self.history_search_input = QLineEdit(placeholderText="検索...")
        self.history_search_input.setClearButtonEnabled(True)
        self.history_search_input.setFixedWidth(200)
        top_controls.addWidget(self.history_title)
        top_controls.addStretch(1)
        top_controls.addWidget(self.history_sort_combo)
        top_controls.addWidget(self.history_search_input)
        layout.addLayout(top_controls)
        self.history_list = QListWidget(objectName="HistoryList")
        self.history_list.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        layout.addWidget(self.history_list, 1)
        self.tabs.addTab(tab, "記録")

    def _create_favorites_tab(self):
        tab = QWidget(objectName="FavoritesTab")
        layout = QVBoxLayout(tab); layout.setContentsMargins(12, 12, 12, 12); layout.setSpacing(8)
        row = QHBoxLayout(); row.addWidget(QLabel("お気に入り（シリーズ）", objectName="PaneTitle")); row.addStretch(1); layout.addLayout(row)
        ctrl = QHBoxLayout()
        self.fav_input = QLineEdit(placeholderText="TVer シリーズURL (例: https://tver.jp/series/....)")
        self.fav_add_btn = QPushButton("追加", objectName="PrimaryButton")
        self.fav_del_btn = QPushButton("削除", objectName="DangerButton")
        self.fav_chk_btn = QPushButton("新しい動画を確認する", objectName="PurpleButton")
        ctrl.addWidget(self.fav_input, 1); ctrl.addWidget(self.fav_add_btn); ctrl.addWidget(self.fav_del_btn)
        ctrl.addWidget(self.fav_chk_btn); layout.addLayout(ctrl)
        self.fav_list = QListWidget(objectName="FavoritesList"); self.fav_list.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        layout.addWidget(self.fav_list, 1); self.tabs.addTab(tab, "お気に入り")
    
    def setup_tray(self, app_version):
        tray_icon = self.main_window.tray_icon; tray_icon.setIcon(get_app_icon())
        tray_icon.setToolTip(f"TVer Downloader {app_version}")
        tray_menu = QMenu()
        restore_action = QAction("ウィンドウの復元", self.main_window, triggered=self.main_window.bring_to_front)
        quit_action = QAction("完全に終了", self.main_window, triggered=self.main_window.quit_application)
        tray_menu.addAction(restore_action); tray_menu.addAction(quit_action)
        tray_icon.setContextMenu(tray_menu); tray_icon.show()