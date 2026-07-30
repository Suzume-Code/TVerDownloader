# src/threads/series_parse_thread.py
# 修正:
# - runメソッドでシリーズタイトル解析時に'playlist_title'キーを優先して確認するように変更

import subprocess
import json
from typing import List, Dict

from PyQt6.QtCore import QThread, pyqtSignal

from src.utils import get_startupinfo

class SeriesParseThread(QThread):
    """シリーズURLを受け取り、サブエピソード情報（辞書）のリストを返すスレッド。"""
    log = pyqtSignal(str)
    finished = pyqtSignal(str, list) # (シリーズタイトル, エピソード情報リスト)

    def __init__(self, series_url: str, ytdlp_exe_path: str, exclude_keywords: List[str], parent=None):
        super().__init__(parent)
        self.series_url = series_url
        self.ytdlp_exe_path = ytdlp_exe_path
        self.exclude_keywords = [k.lower() for k in exclude_keywords if k.strip()]

    def _is_excluded(self, title: str) -> bool:
        if not self.exclude_keywords:
            return False
        title_lower = title.lower()
        for keyword in self.exclude_keywords:
            if keyword in title_lower:
                return True
        return False

    def _parse_entries(self, entries: list) -> List[Dict[str, str]]:
        results: List[Dict[str, str]] = []
        for meta in entries:
            if not isinstance(meta, dict): continue
            url = meta.get("webpage_url") or meta.get("url")
            title = meta.get("title", "(タイトルなし)")
            thumbnail_url = meta.get("thumbnail")
            if url and title and not self._is_excluded(title):
                results.append({
                    "url": url.strip(),
                    "title": title.strip(),
                    "thumbnail_url": thumbnail_url or ""
                })
        return results

    def _parse_json_output(self, out: str) -> List[Dict[str, str]]:
        try:
            data = json.loads(out)
            if isinstance(data, dict) and "entries" in data:
                return self._parse_entries(data.get("entries") or [])
            else:
                return self._parse_entries([data])
        except json.JSONDecodeError:
            entries = []
            for line in (out or "").splitlines():
                try:
                    entries.append(json.loads(line))
                except (json.JSONDecodeError, KeyError): continue
            return self._parse_entries(entries)

    def _parse_flat_output(self, out: str) -> List[Dict[str, str]]:
        results: List[Dict[str, str]] = []
        lines = [l for l in (out or "").splitlines() if "\t" in l]
        for line in lines:
            try:
                url, title = line.split("\t", 1)
                if not self._is_excluded(title or ""):
                    results.append({"url": url.strip(), "title": title.strip(), "thumbnail_url": ""})
            except ValueError: continue
        return results

    def run(self):
        try:
            self.log.emit(f"[シリーズ] 解析中 (1/2): {self.series_url}")
            command1 = [self.ytdlp_exe_path, "-J", "--skip-download", "--no-warnings", self.series_url]
            startupinfo = get_startupinfo()
            proc1 = subprocess.Popen(
                command1, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                startupinfo=startupinfo, text=True, encoding="utf-8", errors="ignore"
            )
            out1, err1 = proc1.communicate()

            series_title = ""
            episodes = []

            if proc1.returncode == 0:
                # --- [修正済み部分 開始] ---
                try:
                    data = json.loads(out1)
                    # ✅ 'playlist_title'を先に確認し、なければ'title'を確認
                    series_title = data.get("playlist_title") or data.get("title", "")
                except json.JSONDecodeError:
                    pass
                # --- [修正済み部分 終了] ---
                episodes = self._parse_json_output(out1)
            else:
                self.log.emit(f"[エラー] シリーズ1次解析失敗:\n{(err1 or '').strip()}");
                self.finished.emit("", []); return

            if not episodes:
                self.log.emit("[シリーズ] 1次解析結果なし。2次解析を試行中...")
                command2 = [self.ytdlp_exe_path, "--flat-playlist", "--print", "%(url)s\t%(title)s", "--skip-download", "--no-warnings", self.series_url]
                proc2 = subprocess.Popen(
                    command2, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                    startupinfo=startupinfo, text=True, encoding="utf-8", errors="ignore"
                )
                out2, err2 = proc2.communicate()

                if proc2.returncode != 0:
                    self.log.emit(f"[エラー] シリーズ2次解析失敗:\n{(err2 or '').strip()}");
                    self.finished.emit(series_title, []); return
                
                episodes = self._parse_flat_output(out2)
                if not episodes and err2: self.log.emit(f"[診断] 2次解析結果なし。エラーストリーム: {(err2 or 'なし').strip()}")

            self.log.emit(f"最終 {len(episodes)} 件のエピソード情報抽出完了。")
            self.finished.emit(series_title, episodes)
        except Exception as e:
            self.log.emit(f"[오류] 시리즈 분석 중 예외: {e}");
            self.finished.emit("", [])