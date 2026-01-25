#!/usr/bin/env python3
"""
סקריפט לבניית האפליקציה לכל הפלטפורמות:
- Windows (x64)
- Linux (x64)
- macOS Intel (x64)
- macOS Apple Silicon (arm64)

שימוש:
    python build_all_platforms.py [platform]
    
    platform יכול להיות:
    - windows
    - linux
    - macos-intel
    - macos-arm
    - all (ברירת מחדל - בונה לפלטפורמה הנוכחית בלבד)
    - current (בונה לפלטפורמה הנוכחית)
"""

import subprocess
import sys
import os
import platform
import shutil
from pathlib import Path

# שם האפליקציה
APP_NAME = "OtzariaSyncOffline"
MAIN_SCRIPT = "otzaria_sync_offline.py"

def get_current_platform():
    """זיהוי הפלטפורמה הנוכחית"""
    system = platform.system().lower()
    machine = platform.machine().lower()
    
    if system == 'windows':
        return 'windows'
    elif system == 'darwin':
        if machine == 'arm64':
            return 'macos-arm'
        return 'macos-intel'
    elif system == 'linux':
        return 'linux'
    return 'unknown'

def check_pyinstaller():
    """בדיקה ש-PyInstaller מותקן"""
    try:
        import PyInstaller
        print(f"✅ PyInstaller גרסה {PyInstaller.__version__} מותקן")
        return True
    except ImportError:
        print("❌ PyInstaller לא מותקן. מתקין...")
        subprocess.run([sys.executable, "-m", "pip", "install", "pyinstaller"], check=True)
        return True

def get_icon_path():
    """קבלת נתיב האייקון בהתאם לפלטפורמה"""
    current_platform = get_current_platform()
    
    if current_platform == 'windows':
        ico_path = Path("build/sync_otzaria.ico")
        if ico_path.exists():
            return str(ico_path)
    elif current_platform in ['macos-intel', 'macos-arm']:
        icns_path = Path("build/sync_otzaria.icns")
        if icns_path.exists():
            return str(icns_path)
    
    return None

def build_for_platform(target_platform):
    """בניית האפליקציה לפלטפורמה מסוימת"""
    current = get_current_platform()
    
    # בדיקה שאפשר לבנות לפלטפורמה המבוקשת
    if target_platform != current and target_platform != 'current':
        print(f"⚠️ אזהרה: אי אפשר לבנות ל-{target_platform} מ-{current}")
        print("   PyInstaller יכול לבנות רק לפלטפורמה הנוכחית.")
        print("   כדי לבנות לפלטפורמות אחרות, הרץ את הסקריפט על אותה פלטפורמה.")
        return False
    
    if target_platform == 'current':
        target_platform = current
    
    print(f"\n{'='*50}")
    print(f"🔨 בונה עבור: {target_platform}")
    print(f"{'='*50}\n")
    
    # הגדרות בסיסיות
    cmd = [
        sys.executable, "-m", "PyInstaller",
        "--onefile",
        "--windowed",
        f"--name={APP_NAME}",
        "--clean",
    ]
    
    # הוספת אייקון אם קיים
    icon_path = get_icon_path()
    if icon_path:
        cmd.append(f"--icon={icon_path}")
    
    # הגדרות ספציפיות לפלטפורמה
    if target_platform == 'windows':
        # Windows specific
        version_file = Path("build/version_info.txt")
        if version_file.exists():
            cmd.append(f"--version-file={version_file}")
        cmd.append("--console")  # להצגת לוגים בפיתוח, אפשר להסיר
        
    elif target_platform in ['macos-intel', 'macos-arm']:
        # macOS specific
        cmd.extend([
            "--osx-bundle-identifier=com.otzaria.syncoffline",
            "--codesign-identity=-",  # ad-hoc signing
        ])
        if target_platform == 'macos-arm':
            cmd.append("--target-arch=arm64")
        else:
            cmd.append("--target-arch=x86_64")
            
    elif target_platform == 'linux':
        # Linux specific
        pass  # אין הגדרות מיוחדות
    
    # הוספת הקובץ הראשי
    cmd.append(MAIN_SCRIPT)
    
    # תיקיית פלט
    dist_dir = Path(f"dist/{target_platform}")
    dist_dir.mkdir(parents=True, exist_ok=True)
    cmd.extend([f"--distpath={dist_dir}"])
    
    print(f"מריץ: {' '.join(cmd)}\n")
    
    try:
        result = subprocess.run(cmd, check=True)
        print(f"\n✅ הבנייה ל-{target_platform} הושלמה בהצלחה!")
        print(f"   הקובץ נמצא ב: {dist_dir}")
        return True
    except subprocess.CalledProcessError as e:
        print(f"\n❌ שגיאה בבנייה ל-{target_platform}: {e}")
        return False

def main():
    print("=" * 60)
    print("   OtzariaSyncOffline - סקריפט בנייה לכל הפלטפורמות")
    print("=" * 60)
    
    current = get_current_platform()
    print(f"\n📍 פלטפורמה נוכחית: {current}")
    print(f"   מערכת: {platform.system()}")
    print(f"   ארכיטקטורה: {platform.machine()}")
    
    # בדיקת PyInstaller
    if not check_pyinstaller():
        sys.exit(1)
    
    # קבלת פלטפורמת יעד מהארגומנטים
    if len(sys.argv) > 1:
        target = sys.argv[1].lower()
    else:
        target = 'current'
    
    valid_targets = ['windows', 'linux', 'macos-intel', 'macos-arm', 'all', 'current']
    
    if target not in valid_targets:
        print(f"\n❌ פלטפורמה לא חוקית: {target}")
        print(f"   אפשרויות: {', '.join(valid_targets)}")
        sys.exit(1)
    
    if target == 'all':
        print("\n⚠️ 'all' יבנה רק לפלטפורמה הנוכחית.")
        print("   כדי לבנות לכל הפלטפורמות, הרץ את הסקריפט על כל פלטפורמה בנפרד.")
        target = 'current'
    
    success = build_for_platform(target)
    
    if success:
        print("\n" + "=" * 60)
        print("   ✅ הבנייה הושלמה בהצלחה!")
        print("=" * 60)
    else:
        print("\n" + "=" * 60)
        print("   ❌ הבנייה נכשלה")
        print("=" * 60)
        sys.exit(1)

if __name__ == "__main__":
    main()
