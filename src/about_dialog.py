# src/about_dialog.py
# 修正: v2.3.1 機能に合わせて「主な機能」の説明文を更新

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QDialogButtonBox, QTextBrowser, QWidget
)
from PyQt6.QtCore import Qt
from src.icon import get_app_icon
from src.utils import open_developer_link, open_feedback_link

class AboutDialog(QDialog):
    def __init__(self, version: str, parent: QWidget | None = None):
        super().__init__(parent)
        self.setWindowTitle("情報")
        self.setWindowIcon(get_app_icon())
        self.setModal(True)
        self.setMinimumSize(640, 480)

        root = QVBoxLayout(self)
        root.setContentsMargins(16, 16, 16, 16)
        root.setSpacing(12)

        # 上部ヘッダー
        header = QHBoxLayout()
        icon_label = QLabel()
        icon_label.setPixmap(get_app_icon().pixmap(32, 32))
        title_box = QVBoxLayout()
        title = QLabel("TVerダウンローダー"); title.setObjectName("PaneTitle")
        subtitle = QLabel(f"バージョン: {version}"); subtitle.setObjectName("PaneSubtitle")
        title_box.addWidget(title); title_box.addWidget(subtitle)
        header.addWidget(icon_label); header.addLayout(title_box); header.addStretch(1)
        root.addLayout(header)

        # 本文
        self.viewer = QTextBrowser(objectName="AboutViewer")
        self.viewer.setOpenExternalLinks(True)
        self.viewer.setHtml(self._build_html())
        root.addWidget(self.viewer, 1)

        # 下部ボタン
        btn_row = QHBoxLayout()
        youtube_btn = QPushButton("制作者 YouTube"); youtube_btn.setObjectName("LinkButton"); youtube_btn.clicked.connect(open_developer_link)
        contact_btn = QPushButton("お問い合わせ"); contact_btn.setObjectName("LinkButton"); contact_btn.clicked.connect(open_feedback_link)
        btn_row.addWidget(youtube_btn); btn_row.addWidget(contact_btn); btn_row.addStretch(1)

        close_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        close_box.button(QDialogButtonBox.StandardButton.Close).setText("閉じる")
        close_box.rejected.connect(self.reject)
        btn_row.addWidget(close_box)

        root.addLayout(btn_row)

    def _build_html(self) -> str:
        # v2.3.1 基準となる主要機能リストに更新
        return """
        <html>
        <head>
            <meta charset="utf-8">
            <style>
                body { font-family: -apple-system, Segoe UI, Arial, sans-serif; font-size: 14px; }
                h3 { margin: 12px 0 6px 0; }
                ul { margin: 6px 0 12px 24px; list-style-type: disc; }
                li { margin: 6px 0; }
            </style>
        </head>
        <body>
            <p><b>Tverダウンローダー</b>は、TVerのコンテンツを合法的な範囲内で個人利用目的にダウンロードするのに役立つデスクトップアプリです。</p>
            <p>地域制限のあるサービスの性質上、日本でのVPN環境でのご利用をお勧めします。</p>

            <h3>主な機能</h3>
            <ul>
                <li>エピソード／シリーズのURL分析および一括ダウンロード</li>
                <li>ダウンロードキューおよび同時ダウンロード数の制御</li>
                <li>お気に入りシリーズの登録および新着動画の自動確認</li>
                <li>動画／音声の画質選択および字幕の自動統合</li>
                <li>ユーザー定義のファイル名形式に対応</li>
                <li>ダウンロード完了後の自動処理（フォルダのオープン、システムの終了）</li>
                <li>サムネイルのプレビュー（拡大・保存）およびダウンロード履歴の管理</li>
                <li>シングルインスタンス実行（プログラムの重複実行防止）</li>
            </ul>

            <h3>オープンソース／リファレンス</h3>
            <ul>
                <li><a href="https://github.com/yt-dlp/yt-dlp">yt-dlp</a></li>
                <li><a href="https://ffmpeg.org/">FFmpeg</a></li>
                <li><a href="https://pypi.org/project/PyQt6/">PyQt6</a></li>
                <li><a href="https://pypi.org/project/requests/">requests</a></li>
                <li><a href="https://github.com/deuxdoom/TVerDownloader">TVerDownloader (GitHub)</a></li>
            </ul>

            <p style="color:#6b7280;">* ユーザーは、コンテンツ提供者の利用規約および著作権を遵守しなければなりません。</p>
        </body>
        </html>
        """