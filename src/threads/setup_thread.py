# src/threads/setup_thread.py
# 修正: FFmpegの更新時にffmpeg.exeとともにffprobe.exeもbinフォルダにコピーするように修正

import os
import shutil
import zipfile
from pathlib import Path
from typing import Optional

import requests
from PyQt6.QtCore import QThread, pyqtSignal

class SetupThread(QThread):
    """yt-dlpおよびffmpegの実行ファイルパスを見つけ、準備状態を通知するスレッド。"""
    log = pyqtSignal(str)
    finished = pyqtSignal(bool, str, str)

    BIN_DIR = Path("bin")
    YTDLP_API_URL = "https://api.github.com/repos/yt-dlp/yt-dlp-nightly-builds/releases/latest"
    FFMPEG_API_URL = "https://api.github.com/repos/GyanD/codexffmpeg/releases/latest"
    FFMPEG_ASSET_KEYWORD = "essentials"
    FFMPEG_ASSET_EXTENSION = ".zip"

    def run(self):
        try:
            ytdlp_exe_path = self._update_ytdlp()
            ffmpeg_exe_path = self._update_ffmpeg()
            if ytdlp_exe_path and ffmpeg_exe_path:
                self.finished.emit(True, str(ytdlp_exe_path), str(ffmpeg_exe_path))
            else:
                self.finished.emit(False, "", "")
        except Exception as e:
            self.log.emit(f"[致命的エラー] 設定中に例外が発生しました: {e}")
            self.finished.emit(False, "", "")

    def _get_api_info(self, url: str) -> Optional[dict]:
        try:
            r = requests.get(url, timeout=10)
            r.raise_for_status()
            return r.json()
        except requests.exceptions.RequestException as e:
            self.log.emit(f"[エラー] GitHub API呼び出しに失敗しました: {e}")
            return None

    def _download_and_place(self, url: str, target_path: Path) -> bool:
        self.log.emit(f" -> ダウンロード開始: {url}")
        target_path.parent.mkdir(parents=True, exist_ok=True)
        with requests.get(url, stream=True, timeout=60) as r:
            r.raise_for_status()
            with open(target_path, "wb") as f:
                for chunk in r.iter_content(chunk_size=8192):
                    f.write(chunk)
        return True

    def _download_and_unzip(self, url: str, target_dir: Path, file_name: str) -> bool:
        target_dir.mkdir(parents=True, exist_ok=True)
        zip_path = target_dir / file_name
        self.log.emit(f" -> ダウンロード開始: {url}")
        with requests.get(url, stream=True, timeout=60) as r:
            r.raise_for_status()
            with open(zip_path, "wb") as f:
                for chunk in r.iter_content(chunk_size=8192):
                    f.write(chunk)
        self.log.emit(f" -> 解凍中: {zip_path}")
        with zipfile.ZipFile(zip_path, "r") as zf:
            zf.extractall(target_dir)
        try:
            os.remove(zip_path)
        except Exception:
            pass
        return True

    def _update_ytdlp(self) -> Optional[Path]:
        self.log.emit("[1] yt-dlp.exe 最新バージョンを確認しています...")
        ytdlp_exe_path = self.BIN_DIR / "yt-dlp.exe"
        version_file = self.BIN_DIR / "ytdlp_version.txt"

        info = self._get_api_info(self.YTDLP_API_URL)
        if not info:
            return ytdlp_exe_path if ytdlp_exe_path.exists() else None

        latest = info.get("tag_name")
        current = version_file.read_text().strip() if version_file.exists() else None

        if latest == current and ytdlp_exe_path.exists():
            self.log.emit(f" ... yt-dlpはすでに最新バージョンです ({latest}).")
            return ytdlp_exe_path

        asset = next((a for a in info.get("assets", []) if isinstance(a, dict)
                      and a.get("name", "").endswith(".exe")
                      and "yt-dlp" in a.get("name", "").lower()), None)
        if not asset:
            self.log.emit("[エラー] yt-dlp.exeアセットが見つかりません。")
            return ytdlp_exe_path if ytdlp_exe_path.exists() else None

        if self._download_and_place(asset["browser_download_url"], ytdlp_exe_path):
            version_file.write_text(latest or "")
            self.log.emit(" ... yt-dlp.exeの更新が完了しました。")
        return ytdlp_exe_path

    def _update_ffmpeg(self) -> Optional[Path]:
        self.log.emit("[2] FFmpeg 最新バージョンを確認しています...")
        ffmpeg_exe_path = self.BIN_DIR / "ffmpeg.exe"
        ffprobe_exe_path = self.BIN_DIR / "ffprobe.exe" # ffprobeパス定義
        version_file = self.BIN_DIR / "ffmpeg_version.txt"

        info = self._get_api_info(self.FFMPEG_API_URL)
        if not info:
            return ffmpeg_exe_path if ffmpeg_exe_path.exists() and ffprobe_exe_path.exists() else None

        latest = info.get("tag_name")
        current = version_file.read_text().strip() if version_file.exists() else None

        if latest == current and ffmpeg_exe_path.exists() and ffprobe_exe_path.exists():
            self.log.emit(f" ... FFmpegはすでに最新バージョンです ({latest}).")
            return ffmpeg_exe_path

        asset = next(
            (a for a in info.get("assets", []) if isinstance(a, dict)
             and self.FFMPEG_ASSET_KEYWORD in a.get("name", "").lower()
             and a.get("name", "").endswith(self.FFMPEG_ASSET_EXTENSION)),
            None,
        )
        if not asset:
            self.log.emit("[エラー] FFmpeg .zipアセットが見つかりません。")
            return ffmpeg_exe_path if ffmpeg_exe_path.exists() else None

        temp_dir = self.BIN_DIR / "ffmpeg_temp"
        if temp_dir.exists():
            shutil.rmtree(temp_dir)

        if not self._download_and_unzip(asset["browser_download_url"], temp_dir, asset["name"]):
            return ffmpeg_exe_path if ffmpeg_exe_path.exists() else None

        extracted_root = next((p for p in temp_dir.iterdir() if p.is_dir()), None)
        
        # --- [修正済み部分 開始] ---
        if not extracted_root:
            self.log.emit("[エラー] FFmpeg解凍後にフォルダが見つかりません。")
            return ffmpeg_exe_path if ffmpeg_exe_path.exists() else None
            
        source_ffmpeg = extracted_root / "bin" / "ffmpeg.exe"
        source_ffprobe = extracted_root / "bin" / "ffprobe.exe"

        if source_ffmpeg.exists() and source_ffprobe.exists():
            self.BIN_DIR.mkdir(parents=True, exist_ok=True)
            
            # 既存ファイルを削除
            if ffmpeg_exe_path.exists(): ffmpeg_exe_path.unlink()
            if ffprobe_exe_path.exists(): ffprobe_exe_path.unlink()

            # 新しいファイルを移動
            shutil.move(str(source_ffmpeg), str(ffmpeg_exe_path))
            shutil.move(str(source_ffprobe), str(ffprobe_exe_path))

            self.log.emit(f" -> {ffmpeg_exe_path.name} および {ffprobe_exe_path.name} の移動が完了しました。")
            try:
                shutil.rmtree(temp_dir)
            except Exception:
                pass
            version_file.write_text(latest or "")
            self.log.emit(" ... FFmpegの更新が完了しました。")
            return ffmpeg_exe_path
        # --- [修正済み部分 終了] ---
        else:
            self.log.emit("[エラー] 解凍されたファイルから ffmpeg.exe または ffprobe.exe が見つかりません。")
            try:
                shutil.rmtree(temp_dir)
            except Exception:
                pass
            return ffmpeg_exe_path if ffmpeg_exe_path.exists() else None