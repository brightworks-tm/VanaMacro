"""UI要素の多言語対応テキスト管理モジュール

このモジュールはUIに表示されるテキストを日本語と英語で管理します。
"""

from config import Config

# 多言語テキスト辞書
_TEXTS = {
    "ja": {
        # メニュー
        "menu_file": "ファイル",
        "menu_edit": "編集",
        "menu_view": "表示",
        "menu_macro": "マクロ",
        "menu_tools": "ツール",
        "menu_help": "ヘルプ",
        
        # ファイルメニュー
        "action_export_center": "エクスポートセンター...",
        "action_exit": "終了",
        
        # 編集メニュー
        "menu_book": "ブック",
        "menu_set": "セット",
        "action_rename": "名前変更...",
        "action_copy": "コピー",
        "action_paste": "ペースト",
        "action_clear": "クリア",
        
        # 表示メニュー
        "menu_theme": "テーマ",
        "action_reset_layout": "レイアウトをリセット",
        
        # マクロメニュー
        "action_save": "保存",
        
        # ツールメニュー
        "action_char_manage": "キャラ管理...",
        "action_settings": "設定...",
        "action_lang_settings": "言語設定...",
        
        # ヘルプメニュー
        "action_about": "バージョン情報...",
        
        # ボタン・ラベル
        "btn_save": "マクロ保存",
        "btn_import": "FFXIから取込",
        "btn_manage": "管理",
        "label_book": "Book",
        "label_set": "Set",
        "label_macro": "マクロ",
        "label_autotrans": "定型文リスト",
        "label_category": "カテゴリ",
        "label_search": "検索:",
        "label_entries": "エントリ",
        "label_character": "キャラ:",
        "label_bulk_text": "一括テキスト(6行):",
        "action_import": "FFXIから取り込み",
        "action_autotrans": "定型文リスト...",
        "btn_export_center": "エクスポートセンター",
        
        # 設定ダイアログ
        "dlg_settings_title": "設定",
        "dlg_settings_language": "言語:",
        "dlg_settings_japanese": "日本語",
        "dlg_settings_english": "English",
        "dlg_settings_note": "言語を変更すると、UIが即座に更新されます。",
        "btn_ok": "OK",
        "btn_cancel": "キャンセル",
        "btn_apply": "適用",
        
        # メッセージ
        "msg_save_success": "保存しました。",
        "msg_unsaved_changes": "未保存の変更があります。保存しますか？",
        "msg_lang_changed": "言語設定を変更しました。",
        "msg_restart_required": "変更を完全に反映するには、ツールを再起動してください。",
        
        # エクスポートセンター
        "export_title": "エクスポートセンター",
        "export_character": "キャラクター:",
        "export_destination": "出力先:",
        "export_execute": "エクスポート実行",
        "export_to_ffxi": "FFXI USER フォルダへコピー（上書き）",
        "export_group_edit_data": "編集データ",
        "export_group_template": "テンプレート",
        "export_group_history": "エクスポート履歴",
        "export_group_actions": "操作",
        "export_btn_open_folder": "フォルダを開く",
        "export_hint_run": "「エクスポート実行」で FFXI 形式の mcr*.dat を生成します。",
        "export_tooltip_storage_unavailable": "storage モジュールが利用できないためコピーできません。",
        "export_json_label": "JSON:",
        "export_last_modified": "最終更新:",
        "export_template_label": "テンプレート:",
        "export_no_history": "まだエクスポートは実行されていません。",
        "export_cannot_prepare": "エクスポート先を用意できません:",
        "export_no_manifest": "manifest なし",
        "export_load_error": "読込エラー",
        "export_verified": "検証済み",
        "export_skipped": "検証スキップ",
        "export_complete": "エクスポート完了",
        "export_complete_msg": "エクスポート完了:",
        "export_verification_ok": "検証: OK",
        "export_verification_check": "検証: 要確認",
        "export_warning": "警告:",
        "dlg_copy_to_ffxi": "FFXI USER へコピー",
        "msg_copy_to_ffxi_confirm": "FFXI USER フォルダへ上書きコピーします。\n\n元: {source}\n先: {target}\n\n続行しますか？",
        "dlg_copy_complete": "コピー完了",
        "msg_copy_complete": "FFXI USER フォルダへのコピーが完了しました。\n\n{target}",
        "dlg_copy_failed": "コピー失敗",
        "msg_copy_failed_permission": "FFXI USER フォルダへの書き込み権限がありません。\n\nProgram Files 配下にインストールされている場合は、\nVanaMacro を「管理者として実行」してから再度お試しください。\n\n詳細: {error}",
        "msg_copy_failed": "FFXI USER フォルダへのコピーに失敗しました。\n\n{error}",
        "msg_select_export_or_run": "コピーするエクスポート結果を選択するか、\n先にエクスポートを実行してください。",
        
        # キャラクター管理
        "char_manage_title": "キャラ管理",
        "char_id": "ID",
        "char_display_name": "表示名",
        "btn_add": "追加",
        "btn_rename": "名前変更",
        "btn_delete": "削除",
        
        # 定型文ダイアログ
        "autotrans_title": "定型文リスト",
        "autotrans_no_data": "定型文データがありません",
        "btn_insert": "挿入",
        "btn_close": "閉じる",
        
        # About dialog
        "about_title": "VanaMacro",
        "about_text": "VanaMacro v1.2.0\n\nMacro Editor for Final Fantasy XI\n\n© 2025 VanaMacro Project\n\nPython 3.13+ / PyQt6\nhttps://github.com/brightworks-tm/VanaMacro",
        
        # Shortcuts dialog
        "action_shortcuts": "ショートカット一覧...",
        "shortcuts_title": "ショートカット一覧",
        "shortcuts_text": """【ファイル】
Ctrl+I : FFXIから取り込み
Ctrl+E : エクスポートセンター
Ctrl+Q : 終了

【表示】
Ctrl+0 : レイアウトをリセット

【マクロ】
Ctrl+S : マクロを保存
Ctrl+Shift+C : マクロをコピー
Ctrl+Shift+V : マクロをペースト
Ctrl+Shift+D : マクロをクリア
Ctrl+T : 定型文リスト""",
        
        # Bookエリア
        "label_book_rename": "Book名変更",
        "btn_copy": "コピー",
        "btn_paste": "ペースト",
        "btn_clear": "クリア",
        
        # Setエリア
        "btn_set_rename": "Set名変更",
        
        # マクロエリア
        "label_macro_name": "マクロ名:",
        "btn_macro_save": "マクロ保存",
        "btn_macro_copy": "コピー",
        "btn_macro_paste": "ペースト",
        "btn_macro_clear": "クリア",
        
        # ステータスメッセージ
        "status_saved": "保存しました",
        "status_copied": "コピーしました",
        "status_pasted": "ペーストしました",
        "status_cleared": "クリアしました",
        "status_no_selection": "選択されていません",
        
        # ダイアログタイトル
        "dlg_book_rename": "ブック名変更",
        "dlg_set_rename": "セット名変更",
        "dlg_info": "情報",
        "dlg_confirm": "確認",
        "dlg_error": "エラー",
        "dlg_warning": "警告",
        "dlg_folder_add": "フォルダ追加",
        "dlg_display_name": "表示名",
        "dlg_name_change": "名前変更",
        "dlg_folder": "フォルダ",
        "dlg_template": "テンプレート",
        "dlg_export": "エクスポート",
        "dlg_copy": "コピー",
        "dlg_ffxi_import": "FFXI取り込みの確認",
        "dlg_ffxi_import_error": "FFXI取り込みエラー",
        
        # ダイアログメッセージ
        "msg_new_book_name": "新しいブック名:",
        "msg_new_set_name": "セット名（FFXI本体には反映されない見出し用ラベルです）:",
        "msg_folder_name": "フォルダ名（例: user1）:",
        "msg_display_name_optional": "表示名（任意）:",
        "msg_new_display_name": "新しい表示名:",
        "msg_storage_not_set": "storage が未セットのため追加はスキップします。",
        "msg_folder_exists": "同名フォルダが既に存在します。",
        "msg_storage_not_set_rename": "storage が未セットのため名前変更はスキップします。",
        "msg_storage_not_set_delete": "storage が未セットのため削除はスキップします。",
        "msg_confirm_delete": "を削除しますか？（物理フォルダは残ります）",
        "msg_cannot_open_folder": "フォルダを開けません:",
        "msg_select_folder": "開くフォルダを選択してください。",
        "msg_template_not_found": "テンプレートフォルダが見つかりません。",
        "msg_exporter_not_loaded": "exporter モジュールが読み込めないため実行できません。",
        "msg_template_not_found_export": "テンプレートフォルダが見つからないためエクスポートできません。",
        "msg_export_error": "エクスポート処理でエラーが発生しました:",
        "msg_source_folder_not_found": "コピー元のフォルダが見つかりません。",
        "msg_storage_not_available": "storage モジュールが利用できないためコピーできません。",
        "msg_ffxi_folder_not_found": "フォルダが見つかりません:",
        "msg_ffxi_mcr_not_loaded": "ffxi_mcr モジュールを読み込めません。",
        "msg_ffxi_import_confirm": "FFXIのデータを取り込み、現在のVanaMacro上のデータを上書きします。\n\n編集中のデータは、[エクスポート]処理でバックアップされます。\n\n実行してもよろしいですか？\n",
        "msg_ffxi_mcr_not_found": "mcr*.dat が見つからないか、読み込みは失敗しました。",
        "msg_ffxi_import_complete": "FFXIデータの取り込みが完了しました。",
        "dlg_ffxi_import_title": "FFXI取り込み",
        "dlg_complete": "完了",
    },
    "en": {
        # Menu
        "menu_file": "File",
        "menu_edit": "Edit",
        "menu_view": "View",
        "menu_macro": "Macro",
        "menu_tools": "Tools",
        "menu_help": "Help",
        
        # File menu
        "action_export_center": "Export Center...",
        "action_exit": "Exit",
        
        # Edit menu
        "menu_book": "Book",
        "menu_set": "Set",
        "action_rename": "Rename...",
        "action_copy": "Copy",
        "action_paste": "Paste",
        "action_clear": "Clear",
        
        # View menu
        "menu_theme": "Theme",
        "action_reset_layout": "Reset Layout",
        
        # Macro menu
        "action_save": "Save",
        
        # Tools menu
        "action_char_manage": "Character Management...",
        "action_settings": "Settings...",
        "action_lang_settings": "Language Settings...",
        
        # Help menu
        "action_about": "About VanaMacro...",
        
        # Buttons & Labels
        "btn_save": "Save Macro",
        "btn_import": "Import from FFXI",
        "btn_manage": "Manage",
        "label_book": "Book",
        "label_set": "Set",
        "label_macro": "Macro",
        "label_autotrans": "Auto-translate List",
        "label_category": "Category",
        "label_search": "Search:",
        "label_entries": "Entries",
        "label_character": "Character:",
        "label_bulk_text": "Bulk Text (6 lines):",
        "action_import": "Import from FFXI",
        "action_autotrans": "Auto-translate List...",
        "btn_export_center": "Export Center",
        
        # Settings dialog
        "dlg_settings_title": "Settings",
        "dlg_settings_language": "Language:",
        "dlg_settings_japanese": "日本語 (Japanese)",
        "dlg_settings_english": "English",
        "dlg_settings_note": "UI will be updated immediately when you change the language.",
        "btn_ok": "OK",
        "btn_cancel": "Cancel",
        "btn_apply": "Apply",
        
        # Messages
        "msg_save_success": "Saved successfully.",
        "msg_unsaved_changes": "You have unsaved changes. Save them?",
        "msg_lang_changed": "Language settings changed.",
        "msg_restart_required": "Please restart the application to apply the changes.",
        
        # Export Center
        "export_title": "Export Center",
        "export_character": "Character:",
        "export_destination": "Destination:",
        "export_execute": "Execute Export",
        "export_to_ffxi": "Copy to FFXI USER Folder (Overwrite)",
        "export_group_edit_data": "Edit Data",
        "export_group_template": "Template",
        "export_group_history": "Export History",
        "export_group_actions": "Actions",
        "export_btn_open_folder": "Open Folder",
        "export_hint_run": "Click 'Execute Export' to generate FFXI format mcr*.dat files.",
        "export_tooltip_storage_unavailable": "Cannot copy because storage module is unavailable.",
        "export_json_label": "JSON:",
        "export_last_modified": "Last modified:",
        "export_template_label": "Template:",
        "export_no_history": "No exports have been executed yet.",
        "export_cannot_prepare": "Cannot prepare export destination:",
        "export_no_manifest": "No manifest",
        "export_load_error": "Load error",
        "export_verified": "Verified",
        "export_skipped": "Verification skipped",
        "export_complete": "Export Complete",
        "export_complete_msg": "Export completed:",
        "export_verification_ok": "Verification: OK",
        "export_verification_check": "Verification: Check Required",
        "export_warning": "Warning:",
        "dlg_copy_to_ffxi": "Copy to FFXI USER",
        "msg_copy_to_ffxi_confirm": "Will overwrite FFXI USER folder.\n\nSource: {source}\nDestination: {target}\n\nContinue?",
        "dlg_copy_complete": "Copy Complete",
        "msg_copy_complete": "Copy to FFXI USER folder completed.\n\n{target}",
        "dlg_copy_failed": "Copy Failed",
        "msg_copy_failed_permission": "No write permission for FFXI USER folder.\n\nIf installed under Program Files,\nplease 'Run as Administrator' and try again.\n\nDetails: {error}",
        "msg_copy_failed": "Copy to FFXI USER folder failed.\n\n{error}",
        "msg_select_export_or_run": "Select an export result to copy,\nor run export first.",
        
        # Character Management
        "char_manage_title": "Character Management",
        "char_id": "ID",
        "char_display_name": "Display Name",
        "btn_add": "Add",
        "btn_rename": "Rename",
        "btn_delete": "Delete",
        
        # Auto-translate Dialog
        "autotrans_title": "Auto-translate List",
        "autotrans_no_data": "No auto-translate data available",
        "btn_insert": "Insert",
        "btn_close": "Close",
        
        # About dialog
        "about_title": "VanaMacro",
        "about_text": "VanaMacro v1.2.0\n\nMacro Editor for Final Fantasy XI\n\n© 2025 VanaMacro Project\n\nPython 3.13+ / PyQt6\nhttps://github.com/brightworks-tm/VanaMacro",
        
        # Shortcuts dialog
        "action_shortcuts": "Keyboard Shortcuts...",
        "shortcuts_title": "Keyboard Shortcuts",
        "shortcuts_text": """[File]
Ctrl+I : Import from FFXI
Ctrl+E : Export Center
Ctrl+Q : Exit

[View]
Ctrl+0 : Reset Layout

[Macro]
Ctrl+S : Save Macro
Ctrl+Shift+C : Copy Macro
Ctrl+Shift+V : Paste Macro
Ctrl+Shift+D : Clear Macro
Ctrl+T : Auto-translate List""",
        
        # Book Area
        "label_book_rename": "Rename Book",
        "btn_copy": "Copy",
        "btn_paste": "Paste",
        "btn_clear": "Clear",
        
        # Set Area
        "btn_set_rename": "Rename Set",
        
        # Macro Area
        "label_macro_name": "Macro Name:",
        "btn_macro_save": "Save Macro",
        "btn_macro_copy": "Copy",
        "btn_macro_paste": "Paste",
        "btn_macro_clear": "Clear",
        
        # Status Messages
        "status_saved": "Saved",
        "status_copied": "Copied",
        "status_pasted": "Pasted",
        "status_cleared": "Cleared",
        "status_no_selection": "No selection",
        
        # Dialog Titles
        "dlg_book_rename": "Rename Book",
        "dlg_set_rename": "Rename Set",
        "dlg_info": "Information",
        "dlg_confirm": "Confirm",
        "dlg_error": "Error",
        "dlg_warning": "Warning",
        "dlg_folder_add": "Add Folder",
        "dlg_display_name": "Display Name",
        "dlg_name_change": "Rename",
        "dlg_folder": "Folder",
        "dlg_template": "Template",
        "dlg_export": "Export",
        "dlg_copy": "Copy",
        "dlg_ffxi_import": "FFXI Import Confirmation",
        "dlg_ffxi_import_error": "FFXI Import Error",
        
        # Dialog Messages
        "msg_new_book_name": "New book name:",
        "msg_new_set_name": "Set name (label only, not reflected in FFXI):",
        "msg_folder_name": "Folder name (e.g., user1):",
        "msg_display_name_optional": "Display name (optional):",
        "msg_new_display_name": "New display name:",
        "msg_storage_not_set": "Storage module not loaded. Skipping add operation.",
        "msg_folder_exists": "A folder with the same name already exists.",
        "msg_storage_not_set_rename": "Storage module not loaded. Skipping rename operation.",
        "msg_storage_not_set_delete": "Storage module not loaded. Skipping delete operation.",
        "msg_confirm_delete": " will be deleted (physical folder remains).",
        "msg_cannot_open_folder": "Cannot open folder:",
        "msg_select_folder": "Please select a folder to open.",
        "msg_template_not_found": "Template folder not found.",
        "msg_exporter_not_loaded": "Exporter module not loaded. Cannot execute.",
        "msg_template_not_found_export": "Template folder not found. Cannot export.",
        "msg_export_error": "An error occurred during export:",
        "msg_source_folder_not_found": "Source folder not found.",
        "msg_storage_not_available": "Storage module not available. Cannot copy.",
        "msg_ffxi_folder_not_found": "Folder not found:",
        "msg_ffxi_mcr_not_loaded": "Cannot load ffxi_mcr module.",
        "msg_ffxi_import_confirm": "This will import FFXI data and overwrite the current VanaMacro data.\n\nYour current edits will be backed up via [Export].\n\nDo you want to proceed?\n",
        "msg_ffxi_mcr_not_found": "mcr*.dat not found or failed to load.",
        "msg_ffxi_import_complete": "FFXI data import completed.",
        "dlg_ffxi_import_title": "FFXI Import",
        "dlg_complete": "Complete",
    }
}


def get_text(key: str) -> str:
    """指定されたキーに対応する現在の言語のテキストを取得
    
    Args:
        key: テキストキー
        
    Returns:
        現在の言語に対応するテキスト。キーが見つからない場合はキー自体を返す
    """
    lang = Config.get_language()
    return _TEXTS.get(lang, _TEXTS["ja"]).get(key, key)


def get_all_keys() -> list:
    """すべてのテキストキーのリストを取得（デバッグ用）
    
    Returns:
        テキストキーのリスト
    """
    return list(_TEXTS["ja"].keys())


__all__ = ["get_text", "get_all_keys"]
