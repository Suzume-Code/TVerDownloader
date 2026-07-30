# src/threads/download_thread.py

import os, re, json, time, signal, subprocess
from pathlib import Path
from typing import List, Optional, Dict, Any
from PyQt6.QtCore import QThread, pyqtSignal
from src.utils import get_startupinfo, FILENAME_TITLE_MAX_LENGTH

class DownloadThread(QThread):
    progress = pyqtSignal(str, dict)
    finished = pyqtSignal(str, bool, str, dict)

    def __init__(self, url: str, download_folder: str, ytdlp_exe_path: str, ffmpeg_exe_path: str,
                 output_template: str, quality_format: str, bandwidth_limit: str, 
                 download_subtitles: bool, embed_subtitles: bool, subtitle_format: str,
                 parent=None):
        super().__init__(parent)
        self.url = url; self.download_folder = download_folder
        self.ytdlp_exe_path = ytdlp_exe_path
        
        self.ffmpeg_path_dir = os.path.dirname(ffmpeg_exe_path)
        self.ffmpeg_full_exe_path = ffmpeg_exe_path 

        self.output_template = output_template; self.quality_format = quality_format
        self.bandwidth_limit = bandwidth_limit
        
        self.download_subtitles = download_subtitles
        self.embed_subtitles = embed_subtitles
        self.subtitle_format = subtitle_format
        
        self.process: Optional[subprocess.Popen] = None
        self._stop_flag = False; self._current_component: str = "動画"; self._final_filepath: str = ""
        self._metadata: Dict = {}

    def stop(self):
        if self._stop_flag: return
        self._stop_flag = True
        try: self.progress.emit(self.url, {"status": "キャンセル中...", "log": "ユーザーによる中断要求"})
        except RuntimeError: pass
        self._kill_process_tree()

    def _kill_process_tree(self):
        p = self.process
        if not p or p.poll() is not None: return
        try:
            if os.name == "nt": p.send_signal(signal.CTRL_BREAK_EVENT); p.wait(timeout=2)
            else: os.killpg(os.getpgid(p.pid), signal.SIGTERM); p.wait(timeout=2)
        except (ProcessLookupError, subprocess.TimeoutExpired, OSError): pass
        if p.poll() is None:
            try:
                if os.name == "nt":
                    flags = subprocess.CREATE_NO_WINDOW
                    subprocess.run(["taskkill", "/PID", str(p.pid), "/T", "/F"], check=False, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, creationflags=flags)
                else: os.killpg(os.getpgid(p.pid), signal.SIGKILL)
            except (ProcessLookupError, OSError, AttributeError): pass
            finally: self.process = None

    def run(self):
        is_successful = False
        try: is_successful = self._execute_download()
        except Exception as e:
            is_successful = False
            log_msg = f"ダウンロードスレッド例外発生: {e}"
            self.progress.emit(self.url, {"status": "エラー", "log": log_msg})
        self.finished.emit(self.url, is_successful, self._final_filepath if is_successful else "", self._metadata)

    def _convert_vtt_to_srt(self, vtt_filepath: Path):
        """FFmpegを使用してVTTファイルをSRTファイルに変換し、元のVTTを削除します。"""
        if not vtt_filepath.exists():
            self.progress.emit(self.url, {"log": f"[エラー] SRT変換対象のVTTファイルが見つかりません: {vtt_filepath}"})
            return

        srt_filepath = vtt_filepath.with_suffix('.srt')
        
        if srt_filepath.exists():
            self.progress.emit(self.url, {"log": "SRTファイルは既に存在します。"})
            return

        command = [
            self.ffmpeg_full_exe_path,
            '-y',
            '-i', str(vtt_filepath),
            str(srt_filepath)
        ]
        
        try:
            proc = subprocess.run(command, capture_output=True, text=True, startupinfo=get_startupinfo(), timeout=15)
            if proc.returncode == 0:
                self.progress.emit(self.url, {"log": "字幕をSRTに変換しました。"})
                try:
                    vtt_filepath.unlink()
                except OSError as e:
                    self.progress.emit(self.url, {"log": f"[エラー] 元のVTTファイルの削除に失敗しました: {e}"})
            else:
                self.progress.emit(self.url, {"log": f"[エラー] SRT変換に失敗しました: {proc.stderr}"})
        except Exception as e:
            self.progress.emit(self.url, {"log": f"[エラー] SRT変換中に例外が発生しました: {e}"})
    def _execute_download(self) -> bool:
        self._metadata = self._get_metadata() or {}
        if not self._metadata:
            self.progress.emit(self.url, {"status": "エラー", "log": "メタデータを取得できません。"}); return False

        self.progress.emit(self.url, {"title": self._metadata.get("title", "(タイトルなし)"), "thumbnail": self._metadata.get("thumbnail")})
        self._final_filepath = self._build_final_filepath(self._metadata)
        command = self._build_command(self._final_filepath)
        popen_kwargs: Dict[str, Any] = {}
        if os.name == 'nt': popen_kwargs['creationflags'] = subprocess.CREATE_NO_WINDOW | subprocess.CREATE_NEW_PROCESS_GROUP
        else: popen_kwargs['start_new_session'] = True

        self.progress.emit(self.url, {"status": "ダウンロード中", "log": "yt-dlpプロセス開始..."})
        self.process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, encoding="utf-8", errors="ignore", **popen_kwargs)

        if self.process and self.process.stdout:
            for line in iter(self.process.stdout.readline, ""):
                if self._stop_flag: self.progress.emit(self.url, {"status": "キャンセル済み"}); return False
                self._parse_line(line)
        if self._stop_flag: return False
        rc = self.process.wait(timeout=5) if self.process else 1
        
        if not os.path.exists(self._final_filepath):
             self.progress.emit(self.url, {"log": f"[エラー] 最終ファイルが指定されたパスに存在しません: {self._final_filepath}"})

        success = (rc == 0) and os.path.exists(self._final_filepath)
        
        if success and self.download_subtitles and not self.embed_subtitles and self.subtitle_format == 'srt':
            self.progress.emit(self.url, {"status": "字幕変換中 (SRT)..."})
            vtt_path = Path(self._final_filepath).with_suffix('.ja.vtt')
            self._convert_vtt_to_srt(vtt_path)

        final_status = "完了" if success else "エラー"
        self.progress.emit(self.url, {"status": final_status, "percent": 100, "final_filepath": self._final_filepath})
        return success

    def _get_metadata(self) -> Optional[Dict[str, Any]]:
        try:
            cmd = [self.ytdlp_exe_path, "-J", "--no-warnings", self.url]
            p = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="ignore", startupinfo=get_startupinfo(), timeout=20)
            return json.loads(p.stdout) if p.returncode == 0 else None
        except Exception: return None

    def _build_final_filepath(self, metadata: Dict[str, Any]) -> str:
        template, ext = self.output_template.rsplit('.', 1)
        
        # [修正] シリーズ/タイトル重複除去ロジック強化（正規表現導入）
        series_title = (metadata.get('series') or metadata.get('playlist_title') or '').strip()
        episode_title = metadata.get('title', 'NA').strip()
        
        if series_title:
            # 1. まず厳密一致を試行
            if episode_title.startswith(series_title):
                episode_title = episode_title[len(series_title):]
            else:
                # 2. 失敗した場合は正規表現で柔軟にマッチ
                try:
                    # シリーズ名を安全なパターンに変換
                    safe_series = re.escape(series_title)
                    # シリーズ名がエピソードタイトルの先頭にあるかを確認
                    # その後に空白や特殊文字が続く可能性を許容
                    match = re.match(r'^' + safe_series, episode_title, re.IGNORECASE)
                    if match:
                         episode_title = episode_title[match.end():]
                except Exception:
                    pass

            # 3. 重複除去後、残った文字列の先頭の区切り文字（空白、コロン、ダッシュ、全角スペースなど）を削除
            # \u3000: 全角スペース（日本語テキストでよく見られる）
            episode_title = re.sub(r'^[:\-\s\u3000]+', '', episode_title).strip()
            
        def replacer(match):
            key = match.group(1)
            if key == 'title':
                return episode_title[:FILENAME_TITLE_MAX_LENGTH]
            elif key == 'series,playlist_title': return series_title
            elif key == 'upload_date>%Y-%m-%d': return (metadata.get('upload_date') or '')[:8]
            else: return str(metadata.get(key, ''))
        
        path_without_ext = re.sub(r'%\((.*?)\)s', replacer, template)
        path_without_ext = re.sub(r'\s+', ' ', path_without_ext).strip()

        # [修正] 全パス長制限および自動縮小（Windows MAX_PATH対応）
        full_dir = os.path.abspath(self.download_folder)
        filename = f"{path_without_ext}.{metadata.get('ext', ext)}"
        full_path = os.path.join(full_dir, filename)
        
        MAX_PATH_LEN = 250
        current_len = len(full_path)
        
        if current_len > MAX_PATH_LEN:
            excess = current_len - MAX_PATH_LEN
            name_part = path_without_ext
            new_len = max(10, len(name_part) - excess)
            path_without_ext = name_part[:new_len].strip()
            
            filename = f"{path_without_ext}.{metadata.get('ext', ext)}"
            full_path = os.path.join(full_dir, filename)
            self.progress.emit(self.url, {"log": f"[通知] パスが長すぎるためファイル名を縮小しました: {filename}"})
            
        return full_path

    def _build_command(self, final_filepath: str) -> List[str]:
        command: List[str] = [
            self.ytdlp_exe_path, self.url,
            "--ffmpeg-location", self.ffmpeg_path_dir,
            "-o", final_filepath,
            "--retries", "10", "--fragment-retries", "10", "--force-overwrites", "--no-keep-fragments",
            "--no-check-certificate", "--windows-filenames", "--no-cache-dir", "--abort-on-error",
            "--add-header", "Accept-Language:ja-JP", "--progress", "--encoding", "utf-8", "--newline",
            "-f", self.quality_format,
            "--merge-output-format", "mp4",
        ]
        
        if self.download_subtitles:
            command.append("--write-subs")
            command.append("--sub-langs")
            command.append("ja")
            
            if self.embed_subtitles:
                command.append("--embed-subs")
            else:
                command.append("--sub-format")
                command.append("vtt")
        else:
            command.append("--no-write-subs")

        if self.bandwidth_limit and self.bandwidth_limit != "0": command.extend(["-r", self.bandwidth_limit])
        return command

    def _parse_line(self, line: str):
        line = (line or "").strip()
        if not line: return
        payload: Dict[str, Any] = {}
        log_keywords = ["Merging formats into", "Embedding subtitles", "[error]", "ERROR:"]
        if any(keyword in line for keyword in log_keywords): payload["log"] = line
        
        m_merger = re.search(r"\[Merger\] Merging formats into \"(.+)\"", line)
        if m_merger:
            self._final_filepath = m_merger.group(1)

        if "[download] Destination:" in line:
            if not self._final_filepath:
                self._final_filepath = line.split("Destination:", 1)[1].strip()
            
            destination_path = line.split("Destination:", 1)[1].lower()
            if ".m4a" in destination_path or "audio" in destination_path: self._current_component = "音声"
            else: self._current_component = "動画"
        
        m_progress = re.search(r"\[download\]\s+([0-9.]+)% of.*?at (.*?/s)\s+ETA\s+(.*)", line)
        if m_progress:
            payload.update({"status": "ダウンロード中", "percent": float(m_progress.group(1)), "speed": m_progress.group(2),
                            "eta": m_progress.group(3), "component": self._current_component})
        
        if "Merging formats" in line: payload["status"] = "後処理中（マージ）"
        elif "Embedding subtitles" in line: payload["status"] = "後処理中（字幕）"
        
        if payload: self.progress.emit(self.url, payload)