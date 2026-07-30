# src/updater.py
# 修正: アップデート案内メッセージボックスのテキストを修正し、リリースノートプレビュー機能を削除

from __future__ import annotations
import re
import webbrowser

def _norm(tag: str) -> tuple[int,int,int]:
    """バージョンタグを比較可能なタプルに変換します。（例: 'v2.3.1' -> (2, 3, 1)）"""
    if not tag: return (0,0,0)
    t = tag.strip()
    if t.lower().startswith("v"): t = t[1:]
    t = t.split('-',1)[0].split('+',1)[0]
    nums = re.findall(r'\d+', t)[:3]
    parts = [int(x) for x in nums] + [0]*(3-len(nums))
    return tuple(parts[:3])

def _newer(cur: str, latest: str) -> bool:
    """最新バージョンタグが現在のバージョンより新しいか比較します。"""
    return _norm(latest) > _norm(cur)

def maybe_show_update(parent, current_version: str) -> None:
    """GitHub /releases/latest APIを呼び出して最新タグを確認し、新しいバージョンがあれば案内ウィンドウを表示します。"""
    try:
        import requests
    except ImportError:
        # requestsモジュールがない環境ではアップデート確認をスキップします。
        return

    API_URL = "https://api.github.com/repos/deuxdoom/TVerDownloader/releases/latest"
    RELEASE_PAGE_URL = "https://github.com/deuxdoom/TVerDownloader/releases/latest"
    headers = {"Accept": "application/vnd.github+json", "User-Agent": "TVerDownloader-UpdateCheck"}

    latest_tag = ""
    html_url = RELEASE_PAGE_URL
    
    try:
        # GitHub APIを通じて最新リリース情報を取得
        response = requests.get(API_URL, headers=headers, timeout=10)
        response.raise_for_status()
        release_data = response.json()
        latest_tag = release_data.get("tag_name") or release_data.get("name") or ""
        html_url = release_data.get("html_url") or RELEASE_PAGE_URL
    except requests.exceptions.RequestException:
        # API呼び出し失敗時は静かに終了
        return

    # 新しいバージョンがない場合は何もしません
    if not latest_tag or not _newer(current_version, latest_tag):
        return

    # PyQt6.QtWidgetsはUIスレッドでのみimportするのが安全なため、関数内でimport
    from PyQt6.QtWidgets import QMessageBox
    
    msg_box = QMessageBox(parent)
    msg_box.setWindowTitle("新しいバージョンを確認")
    
    # ご要望の文言に修正
    text = f"新しいバージョン {latest_tag} がリリースされました。\n今すぐダウンロードしますか？"
    msg_box.setText(text)
    
    go_btn = msg_box.addButton("移動", QMessageBox.ButtonRole.AcceptRole)
    later_btn = msg_box.addButton("後で", QMessageBox.ButtonRole.RejectRole)
    msg_box.setDefaultButton(go_btn)
    
    msg_box.exec()
    
    if msg_box.clickedButton() == go_btn:
        try:
            webbrowser.open(html_url)
        except Exception:
            pass # ブラウザの起動に失敗しても、致命的なエラーではないため無視する