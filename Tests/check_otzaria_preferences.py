#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
בדיקה מהירה של קובץ העדפות אוצריא
"""

import os
from pathlib import Path

def check_otzaria_preferences():
    """בדיקה מפורטת של קובץ העדפות אוצריא"""
    print("🔍 בודק קובץ העדפות של אוצריא")
    print("=" * 50)
    
    # בדיקת APPDATA
    appdata = os.getenv("APPDATA")
    print(f"📁 APPDATA: {appdata}")
    
    if not appdata:
        print("❌ APPDATA לא זמין")
        return
    
    # בניית הנתיב
    base_path = Path(appdata)
    com_example_path = base_path / "com.example"
    otzaria_path = com_example_path / "otzaria"
    preferences_file = otzaria_path / "app_preferences.isar"
    
    print(f"📂 נתיב com.example: {com_example_path}")
    print(f"📂 קיים: {com_example_path.exists()}")
    
    if com_example_path.exists():
        try:
            subdirs = [d.name for d in com_example_path.iterdir() if d.is_dir()]
            print(f"📋 תיקיות בתוך com.example: {subdirs}")
        except Exception as e:
            print(f"❌ שגיאה ברישום תיקיות: {e}")
    
    print(f"📂 נתיב otzaria: {otzaria_path}")
    print(f"📂 קיים: {otzaria_path.exists()}")
    
    if otzaria_path.exists():
        try:
            files = [f.name for f in otzaria_path.iterdir()]
            print(f"📋 קבצים בתוך otzaria: {files}")
        except Exception as e:
            print(f"❌ שגיאה ברישום קבצים: {e}")
    
    print(f"📄 קובץ העדפות: {preferences_file}")
    print(f"📄 קיים: {preferences_file.exists()}")
    
    if preferences_file.exists():
        try:
            size = preferences_file.stat().st_size
            print(f"📊 גודל: {size} בייטים")
            
            # קריאת תחילת הקובץ
            with open(preferences_file, 'rb') as f:
                first_bytes = f.read(100)
            print(f"🔍 100 בייטים ראשונים: {first_bytes}")
            
            # ניסיון קריאה כטקסט
            try:
                with open(preferences_file, 'r', encoding='utf-8', errors='replace') as f:
                    content = f.read(500)
                print(f"📖 תוכן (500 תווים ראשונים): {content}")
            except Exception as e:
                print(f"❌ שגיאה בקריאת טקסט: {e}")
                
        except Exception as e:
            print(f"❌ שגיאה בקבלת מידע על הקובץ: {e}")
    
    # חיפוש קבצים דומים
    print("\n🔍 מחפש קבצים דומים...")
    for root, dirs, files in os.walk(base_path):
        for file in files:
            if 'pref' in file.lower() or 'otzar' in file.lower():
                full_path = Path(root) / file
                print(f"📄 נמצא קובץ דומה: {full_path}")

if __name__ == "__main__":
    check_otzaria_preferences()