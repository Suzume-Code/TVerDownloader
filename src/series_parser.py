# src/series_parser.py
# 修正:
# - finishedシグナルにseries_titleを追加
# - _on_parse_finishedでseries_titleを受け取りfinishedシグナルに渡す

from typing import List, Dict, Optional, Tuple
from PyQt6.QtCore import QObject, pyqtSignal

from src.threads.series_parse_thread import SeriesParseThread

class SeriesParser(QObject):
    log = pyqtSignal(str, str) 
    # ✅ finishedシグナルの変更: (コンテキスト, シリーズURL, シリーズタイトル, エピソードリスト)
    finished = pyqtSignal(str, str, str, list)

    def __init__(self, ytdlp_path: str, config: Dict, parent=None):
        super().__init__(parent)
        self.ytdlp_path = ytdlp_path
        self.config = config
        self._queue: List[Tuple[str, str]] = []
        self._thread: Optional[SeriesParseThread] = None
        self._current_context: str = ""
        self._current_url: str = ""

    def set_ytdlp_path(self, path: str):
        self.ytdlp_path = path

    def update_config(self, config: Dict):
        self.config = config

    def parse(self, context: str, urls: List[str]):
        if not self.ytdlp_path:
            self.log.emit(context, "[エラー] yt-dlp パスが設定されていないため、シリーズを解析できません。")
            return
        initial_count = len(self._queue)
        for url in urls:
            self._queue.append((context, url))
        if initial_count == 0 and self._queue:
            self._run_next()

    def _run_next(self):
        if self._thread is not None or not self._queue:
            return
        self._current_context, self._current_url = self._queue.pop(0)
        exclude_keywords = self.config.get("series_exclude_keywords", [])
        self._thread = SeriesParseThread(self._current_url, self.ytdlp_path, exclude_keywords)
        self._thread.log.connect(lambda msg: self.log.emit(self._current_context, msg))
        # ✅ _on_parse_finishedシグナル接続 (引数の数を調整)
        self._thread.finished.connect(self._on_parse_finished)
        self._thread.start()

    # ✅ _on_parse_finishedシグナル: (シリーズタイトル, エピソードURLリスト)
    def _on_parse_finished(self, series_title: str, episode_urls: List[str]):
        """スレッド完了時の結果をfinishedシグナルに送信し、次の処理を開始します。"""
        # ✅ シリーズタイトルを含めてemit
        self.finished.emit(self._current_context, self._current_url, series_title, episode_urls or [])
        
        if self._thread:
            self._thread.deleteLater()
            self._thread = None
        
        self._run_next()