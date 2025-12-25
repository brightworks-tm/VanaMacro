"""グローバル設定管理モジュール

このモジュールはアプリケーション全体の設定を管理します。
現在は言語設定のみをサポートしています。
"""

import json
import os
from pathlib import Path

class Config:
    """アプリケーション全体の設定を管理するクラス"""
    
    _language: str = "ja"  # デフォルトは日本語
    _config_file: Path = Path("config.json")  # 設定ファイルのパス
    
    @classmethod
    def set_language(cls, lang: str) -> None:
        """言語を設定
        
        Args:
            lang: "ja" (日本語) または "en" (英語)
            
        Raises:
            ValueError: サポートされていない言語の場合
        """
        if lang not in ["ja", "en"]:
            raise ValueError(f"Unsupported language: {lang}. Use 'ja' or 'en'.")
        cls._language = lang
    
    @classmethod
    def get_language(cls) -> str:
        """現在の言語設定を取得
        
        Returns:
            "ja" または "en"
        """
        return cls._language
    
    @classmethod
    def is_japanese(cls) -> bool:
        """日本語モードかどうかを判定
        
        Returns:
            日本語モードの場合 True
        """
        return cls._language == "ja"
    
    @classmethod
    def is_english(cls) -> bool:
        """英語モードかどうかを判定
        
        Returns:
            英語モードの場合 True
        """
        return cls._language == "en"
    
    @classmethod
    def load(cls) -> None:
        """設定ファイルから設定を読み込み"""
        try:
            if cls._config_file.exists():
                with open(cls._config_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    cls._language = data.get("language", "ja")
        except Exception as e:
            print(f"Warning: Failed to load config: {e}")
            cls._language = "ja"  # エラー時はデフォルトに戻す
    
    @classmethod
    def save(cls) -> None:
        """設定ファイルに設定を保存"""
        try:
            data = {
                "language": cls._language
            }
            with open(cls._config_file, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"Warning: Failed to save config: {e}")
        return cls._language == "en"


__all__ = ["Config"]
