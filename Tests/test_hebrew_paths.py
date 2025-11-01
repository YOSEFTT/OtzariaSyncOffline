#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
בדיקת הפונקציות החדשות לטיפול בנתיבים עם עברית
"""

import os
import sys
from pathlib import Path

# ניסיון לייבא chardet עם fallback
try:
    import chardet
    HAS_CHARDET = True
    print("✓ chardet זמין")
except ImportError:
    HAS_CHARDET = False
    print("⚠ chardet לא זמין - ישתמש ב-fallback")

def safe_path_handling(path_str):
    """טיפול בטוח בנתיבים עם תווים בעברית"""
    if not path_str:
        return None
    
    try:
        # שימוש ב-pathlib לטיפול נכון בנתיבים
        path_obj = Path(path_str)
        
        # נרמול הנתיב
        normalized_path = path_obj.resolve()
        
        # החזרת הנתיב כמחרוזת
        return str(normalized_path)
        
    except Exception as e:
        # fallback לטיפול בסיסי
        try:
            return os.path.normpath(os.path.abspath(path_str))
        except Exception:
            return path_str

def detect_file_encoding(file_path):
    """זיהוי קידוד קובץ עם fallback לקידודים נפוצים"""
    try:
        with open(file_path, 'rb') as f:
            raw_data = f.read(8192)  # קריאת חלק מהקובץ לזיהוי
        
        if HAS_CHARDET:
            try:
                detected = chardet.detect(raw_data)
                if detected and detected.get('encoding') and detected.get('confidence', 0) > 0.7:
                    return detected['encoding']
            except Exception:
                pass
        
        # fallback לקידודים נפוצים
        for encoding in ['utf-8', 'utf-16', 'cp1255', 'windows-1255', 'iso-8859-8']:
            try:
                raw_data.decode(encoding)
                return encoding
            except UnicodeDecodeError:
                continue
        
        return 'utf-8'  # ברירת מחדל
        
    except Exception:
        return 'utf-8'

def test_functions():
    """בדיקת הפונקציות"""
    print("\n=== בדיקת פונקציות ===")
    
    # בדיקת safe_path_handling
    test_paths = [
        "C:\\משתמשים\\יוסי\\מסמכים",
        "C:/Users/יוסי/Documents", 
        "אוצריא\\ספרים",
        None,
        ""
    ]
    
    print("\nבדיקת safe_path_handling:")
    for path in test_paths:
        result = safe_path_handling(path)
        print(f"  '{path}' -> '{result}'")
    
    # בדיקת detect_file_encoding על הקובץ הנוכחי
    print(f"\nבדיקת detect_file_encoding על {__file__}:")
    encoding = detect_file_encoding(__file__)
    print(f"  קידוד זוהה: {encoding}")
    
    # בדיקת APPDATA
    print(f"\nבדיקת משתנה APPDATA:")
    appdata = os.getenv("APPDATA")
    if appdata:
        safe_appdata = safe_path_handling(appdata)
        print(f"  APPDATA גולמי: {appdata}")
        print(f"  APPDATA מעובד: {safe_appdata}")
    else:
        print("  APPDATA לא זמין")

if __name__ == "__main__":
    print("בדיקת שיפורים לטיפול בנתיבים עם עברית")
    print("=" * 50)
    
    test_functions()
    
    print("\n✓ הבדיקה הושלמה בהצלחה!")