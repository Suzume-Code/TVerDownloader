# src/dialogs.py

from __future__ import annotations
from pathlib import Path
from PyQt6.QtCore import Qt, QSize
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton,
    QSpinBox, QTabWidget, QWidget, QFileDialog, QDialogButtonBox,
    QListWidget, QListWidgetItem, QAbstractItemView, QToolButton, QStyle,
    QRadioButton, QButtonGroup, QCheckBox, QMessageBox, QFrame, QComboBox,
    QFormLayout, QGroupBox
)
from src.utils import save_config, PARALLEL_MAX
from src.widgets import THUMBNAIL_CACHE_DIR

ROLE_KEY = Qt.ItemDataRole.UserRole

class SettingsDialog(QDialog):
    def __init__(self, config: dict, parent: QWidget | None = None):
        super().__init__(parent)
        self.config = config
        self.setWindowTitle("設定")
        self.setMinimumSize(560, 640)
        root = QVBoxLayout(self)
        self.tabs = QTabWidget(self)
        root.addWidget(self.tabs)
        self._create_general_tab()
        self._create_filename_tab()
        self._create_quality_tab()
        self._create_subtitle_tab()
        self._create_post_action_tab()
        self._create_advanced_tab()
        self._create_cache_tab()
        self.buttons = QDialogButtonBox()
        save_btn = self.buttons.addButton("設定を保存", QDialogButtonBox.ButtonRole.AcceptRole)
        exit_btn = self.buttons.addButton("戻る", QDialogButtonBox.ButtonRole.RejectRole)
        root.addWidget(self.buttons)
        save_btn.clicked.connect(self._save_settings)
        exit_btn.clicked.connect(self.reject)

    def showEvent(self, event):
        super().showEvent(event)
        self._update_cache_label()

    def _calculate_cache_size(self) -> str:
        try:
            total_size = sum(f.stat().st_size for f in THUMBNAIL_CACHE_DIR.glob('**/*') if f.is_file())
            if total_size < 1024: return f"{total_size} Bytes"
            elif total_size < 1024**2: return f"{total_size/1024:.2f} KB"
            else: return f"{total_size/1024**2:.2f} MB"
        except FileNotFoundError: return "0 Bytes"

    def _update_cache_label(self):
        self.cache_size_label.setText(self._calculate_cache_size())

    def _clear_thumbnail_cache(self):
        msg_box = QMessageBox(self); msg_box.setWindowTitle('キャッシュの削除')
        msg_box.setText("本当にすべてのサムネイルキャッシュを削除しますか？")
        msg_box.setStandardButtons(QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        msg_box.setDefaultButton(QMessageBox.StandardButton.No)
        msg_box.button(QMessageBox.StandardButton.Yes).setText('はい'); msg_box.button(QMessageBox.StandardButton.No).setText('いいえ')
        if msg_box.exec() == QMessageBox.StandardButton.No: return
        count = 0
        try:
            for f in THUMBNAIL_CACHE_DIR.glob('**/*'):
                if f.is_file(): f.unlink(); count += 1
            QMessageBox.information(self, "完了", f"サムネイルキャッシュ {count}項目を削除しました。")
        except Exception as e:
            QMessageBox.critical(self, "エラー", f"キャッシュの削除中にエラーが発生しました。:\n{e}")
        finally:
            self._update_cache_label()

    def _create_general_tab(self):
        tab = QWidget(); layout = QVBoxLayout(tab); layout.setSpacing(15)
        folder_group = QWidget(); folder_layout = QVBoxLayout(folder_group); folder_layout.setContentsMargins(0,0,0,0)
        folder_layout.addWidget(QLabel("ダウンロードフォルダ:"))
        row = QHBoxLayout()
        self.folder_path_edit = QLineEdit(self.config.get("download_folder", "")); self.folder_path_edit.setReadOnly(True)
        self.folder_path_edit.setObjectName("PathDisplayEdit")
        row.addWidget(self.folder_path_edit, 1)
        browse = QPushButton("検索..."); browse.clicked.connect(self._browse_folder); row.addWidget(browse)
        folder_layout.addLayout(row); layout.addWidget(folder_group)
        dl_count_group = QWidget(); dl_count_layout = QHBoxLayout(dl_count_group); dl_count_layout.setContentsMargins(0,0,0,0)
        dl_count_layout.addWidget(QLabel("最大同時ダウンロード数:"))
        self.concurrent_spinbox = QSpinBox()
        self.concurrent_spinbox.setRange(1, PARALLEL_MAX) # 修正: PARALLEL_MAX を適用
        self.concurrent_spinbox.setValue(self.config.get("max_concurrent_downloads", 5))
        dl_count_layout.addWidget(self.concurrent_spinbox); dl_count_layout.addStretch(1); layout.addWidget(dl_count_group)
        theme_group = QWidget(); theme_layout = QVBoxLayout(theme_group); theme_layout.setContentsMargins(0,0,0,0)
        theme_layout.addWidget(QLabel("テーマ:"))
        self.theme_button_group = QButtonGroup(self)
        theme_radio_layout = QHBoxLayout()
        themes = {"ライト（デフォルト）": "light", "ダーク": "dark"}
        current_theme = self.config.get("theme", "light")
        for text, key in themes.items():
            radio = QRadioButton(text); radio.setProperty("config_value", key)
            self.theme_button_group.addButton(radio); theme_radio_layout.addWidget(radio)
            if key == current_theme: radio.setChecked(True)
        theme_radio_layout.addStretch(1); theme_layout.addLayout(theme_radio_layout); layout.addWidget(theme_group)
        layout.addStretch(1); self.tabs.addTab(tab, "一般")

    def _create_filename_tab(self):
        tab = QWidget(); layout = QVBoxLayout(tab)
        layout.addWidget(QLabel("ファイル名の構成要素の選択と順序の設定:"))
        list_row = QHBoxLayout()
        self.order_list = QListWidget(); self.order_list.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.order_list.setDragDropMode(QAbstractItemView.DragDropMode.NoDragDrop)
        fm = self.order_list.fontMetrics(); row_h = max(28, fm.height() + 12)
        self.order_list.setStyleSheet("QListWidget::item{ padding:6px 8px; }")
        btn_col = QVBoxLayout()
        self.up_btn = QToolButton(toolTip="上へ", shortcut="Alt+Up"); self.down_btn = QToolButton(toolTip="下へ", shortcut="Alt+Down")
        self.up_btn.setFixedSize(32, 32); self.down_btn.setFixedSize(32, 32)
        self.up_btn.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_ArrowUp))
        self.down_btn.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_ArrowDown))
        btn_col.addWidget(self.up_btn); btn_col.addWidget(self.down_btn); btn_col.addStretch(1)
        list_row.addWidget(self.order_list, 1); list_row.addLayout(btn_col); layout.addLayout(list_row, 1)
        self.part_names: dict[str, str] = {"series": "シリーズ名", "upload_date": "放送日", "episode_number": "話数", "episode": "タイトル", "id": "固有ID"}
        parts_cfg: dict = self.config.get("filename_parts", {})
        current_order = self.config.get("filename_order", list(self.part_names.keys()))
        for key in current_order:
            if key not in self.part_names: continue
            item = QListWidgetItem(self.part_names[key]); item.setData(ROLE_KEY, key)
            item.setFlags(item.flags() | Qt.ItemFlag.ItemIsUserCheckable); item.setCheckState(Qt.CheckState.Checked if parts_cfg.get(key, True) else Qt.CheckState.Unchecked)
            item.setSizeHint(QSize(0, row_h)); self.order_list.addItem(item)
        pv = QHBoxLayout(); pv.addWidget(QLabel("ファイル名プレビュー:")); self.preview_label = QLabel(); pv.addWidget(self.preview_label, 1); layout.addLayout(pv)
        self.order_list.itemChanged.connect(self._update_preview)
        self.order_list.currentRowChanged.connect(self._sync_move_buttons)
        self.up_btn.clicked.connect(lambda: self._move_selected(-1)); self.down_btn.clicked.connect(lambda: self._move_selected(+1))
        self._update_preview(); self._sync_move_buttons(); self.tabs.addTab(tab, "ファイル名")

    def _move_selected(self, delta: int):
        row = self.order_list.currentRow(); new_row = row + delta
        if row < 0 or new_row < 0 or new_row >= self.order_list.count(): return
        item = self.order_list.takeItem(row); self.order_list.insertItem(new_row, item)
        self.order_list.setCurrentRow(new_row); self.order_list.scrollToItem(item)
        self._update_preview(); self._sync_move_buttons()

    def _sync_move_buttons(self, *_):
        row = self.order_list.currentRow(); cnt = self.order_list.count()
        self.up_btn.setEnabled(cnt > 1 and row > 0); self.down_btn.setEnabled(cnt > 1 and 0 <= row < cnt - 1)

    def _update_preview(self, *args):
        parts = [it.text() for i in range(self.order_list.count()) if (it := self.order_list.item(i)).checkState() == Qt.CheckState.Checked]
        self.preview_label.setText(" ".join(parts) + ".mp4")

    def _create_quality_tab(self):
        tab = QWidget(); layout = QVBoxLayout(tab); layout.setSpacing(15)
        
        q_groupbox = QWidget(); q_layout = QVBoxLayout(q_groupbox); q_layout.setContentsMargins(0,0,0,0)
        q_layout.addWidget(QLabel("ダウンロード画質の選択:"))
        q_radio_layout = QVBoxLayout(); q_radio_layout.setSpacing(10); self.quality_button_group = QButtonGroup(self)
        qualities = {"最高画質（デフォルト）": "bv*+ba/b", "1080p": "bestvideo[height<=1080]+bestaudio/best[height<=1080]", "720p": "bestvideo[height<=720]+bestaudio/best[height<=720]"}
        current_quality = self.config.get("quality", "bv*+ba/b")
        for text, key in qualities.items():
            radio = QRadioButton(text); radio.setProperty("config_value", key); self.quality_button_group.addButton(radio); q_radio_layout.addWidget(radio)
            if key == current_quality: radio.setChecked(True)
        q_layout.addLayout(q_radio_layout); layout.addWidget(q_groupbox)

        c_groupbox = QWidget(); c_layout = QVBoxLayout(c_groupbox); c_layout.setContentsMargins(0,0,0,0)
        c_layout.addWidget(QLabel("優先コーデック (再エンコード):"))
        c_radio_layout = QVBoxLayout(); c_radio_layout.setSpacing(10); self.codec_button_group = QButtonGroup(self)
        codecs = {"AVC/H.264（最大互換性）": "avc", "HEVC/H.265（高効率）": "hevc", "VP9（Web標準）": "vp9", "AV1（次世代）": "av1"}
        current_codec = self.config.get("preferred_codec", "avc")
        for text, key in codecs.items():
            radio = QRadioButton(text); radio.setProperty("config_value", key); self.codec_button_group.addButton(radio); c_radio_layout.addWidget(radio)
            if key == current_codec: radio.setChecked(True)
        c_layout.addLayout(c_radio_layout); layout.addWidget(c_groupbox)

        hw_groupbox = QWidget()
        hw_v_layout = QVBoxLayout(hw_groupbox)
        hw_v_layout.setContentsMargins(0,0,0,0)
        hw_v_layout.addWidget(QLabel("コーデック変換の高速化 (GPUエンコード):"))
        self.hw_encoder_combo = QComboBox()
        self.hw_encoder_map = {
            "CPU（デフォルト、互換性）": "cpu",
            "NVIDIA (NVENC)": "nvidia",
            "Intel (QSV)": "intel",
            "AMD (AMF)": "amd"
        }
        current_hw = self.config.get("hardware_encoder", "cpu")
        for text, key in self.hw_encoder_map.items():
            self.hw_encoder_combo.addItem(text, userData=key)
            if key == current_hw:
                self.hw_encoder_combo.setCurrentText(text)
        hw_v_layout.addWidget(self.hw_encoder_combo)
        layout.addWidget(hw_groupbox)

        quality_group = QWidget()
        quality_layout = QFormLayout(quality_group)
        quality_layout.setContentsMargins(0, 5, 0, 5)
        quality_layout.setSpacing(10)
        quality_layout.addRow(QLabel("詳細品質設定（数値が低いほど高画質）"))
        
        self.q_cpu_h264_crf = QSpinBox()
        self.q_cpu_h264_crf.setRange(0, 51)
        self.q_cpu_h264_crf.setValue(self.config.get("quality_cpu_h264_crf", 26)) 
        quality_layout.addRow("CPU H.264 CRF (推奨: 26):", self.q_cpu_h264_crf)
        
        self.q_cpu_h265_crf = QSpinBox()
        self.q_cpu_h265_crf.setRange(0, 51)
        self.q_cpu_h265_crf.setValue(self.config.get("quality_cpu_h265_crf", 31)) 
        quality_layout.addRow("CPU H.265 CRF (推奨: 31):", self.q_cpu_h265_crf)
        
        self.q_cpu_vp9_crf = QSpinBox()
        self.q_cpu_vp9_crf.setRange(0, 63)
        self.q_cpu_vp9_crf.setValue(self.config.get("quality_cpu_vp9_crf", 36)) 
        quality_layout.addRow("CPU VP9 CRF (推奨: 36):", self.q_cpu_vp9_crf)
        
        self.q_cpu_av1_crf = QSpinBox()
        self.q_cpu_av1_crf.setRange(0, 63)
        self.q_cpu_av1_crf.setValue(self.config.get("quality_cpu_av1_crf", 41)) 
        quality_layout.addRow("CPU AV1 CRF (推奨: 41):", self.q_cpu_av1_crf)
        
        self.q_gpu_cq = QSpinBox()
        self.q_gpu_cq.setRange(0, 51)
        self.q_gpu_cq.setValue(self.config.get("quality_gpu_cq", 30)) 
        quality_layout.addRow("GPU CQ/CQP (推奨: 30):", self.q_gpu_cq)
        
        layout.addWidget(quality_group)
        layout.addStretch(1); self.tabs.addTab(tab, "画質")

    def _create_subtitle_tab(self):
        tab = QWidget(); layout = QVBoxLayout(tab); layout.setSpacing(15)

        self.download_subs_checkbox = QCheckBox("字幕ダウンロードを有効にする")
        self.download_subs_checkbox.setChecked(self.config.get("download_subtitles", True))
        layout.addWidget(self.download_subs_checkbox)

        line = QFrame()
        line.setFrameShape(QFrame.Shape.HLine)
        line.setFrameShadow(QFrame.Shadow.Sunken)
        layout.addWidget(line)

        self.embed_subs_checkbox = QCheckBox("字幕を動画ファイルに埋め込む (Embed)")
        self.embed_subs_checkbox.setChecked(self.config.get("embed_subtitles", True))
        layout.addWidget(self.embed_subs_checkbox)

        self.sub_fmt_groupbox = QGroupBox("別ファイル保存時の形式")
        sub_fmt_layout = QVBoxLayout(self.sub_fmt_groupbox)
        sub_fmt_layout.setSpacing(10)
        
        self.subtitle_format_button_group = QButtonGroup(self)
        self.sub_format_vtt = QRadioButton("VTT (元のまま)")
        self.sub_format_vtt.setProperty("config_value", "vtt")
        self.sub_format_srt = QRadioButton("SRT (変換、互換性重視)")
        self.sub_format_srt.setProperty("config_value", "srt")
        
        self.subtitle_format_button_group.addButton(self.sub_format_vtt)
        self.subtitle_format_button_group.addButton(self.sub_format_srt)
        
        sub_fmt_layout.addWidget(self.sub_format_vtt)
        sub_fmt_layout.addWidget(self.sub_format_srt)
        
        current_sub_format = self.config.get("subtitle_format", "vtt")
        if current_sub_format == "srt":
            self.sub_format_srt.setChecked(True)
        else:
            self.sub_format_vtt.setChecked(True)
            
        layout.addWidget(self.sub_fmt_groupbox)

        def update_ui_state():
            is_download_enabled = self.download_subs_checkbox.isChecked()
            is_embed_enabled = self.embed_subs_checkbox.isChecked()
            self.embed_subs_checkbox.setEnabled(is_download_enabled)
            self.sub_fmt_groupbox.setEnabled(is_download_enabled and not is_embed_enabled)

        self.download_subs_checkbox.toggled.connect(update_ui_state)
        self.embed_subs_checkbox.toggled.connect(update_ui_state)
        update_ui_state()
        layout.addStretch(1)
        self.tabs.addTab(tab, "字幕")

    def _create_post_action_tab(self):
        tab = QWidget(); layout = QVBoxLayout(tab); layout.addWidget(QLabel("すべてのダウンロード完了後の動作:"))
        radio_layout = QVBoxLayout(); radio_layout.setSpacing(10); self.post_action_button_group = QButtonGroup(self)
        actions = {"何もしない": "None", "ダウンロードフォルダを開く": "Open Folder", "1分後にシャットダウン": "Shutdown"}
        current_action = self.config.get("post_action", "None")
        for text, key in actions.items():
            radio = QRadioButton(text); radio.setProperty("config_value", key); self.post_action_button_group.addButton(radio); radio_layout.addWidget(radio)
            if key == current_action: radio.setChecked(True)
        layout.addLayout(radio_layout); layout.addStretch(1); self.tabs.addTab(tab, "ダウンロード後の動作")

    def _create_advanced_tab(self):
        tab = QWidget(); layout = QVBoxLayout(tab); layout.setSpacing(20)
        
        bw_groupbox = QWidget(); bw_v_layout = QVBoxLayout(bw_groupbox); bw_v_layout.setContentsMargins(0,0,0,0)
        bw_v_layout.addWidget(QLabel("帯域幅制限:"))
        self.bw_limit_button_group = QButtonGroup(self); bw_radio_layout = QVBoxLayout(); bw_radio_layout.setSpacing(10)
        limits = {"制限なし": "0", "1 MB/s": "1M", "5 MB/s": "5M", "10 MB/s": "10M", "50 MB/s": "50M"}
        current_limit = self.config.get("bandwidth_limit", "0")
        for text, key in limits.items():
            radio = QRadioButton(text); radio.setProperty("config_value", key); self.bw_limit_button_group.addButton(radio); bw_radio_layout.addWidget(radio)
            if key == current_limit: radio.setChecked(True)
        bw_v_layout.addLayout(bw_radio_layout); layout.addWidget(bw_groupbox)
        
        conv_groupbox = QWidget(); conv_v_layout = QVBoxLayout(conv_groupbox); conv_v_layout.setContentsMargins(0,0,0,0)
        conv_v_layout.addWidget(QLabel("ダウンロード後の変換 (コンテナ):"))
        self.conversion_button_group = QButtonGroup(self); conv_radio_layout = QVBoxLayout(); conv_radio_layout.setSpacing(10)
        formats = {"変換しない (MP4)": "none", "AVIに変換": "avi", "MOVに変換": "mov", "音声のみ抽出 (MP3)": "mp3"}
        current_format = self.config.get("conversion_format", "none")
        for text, key in formats.items():
            radio = QRadioButton(text); radio.setProperty("config_value", key); self.conversion_button_group.addButton(radio); conv_radio_layout.addWidget(radio)
            if key == current_format: radio.setChecked(True)
        conv_v_layout.addLayout(conv_radio_layout)
        self.delete_original_checkbox = QCheckBox("変換後に元ファイルを削除")
        self.delete_original_checkbox.setChecked(self.config.get("delete_on_conversion", False))
        self.conversion_button_group.buttonToggled.connect(self._toggle_delete_checkbox)
        self._toggle_delete_checkbox()
        conv_v_layout.addWidget(self.delete_original_checkbox); layout.addWidget(conv_groupbox)

        exclude_groupbox = QWidget()
        exclude_v_layout = QVBoxLayout(exclude_groupbox)
        exclude_v_layout.setContentsMargins(0,0,0,0)
        exclude_v_layout.addWidget(QLabel("シリーズ分析時に除外するキーワード（カンマで区切る）:"))
        current_keywords = self.config.get("series_exclude_keywords", [])
        self.exclude_keywords_edit = QLineEdit(", ".join(current_keywords))
        self.exclude_keywords_edit.setPlaceholderText("例: 予告, SP, ダイジェスト")
        exclude_v_layout.addWidget(self.exclude_keywords_edit)
        layout.addWidget(exclude_groupbox)

        layout.addStretch(1); self.tabs.addTab(tab, "詳細")

    def _create_cache_tab(self):
        tab = QWidget(); layout = QVBoxLayout(tab); layout.setSpacing(15)
        info_layout = QHBoxLayout()
        info_layout.addWidget(QLabel("現在のサムネイルキャッシュサイズ:"))
        self.cache_size_label = QLabel("計算中..."); self.cache_size_label.setObjectName("PaneSubtitle")
        info_layout.addWidget(self.cache_size_label); info_layout.addStretch(1)
        layout.addLayout(info_layout)
        self.clear_cache_button = QPushButton("サムネイルキャッシュを削除"); self.clear_cache_button.setObjectName("DangerButton")
        self.clear_cache_button.clicked.connect(self._clear_thumbnail_cache)
        layout.addWidget(self.clear_cache_button)
        layout.addStretch(1); self.tabs.addTab(tab, "キャッシュ")

    def _toggle_delete_checkbox(self):
        selected_button = self.conversion_button_group.checkedButton()
        is_conversion_selected = selected_button is not None and selected_button.property("config_value") != "none"
        self.delete_original_checkbox.setEnabled(is_conversion_selected)

    def _browse_folder(self):
        folder = QFileDialog.getExistingDirectory(self, "ダウンロードフォルダを選択", self.folder_path_edit.text())
        if folder: self.folder_path_edit.setText(folder)

    def _save_settings(self):
        self.config["download_folder"] = self.folder_path_edit.text()
        self.config["max_concurrent_downloads"] = self.concurrent_spinbox.value()
        if self.theme_button_group.checkedButton(): self.config["theme"] = self.theme_button_group.checkedButton().property("config_value")
        
        filename_parts: dict[str, bool] = {}; filename_order: list[str] = []
        for i in range(self.order_list.count()):
            it = self.order_list.item(i); key = it.data(ROLE_KEY)
            filename_order.append(key); filename_parts[key] = (it.checkState() == Qt.CheckState.Checked)
        self.config["filename_parts"] = filename_parts; self.config["filename_order"] = filename_order
        
        if self.quality_button_group.checkedButton(): self.config["quality"] = self.quality_button_group.checkedButton().property("config_value")
        if self.codec_button_group.checkedButton(): self.config["preferred_codec"] = self.codec_button_group.checkedButton().property("config_value")
        self.config["hardware_encoder"] = self.hw_encoder_combo.currentData()
        self.config["quality_cpu_h264_crf"] = self.q_cpu_h264_crf.value()
        self.config["quality_cpu_h265_crf"] = self.q_cpu_h265_crf.value()
        self.config["quality_cpu_vp9_crf"] = self.q_cpu_vp9_crf.value()
        self.config["quality_cpu_av1_crf"] = self.q_cpu_av1_crf.value()
        self.config["quality_gpu_cq"] = self.q_gpu_cq.value()

        self.config["download_subtitles"] = self.download_subs_checkbox.isChecked()
        self.config["embed_subtitles"] = self.embed_subs_checkbox.isChecked()
        if self.subtitle_format_button_group.checkedButton():
            self.config["subtitle_format"] = self.subtitle_format_button_group.checkedButton().property("config_value")

        if self.post_action_button_group.checkedButton(): self.config["post_action"] = self.post_action_button_group.checkedButton().property("config_value")
        
        if self.bw_limit_button_group.checkedButton(): self.config["bandwidth_limit"] = self.bw_limit_button_group.checkedButton().property("config_value")
        if self.conversion_button_group.checkedButton(): self.config["conversion_format"] = self.conversion_button_group.checkedButton().property("config_value")
        self.config["delete_on_conversion"] = self.delete_original_checkbox.isChecked()
        keywords_str = self.exclude_keywords_edit.text()
        self.config["series_exclude_keywords"] = [k.strip() for k in keywords_str.split(',') if k.strip()]
        
        save_config(self.config)
        self.accept()