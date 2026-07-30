# -*- coding: utf-8 -*-
# ファイル名: src/bulk_dialog.py
# 目的: 複数のURLを一度に入力して返す
# 特徴:
#  - get_urls(): 行単位でURLを解析しリストを返す
#  - 空白/重複を除去
#  - シリーズ/通常URLの区別は呼び出し元(TVerDownloader.open_bulk_add)で処理

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel,
    QTextEdit, QPushButton
)
from PyQt6.QtCore import Qt


class BulkAddDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("一括ダウンロード")
        self.resize(600, 420)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(10)

        self.desc = QLabel(
            "各行に1つのURLを入力してください。\n"
            "- 通常のエピソードのURLはそのまま追加されます。\n"
            "- シリーズのURLはエピソードごとに拡張され、複数の項目として追加されます。"
        )
        self.desc.setWordWrap(True)
        layout.addWidget(self.desc)

        self.text = QTextEdit(self)
        self.text.setPlaceholderText("例:\nhttps://tver.jp/episodes/...\nhttps://tver.jp/series/...")
        layout.addWidget(self.text, 1)

        btns = QHBoxLayout()
        btns.setSpacing(8)
        btns.addStretch(1)
        self.ok_btn = QPushButton("追加")
        self.cancel_btn = QPushButton("キャンセル")
        self.ok_btn.clicked.connect(self.accept)
        self.cancel_btn.clicked.connect(self.reject)
        btns.addWidget(self.ok_btn)
        btns.addWidget(self.cancel_btn)
        layout.addLayout(btns)

    def get_urls(self) -> list[str]:
        raw = self.text.toPlainText() or ""
        lines = [l.strip() for l in raw.splitlines()]
        out = []
        seen = set()
        for s in lines:
            if not s:
                continue
            if s in seen:
                continue
            seen.add(s)
            out.append(s)
        return out
