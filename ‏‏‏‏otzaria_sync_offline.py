import re
import json
import os
import base64
import ctypes
import shutil
import requests
import sys
from pathlib import Path
from PyQt6.QtWidgets import (QApplication, QMainWindow, QVBoxLayout, QHBoxLayout, 
                           QWidget, QPushButton, QLabel, QProgressBar, QTextEdit, 
                           QFileDialog, QMessageBox, QFrame)
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QTimer
from PyQt6.QtGui import QFont, QPixmap, QPalette, QColor, QIcon, QPixmap
import base64
import concurrent.futures
import threading
from urllib.parse import urljoin
import time
from datetime import datetime

BASE_URL = "https://raw.githubusercontent.com/zevisvei/otzaria-library/refs/heads/main/"
BASE_PATH = "אוצריא"
LOCAL_PATH = ""
DEL_LIST_FILE_NAME = "del_list.txt"
MANIFEST_FILE_NAME = "files_manifest.json"
STATE_FILE_NAME = "sync_state.json"
COPIED_DICTA = False

# מזהה ייחודי לאפליקציה
myappid = 'MIT.LEARN_PYQT.OtzariaSyncoffline'

# מחרוזת Base64 של האייקון
icon_base64 = "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"

class StateManager:
    """מחלקה לניהול מצב התוכנה עם זיהוי נכון של מיקום הקובץ"""
    
    def __init__(self):
        self.state_file_path = self._get_state_file_path()
        self.state_version = "1.0"
    
    def _get_state_file_path(self):
        """זיהוי נכון של תיקיית התוכנה גם כאשר רצה כ-EXE מ-PyInstaller"""
        try:
            if getattr(sys, 'frozen', False):
                # רץ כ-EXE מ-PyInstaller
                app_dir = os.path.dirname(sys.executable)
            else:
                # רץ כ-Python script
                app_dir = os.path.dirname(os.path.abspath(__file__))
            
            return os.path.join(app_dir, STATE_FILE_NAME)
        except Exception as e:
            # fallback לתיקיה נוכחית
            return STATE_FILE_NAME
    
    def save_state(self, state_data):
        """שמירת מצב עם טיפול בשגיאות"""
        try:
            # הוספת מטא-דאטה
            state_data.update({
                "version": self.state_version,
                "timestamp": datetime.now().isoformat(),
                "app_location": os.path.dirname(self.state_file_path)
            })
            
            # יצירת תיקיה אם לא קיימת
            os.makedirs(os.path.dirname(self.state_file_path), exist_ok=True)
            
            # שמירה עם גיבוי
            backup_path = self.state_file_path + ".backup"
            if os.path.exists(self.state_file_path):
                shutil.copy2(self.state_file_path, backup_path)
            
            with open(self.state_file_path, "w", encoding="utf-8") as f:
                json.dump(state_data, f, indent=2, ensure_ascii=False)
            
            return True
            
        except PermissionError:
            # אין הרשאות כתיבה - נסה בתיקיית המשתמש
            try:
                fallback_path = os.path.join(os.path.expanduser("~"), "OtzariaSync", STATE_FILE_NAME)
                os.makedirs(os.path.dirname(fallback_path), exist_ok=True)
                
                with open(fallback_path, "w", encoding="utf-8") as f:
                    json.dump(state_data, f, indent=2, ensure_ascii=False)
                
                self.state_file_path = fallback_path
                return True
                
            except Exception as e:
                print(f"שגיאה בשמירת מצב (fallback): {e}")
                return False
                
        except Exception as e:
            print(f"שגיאה בשמירת מצב: {e}")
            return False
    
    def load_state(self):
        """טעינת מצב עם בדיקת תקינות"""
        try:
            if not os.path.exists(self.state_file_path):
                return self._get_default_state()
            
            with open(self.state_file_path, "r", encoding="utf-8") as f:
                state = json.load(f)
            
            # בדיקת תקינות המצב
            if not self._validate_state(state):
                print("קובץ מצב לא תקין, מתחיל מחדש")
                return self._get_default_state()
            
            # בדיקת גרסה ומיגרציה
            state_version = state.get("version", "0.0")
            if state_version != self.state_version:
                print(f"מיגרציה מגרסה {state_version} לגרסה {self.state_version}")
                migrated_state = self._migrate_state(state, state_version)
                if migrated_state:
                    return migrated_state
                else:
                    print("מיגרציה נכשלה, מתחיל מחדש")
                    return self._get_default_state()
            
            return state
            
        except json.JSONDecodeError:
            print("קובץ מצב פגום, מנסה לטעון גיבוי")
            return self._load_backup_state()
            
        except Exception as e:
            print(f"שגיאה בטעינת מצב: {e}")
            return self._get_default_state()
    
    def _load_backup_state(self):
        """טעינת מצב מקובץ גיבוי"""
        try:
            backup_path = self.state_file_path + ".backup"
            if os.path.exists(backup_path):
                with open(backup_path, "r", encoding="utf-8") as f:
                    state = json.load(f)
                
                if self._validate_state(state):
                    return state
        except:
            pass
        
        return self._get_default_state()
    
    def _validate_state(self, state):
        """בדיקת תקינות נתוני המצב"""
        if not isinstance(state, dict):
            return False
        
        required_fields = ["step"]
        for field in required_fields:
            if field not in state:
                return False
        
        # בדיקת טווח השלב
        step = state.get("step", 0)
        if not isinstance(step, int) or step < 0 or step > 3:
            return False
        
        return True
    
    def _get_default_state(self):
        """מצב ברירת מחדל"""
        return {
            "step": 0,
            "version": self.state_version,
            "timestamp": datetime.now().isoformat()
        }
    
    def reset_state(self):
        """איפוס מצב התקדמות"""
        try:
            # מחיקת קובץ המצב
            if os.path.exists(self.state_file_path):
                os.remove(self.state_file_path)
            
            # מחיקת גיבוי
            backup_path = self.state_file_path + ".backup"
            if os.path.exists(backup_path):
                os.remove(backup_path)
            
            return True
            
        except Exception as e:
            print(f"שגיאה באיפוס מצב: {e}")
            return False
    
    def _migrate_state(self, old_state, old_version):
        """מיגרציה של מצב מגרסאות ישנות"""
        try:
            # כרגע אין מיגרציות ספציפיות, פשוט מעדכן את הגרסה
            migrated_state = old_state.copy()
            migrated_state["version"] = self.state_version
            migrated_state["migrated_from"] = old_version
            migrated_state["migration_timestamp"] = datetime.now().isoformat()
            
            # בדיקת תקינות המצב המיגרר
            if self._validate_state(migrated_state):
                return migrated_state
            else:
                return None
                
        except Exception as e:
            print(f"שגיאה במיגרציה: {e}")
            return None

class WorkerThread(QThread):
    progress = pyqtSignal(int)
    status = pyqtSignal(str)
    finished = pyqtSignal(bool, str)
    manual_selection = pyqtSignal()
    download_progress = pyqtSignal(str, int)  # שם קובץ ואחוז התקדמות
    
    def __init__(self, task_type, *args):
        super().__init__()
        self.task_type = task_type
        self.stop_search = False  # דגל לעצירת חיפוש
        self.is_paused = False  # דגל להשהיה
        self.args = args
        self.session = requests.Session()  # שימוש ב session לחיבורים מתמשכים
    
    def run(self):
        try:
            if self.task_type == "load_manifests":
                self.load_manifests()
            elif self.task_type == "download_updates":
                self.download_updates()
            elif self.task_type == "apply_updates":
                self.apply_updates()
        except Exception as e:
            self.finished.emit(False, str(e))
    
    def load_manifests(self):
        global LOCAL_PATH
        
        self.stop_search = False
        
        def validate_otzaria_folder(path):
            """בדיקה שהתיקיה מכילה את כל הקבצים והתיקיות הנדרשות"""
            required_items = {
                "אוצריא": "folder",
                "links": "folder", 
                "otzaria.exe": "file",
                MANIFEST_FILE_NAME: "file"
            }
            
            for item, item_type in required_items.items():
                item_path = os.path.join(path, item)
                if item_type == "folder" and not os.path.isdir(item_path):
                    return False
                elif item_type == "file" and not os.path.isfile(item_path):
                    return False
            return True
        
        # שלב 1: חיפוש בכונן C בלבד
        self.status.emit("מחפש בכונן C...")
        self.progress.emit(10)
        
        c_path = "C:\\אוצריא"
        if os.path.exists(c_path) and validate_otzaria_folder(c_path):
            LOCAL_PATH = c_path
            self.status.emit(f"נמצאה תיקיית אוצריא: {LOCAL_PATH}")
            self.copy_manifests_and_finish()
            return
        
        if self.stop_search:
            return
        
        # שלב 2: חיפוש בקובץ העדפות
        self.status.emit("לא נמצא בכונן C, מחפש בקובץ ההגדרות של תוכנת אוצריא...")
        self.progress.emit(20)
        
        try:
            APP_DATA = os.getenv("APPDATA")
            FILE_PATH = os.path.join(APP_DATA, "com.example", "otzaria", "app_preferences.isar")
            
            if os.path.exists(FILE_PATH):
                with open(FILE_PATH, "rb") as f:
                    content = f.read().decode("utf-8", errors="ignore")
                pattern = re.compile(r'key-library-path.*?"([^"]+)"', re.DOTALL)
                m = pattern.search(content)
                if m:
                    preferences_path = m.group(1).replace("/", "\\")
                    if os.path.exists(preferences_path) and validate_otzaria_folder(preferences_path):
                        LOCAL_PATH = preferences_path
                        self.status.emit(f"נמצאה תיקיית אוצריא מקובץ ההגדרות של תוכנת אוצריא: {LOCAL_PATH}")
                        self.copy_manifests_and_finish()
                        return
        except Exception as e:
            self.status.emit(f"שגיאה בקריאת קובץ ההגדרות של תוכנת אוצריא.: {str(e)}")
        
        if self.stop_search:
            return
        
        # שלב 3: חיפוש בתיקיות הבסיסיות של כל הכוננים
        self.status.emit("מחפש בתיקיות הבסיסיות של כל הכוננים...")
        self.progress.emit(40)
        
        drives = [f"{chr(i)}:\\" for i in range(ord('A'), ord('Z')+1) if os.path.exists(f"{chr(i)}:\\")]
        
        for drive in drives:
            # בדיקת השהיה
            while self.is_paused and not self.stop_search:
                self.status.emit("פעולה מושהית...")
                time.sleep(0.5)
            
            if self.stop_search:
                return
            self.status.emit(f"מחפש בכונן {drive}")
            try:
                otzaria_path = os.path.join(drive, "אוצריא")
                if os.path.exists(otzaria_path) and validate_otzaria_folder(otzaria_path):
                    LOCAL_PATH = otzaria_path
                    self.status.emit(f"נמצאה תיקיית אוצריא: {LOCAL_PATH}")
                    self.copy_manifests_and_finish()
                    return
            except:
                continue
        
        if self.stop_search:
            return
        
        # שלב 4: חיפוש בכל המחשב + אפשרות בחירה ידנית
        self.status.emit("מחפש בכל המחשב... (ניתן לבחור ידנית)")
        self.progress.emit(60)
        
        # שליחת signal לאפשרות בחירה ידנית
        self.manual_selection.emit()
        
        # המשך חיפוש בכל המחשב
        for drive in drives:
            # בדיקת השהיה
            while self.is_paused and not self.stop_search:
                self.status.emit("פעולה מושהית...")
                time.sleep(0.5)
            
            if self.stop_search:
                return
            self.status.emit(f"מחפש בכל קבצי כונן {drive}")
            try:
                for root, dirs, files in os.walk(drive):
                    # בדיקת השהיה בלולאה הפנימית
                    while self.is_paused and not self.stop_search:
                        self.status.emit("פעולה מושהית...")
                        time.sleep(0.5)
                    
                    if self.stop_search:
                        return
                    if "אוצריא" in dirs:
                        potential_path = os.path.join(root, "אוצריא")
                        if validate_otzaria_folder(potential_path):
                            LOCAL_PATH = potential_path
                            self.status.emit(f"נמצאה תיקיית אוצריא: {LOCAL_PATH}")
                            self.copy_manifests_and_finish()
                            return
            except:
                continue
        
        # אם לא נמצא כלום
        self.finished.emit(False, "לא נמצאה תיקיית אוצריא. אנא בחר את התיקיה ידנית")

    def copy_manifests_and_finish(self):
        """העתקת קבצי המניפסט וסיום"""
        try:
            global COPIED_DICTA  # הוספה
            self.progress.emit(80)
            copied_dicta = False
            
            # העתקת קבצי המניפסט
            os.makedirs(BASE_PATH, exist_ok=True)
            
            # העתקת קובץ המניפסט הרגיל
            src = os.path.join(LOCAL_PATH, MANIFEST_FILE_NAME)
            if os.path.exists(src):
                dst = os.path.join(BASE_PATH, MANIFEST_FILE_NAME)
                shutil.copy(src, dst)
                self.status.emit(f"הועתק: {MANIFEST_FILE_NAME}")
            
            # העתקת קובץ המניפסט של דיקטה (אופציונלי)
            dicta_manifest = f"dicta_{MANIFEST_FILE_NAME}"
            src = os.path.join(LOCAL_PATH, dicta_manifest)
            if os.path.exists(src):
                dst = os.path.join(BASE_PATH, dicta_manifest)
                shutil.copy(src, dst)
                self.status.emit(f"הועתק: {dicta_manifest}")
                # אם הגענו לכאן – יש מניפסט דיקטה
                copied_dicta = True
            COPIED_DICTA = copied_dicta  # הוספה - שמירת המצב הגלובלי

            self.progress.emit(100)
            self.finished.emit(True, "קבצי המניפסט נטענו בהצלחה")
        except Exception as e:
            self.finished.emit(False, f"שגיאה בהעתקת קבצי המניפסט: {str(e)}")
            
    def download_file_parallel(self, file_info):
        """הורדת קובץ יחיד - לשימוש בחוטים מקבילים"""
        book_name, file_url, target_path = file_info
        
        try:
            # בדיקה אם השרת תומך בcompression
            headers = {'Accept-Encoding': 'gzip, deflate'}
            
            response = self.session.get(file_url, timeout=30, headers=headers)
            response.raise_for_status()
            
            os.makedirs(os.path.dirname(target_path), exist_ok=True)
            
            # הורדה בינארית של כל הקבצים - שומר על הקובץ בדיוק כמו שהוא במקור
            with open(target_path, "wb") as f:
                f.write(response.content)
            
            return book_name, None  # הצלחה
            
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 404:
                return book_name, f"קובץ לא נמצא"
            else:
                return book_name, f"שגיאה {e.response.status_code}"
        except Exception as e:
            return book_name, f"שגיאה: {str(e)}"

    def download_updates(self) -> None:
        global COPIED_DICTA  # הוספה
        self.status.emit("מוריד עדכונים...")
        self.progress.emit(10)
        
        try:
            # בדיקת חיבור אינטרנט
            requests.get("https://google.com", timeout=5)
        except:
            self.finished.emit(False, "אין חיבור לאינטרנט")
            return
        
        # קביעת אילו מניפסטים לעבד
        manifests_to_process = []
        if COPIED_DICTA:  # אם יש קובץ דיקטה - סנכרן את שניהם
            manifests_to_process = ["files_manifest.json", "dicta_files_manifest.json"]
        else:  # אם אין קובץ דיקטה - סנכרן רק את הרגיל
            manifests_to_process = ["files_manifest.json"]        

        all_failed_files = []
        all_file_tasks = []  # רשימת כל הקבצים להורדה
        
        # איסוף כל המשימות
        for manifest_file in manifests_to_process:
            self.status.emit(f"מעבד: {manifest_file}")
            
            new_manifest_url = f"{BASE_URL}/{manifest_file}"
            old_manifest_file_path = os.path.join(BASE_PATH, manifest_file)
            
            try:
                new_manifest_content = self.session.get(new_manifest_url, timeout=10).json()
                with open(old_manifest_file_path, "r", encoding="utf-8") as f:
                    old_manifest_content = json.load(f)
                
                if new_manifest_content == old_manifest_content:
                    self.status.emit(f"אין עדכונים בקובץ ה-{manifest_file}")
                    continue

                # הכנת משימות הורדה
                for book_name, value in new_manifest_content.items():
                    if value["hash"] != old_manifest_content.get(book_name, {}).get("hash"):
                        target_path = os.path.join(BASE_PATH, book_name.replace("/", os.sep))
                        
                        if manifest_file == "dicta_files_manifest.json":
                            file_url = f"{BASE_URL}DictaToOtzaria/ספרים/לא ערוך/{book_name.replace(r'/דיקטה', '')}"
                        else:
                            file_url = f"{BASE_URL}{book_name}"
                        
                        all_file_tasks.append((book_name, file_url, target_path))

                # עדכון המניפסט
                with open(old_manifest_file_path, "w", encoding="utf-8") as f:
                    json.dump(new_manifest_content, f, indent=2, ensure_ascii=False)
                    
            except Exception as e:
                self.finished.emit(False, f"שגיאה בעיבוד {manifest_file}: {str(e)}")
                return

        # הורדה מקבילה עם 5 חוטים
        if all_file_tasks:
            self.status.emit(f"מוריד {len(all_file_tasks)} קבצים בו-זמנית...")
            
            completed_files = 0
            failed_files = []
            
            with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
                # שליחת כל המשימות
                future_to_task = {executor.submit(self.download_file_parallel, task): task for task in all_file_tasks}
                
                # איסוף תוצאות
                for future in concurrent.futures.as_completed(future_to_task):
                    # בדיקת השהיה
                    while self.is_paused and not self.stop_search:
                        self.status.emit("פעולה מושהית...")
                        time.sleep(0.5)  # המתן חצי שנייה לפני בדיקה נוספת
                    
                    # בדיקת ביטול
                    if self.stop_search:
                        self.status.emit("פעולה בוטלה")
                        return
                    
                    book_name, error = future.result()
                    completed_files += 1
                    
                    if error:
                        failed_files.append(f"{book_name} ({error})")
                        self.status.emit(f"כשל: {book_name}")
                    else:
                        self.status.emit(f"הורד: {book_name}")
                    
                    # עדכון progress
                    progress = 10 + (completed_files / len(all_file_tasks)) * 80
                    self.progress.emit(int(progress))
            
            all_failed_files.extend(failed_files)
                        
        self.progress.emit(100)
        
        # סיכום התוצאות
        success_count = len(all_file_tasks) - len(all_failed_files)
        
        if len(all_file_tasks) == 0:
            message = "הספרייה שלך מעודכנת, אין קבצים חדשים להורדה!"
        else:
            message = f"הורדו {success_count} קבצים בהצלחה"
        
        if all_failed_files:
            message += f"\nנכשלו {len(all_failed_files)} קבצים:"
            for failed in all_failed_files[:5]:
                message += f"\n- {failed}"
            if len(all_failed_files) > 5:
                message += f"\n... ועוד {len(all_failed_files) - 5} קבצים"
        
        # שליחת מידע על כמות הקבצים שהורדו
        if len(all_file_tasks) == 0:
            self.finished.emit(True, message + "|NO_FILES")  # סימון מיוחד שאין קבצים
        else:
            self.finished.emit(True, message)
    
    def apply_updates(self):
        self.status.emit("מעדכן קבצים...")
        self.progress.emit(10)
        
        try:
            # בדיקת השהיה לפני העתקת קבצים
            while self.is_paused and not self.stop_search:
                self.status.emit("פעולה מושהית...")
                time.sleep(0.5)
            
            if self.stop_search:
                self.status.emit("פעולה בוטלה")
                return
            
            # העתקת קבצים
            if os.path.exists(BASE_PATH):
                shutil.copytree(BASE_PATH, LOCAL_PATH, dirs_exist_ok=True, 
                              ignore=lambda _, files: [DEL_LIST_FILE_NAME] if DEL_LIST_FILE_NAME in files else [])
                self.status.emit("קבצים הועתקו בהצלחה")
                self.progress.emit(50)
            
            # בדיקת השהיה לפני מחיקת קבצים
            while self.is_paused and not self.stop_search:
                self.status.emit("פעולה מושהית...")
                time.sleep(0.5)
            
            if self.stop_search:
                self.status.emit("פעולה בוטלה")
                return
            
            # מחיקת קבצים
            del_list_file_path = os.path.join(BASE_PATH, DEL_LIST_FILE_NAME)
            if os.path.exists(del_list_file_path):
                with open(del_list_file_path, "r", encoding="utf-8") as f:
                    content = f.readlines()
                
                deleted_count = 0
                for file_path in content:
                    # בדיקת השהיה בכל קובץ
                    while self.is_paused and not self.stop_search:
                        self.status.emit("פעולה מושהית...")
                        time.sleep(0.5)
                    
                    if self.stop_search:
                        self.status.emit("פעולה בוטלה")
                        return
                    
                    file_path = file_path.strip()
                    if not file_path:  # שורה חדשה
                        continue  # שורה חדשה
                    if file_path:
                        full_path = os.path.join(LOCAL_PATH, file_path)
                        if os.path.exists(full_path):
                            os.remove(full_path)
                            deleted_count += 1
                
                os.remove(del_list_file_path)
                self.status.emit(f"נמחקו {deleted_count} קבצים")
                self.progress.emit(80)
            
            # בדיקת השהיה לפני מחיקת תיקיות רקות
            while self.is_paused and not self.stop_search:
                self.status.emit("פעולה מושהית...")
                time.sleep(0.5)
            
            if self.stop_search:
                self.status.emit("פעולה בוטלה")
                return
            
            # מחיקת תיקיות רקות
            for root, dirs, _ in os.walk(LOCAL_PATH, topdown=False):
                for dir_name in dirs:
                    # בדיקת השהיה בכל תיקיה
                    while self.is_paused and not self.stop_search:
                        self.status.emit("פעולה מושהית...")
                        time.sleep(0.5)
                    
                    if self.stop_search:
                        self.status.emit("פעולה בוטלה")
                        return
                    
                    dir_path = os.path.join(root, dir_name)
                    try:
                        if not os.listdir(dir_path):
                            os.rmdir(dir_path)
                    except:
                        pass
            
            self.progress.emit(100)
            self.finished.emit(True, "העדכון הושלם בהצלחה!!\n\nכל הספרים נכנסו לתוך תוכנת אוצריא")
            
        except Exception as e:
            self.finished.emit(False, f"שגיאה בעדכון: {str(e)}")

    # פונקציה לטעינת אייקון ממחרוזת Base64
    def get_app_icon(self):
        pixmap = QPixmap()
        pixmap.loadFromData(base64.b64decode(icon_base64))
        return QIcon(pixmap)
class OtzariaSync(QMainWindow):
    def __init__(self):
        super().__init__()
        self.worker = None
        self.is_paused = False
        self.is_cancelled = False
        self.state_manager = StateManager()
        self.initUI()
        
    def initUI(self):
        self.setWindowTitle("אוצריא - סנכרון אופליין")
        self.setGeometry(100, 100, 600, 550)  # הקטנת הגובה מ-500 ל-400
        # self.setMinimumSize(500, 300)  # גודל מינימלי נמוך יותר
        self.setWindowIcon(self.load_icon_from_base64(icon_base64))
        self.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
        
        # Widget מרכזי
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # Layout ראשי
        main_layout = QVBoxLayout()
        main_layout.setSpacing(10)  # הקטנה מ-20 ל-10
        main_layout.setContentsMargins(15, 15, 15, 15)  # הקטנה מ-20 ל-15
        
        # כותרת
        title_label = QLabel("אוצריא - סנכרון אופליין")
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title_font = QFont()
        title_font.setPointSize(18)
        title_font.setBold(True)
        title_label.setFont(title_font)
        title_label.setStyleSheet("color: #2E4057; margin-bottom: 10px;")
        
        # תת-כותרת
        subtitle_label = QLabel("תוכנה לסנכרון ספרי אוצריא ללא חיבור אינטרנט")
        subtitle_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        subtitle_label.setStyleSheet("color: #5A6C7D; margin-bottom: 17px;")
        
        # מסגרת לכפתורים
        buttons_frame = QFrame()
        buttons_frame.setFrameStyle(QFrame.Shape.StyledPanel)
        buttons_frame.setStyleSheet("QFrame { background-color: #F8F9FA; border-radius: 10px; }")
        buttons_layout = QVBoxLayout()
        buttons_layout.setSpacing(10)  # הקטנה מ-15 ל-10
        buttons_layout.setContentsMargins(15, 15, 15, 15)  # הקטנה מ-20 ל-15
        
        # כפתור 1
        self.btn_load_manifests = QPushButton("טען קבצי נתוני ספרים")
        self.btn_load_manifests.setMinimumHeight(50)
        self.btn_load_manifests.setStyleSheet("""
            QPushButton {
                background-color: #4CAF50;
                color: white;
                border: none;
                border-radius: 8px;
                font-size: 14px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
            QPushButton:disabled {
                background-color: #CCCCCC;
                color: #666666;
            }
        """)
        self.btn_load_manifests.clicked.connect(self.load_manifests)
        
        # כפתור 2
        self.btn_download_updates = QPushButton("הורד קבצים חדשים וקבצים שהתעדכנו")
        self.btn_download_updates.setMinimumHeight(50)
        self.btn_download_updates.setStyleSheet("""
            QPushButton {
                background-color: #2196F3;
                color: white;
                border: none;
                border-radius: 8px;
                font-size: 14px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #1976D2;
            }
            QPushButton:disabled {
                background-color: #CCCCCC;
                color: #666666;
            }
        """)
        self.btn_download_updates.clicked.connect(self.download_updates)
        self.btn_download_updates.setEnabled(False)
        
        # כפתור 3
        self.btn_apply_updates = QPushButton("עדכן שינויים לתוך מאגר הספרים")
        self.btn_apply_updates.setMinimumHeight(50)
        self.btn_apply_updates.setStyleSheet("""
            QPushButton {
                background-color: #FF9800;
                color: white;
                border: none;
                border-radius: 8px;
                font-size: 14px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #F57C00;
            }
            QPushButton:disabled {
                background-color: #CCCCCC;
                color: #666666;
            }
        """)
        self.btn_apply_updates.clicked.connect(self.apply_updates)
        self.btn_apply_updates.setEnabled(False)
        
        # כפתורי בקרה
        control_layout = QHBoxLayout()
        
        self.btn_pause = QPushButton("השהה")
        self.btn_pause.setMinimumHeight(40)
        self.btn_pause.setStyleSheet("""
            QPushButton {
                background-color: #FF9800;
                color: white;
                border: none;
                border-radius: 5px;
                font-size: 12px;
            }
            QPushButton:hover {
                background-color: #F57C00;
            }
        """)
        self.btn_pause.clicked.connect(self.toggle_pause)
        self.btn_pause.setEnabled(False)
        
        self.btn_cancel = QPushButton("בטל")
        self.btn_cancel.setMinimumHeight(40)
        self.btn_cancel.setStyleSheet("""
            QPushButton {
                background-color: #f44336;
                color: white;
                border: none;
                border-radius: 5px;
                font-size: 12px;
            }
            QPushButton:hover {
                background-color: #da190b;
            }
        """)
        self.btn_cancel.clicked.connect(self.cancel_operation)
        self.btn_cancel.setEnabled(False)

        self.btn_reset_data = QPushButton("איפוס מצב")
        self.btn_reset_data.setMinimumHeight(40)
        self.btn_reset_data.setStyleSheet("""
            QPushButton {
                background-color: #9C27B0;
                color: white;
                border: none;
                border-radius: 5px;
                font-size: 12px;
            }
            QPushButton:hover {
                background-color: #7B1FA2;
            }
        """)
        self.btn_reset_data.clicked.connect(self.reset_data)

        # Progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        self.progress_bar.setStyleSheet("""
            QProgressBar {
                border: 2px solid #CCCCCC;
                border-radius: 5px;
                text-align: center;
            }
            QProgressBar::chunk {
                background-color: #4CAF50;
                border-radius: 3px;
            }
        """)
        
        # Step indicator label
        self.step_label = QLabel("שלב נוכחי: טעינת קבצי נתונים")
        self.step_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.step_label.setStyleSheet("""
            color: #1976D2; 
            font-weight: bold; 
            font-size: 14px;
            background-color: #E3F2FD;
            padding: 8px;
            border-radius: 5px;
            margin: 5px;
        """)
        
        # Status label
        self.status_label = QLabel("מוכן לפעולה")
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.status_label.setStyleSheet("color: #2E4057; font-weight: bold;")
        
        # Log text area
        self.log_text = QTextEdit()
        self.log_text.setMaximumHeight(120)  # הקטנה מ-150 ל-120
        self.log_text.setReadOnly(True)
        self.log_text.setStyleSheet("""
            QTextEdit {
                background-color: #F5F5F5;
                border: 1px solid #CCCCCC;
                border-radius: 5px;
                font-family: 'Courier New';
                font-size: 10px;
            }
        """)

        # הוספת כל הרכיבים ללייאוט
        main_layout.addWidget(title_label)
        main_layout.addWidget(subtitle_label)
        
        main_layout.addWidget(self.status_label)
        buttons_layout.addWidget(self.btn_load_manifests)
        buttons_layout.addWidget(self.btn_download_updates)
        buttons_layout.addWidget(self.btn_apply_updates)
        buttons_frame.setLayout(buttons_layout)
        main_layout.addWidget(buttons_frame)
        main_layout.addWidget(self.step_label)
        main_layout.addWidget(self.progress_bar)
        control_layout.addWidget(self.btn_pause)
        control_layout.addWidget(self.btn_cancel)
        buttons_layout.addLayout(control_layout)
        control_layout.addWidget(self.btn_reset_data)      
        # תווית יומן פעולות עם מרווח קטן
        log_label = QLabel("יומן פעולות:")
        log_label.setStyleSheet("margin-bottom: 2px; margin-top: 5px; font-weight: bold;")
        main_layout.addWidget(log_label)
        main_layout.addWidget(self.log_text)
        
        central_widget.setLayout(main_layout)
        
        # סגנון כללי
        self.setStyleSheet("""
            QMainWindow {
                background-color: #FFFFFF;
            }
            QLabel {
                color: #2E4057;
            }
        """)
        
        self.load_and_set_state()
        self.check_pyinstaller_compatibility()
        self.log("התוכנה מוכנה לפעולה")

    # הוספת כפתור איפוס מצב
    def add_reset_button(self):
        """הוספת כפתור איפוס מצב לממשק"""
        self.btn_reset = QPushButton("איפוס מצב")
        self.btn_reset.setMinimumHeight(30)
        self.btn_reset.setStyleSheet("""
            QPushButton {
                background-color: #f44336;
                color: white;
                border: none;
                border-radius: 5px;
                font-size: 12px;
            }
            QPushButton:hover {
                background-color: #da190b;
            }
        """)
        self.btn_reset.clicked.connect(self.reset_state)
        
        # הוספה לממשק (ב layout הראשי)
        return self.btn_reset        

    def save_sync_state(self, state_data):
        """שמירת מצב התקדמות באמצעות StateManager"""
        # הוספת מצב השהיה וביטול
        state_data.update({
            "is_paused": getattr(self, 'is_paused', False),
            "is_cancelled": getattr(self, 'is_cancelled', False),
            "local_path": LOCAL_PATH,
            "copied_dicta": COPIED_DICTA
        })
        
        success = self.state_manager.save_state(state_data)
        if not success:
            self.show_error_message(
                "שגיאה בשמירה",
                "לא ניתן לשמור את מצב ההתקדמות.\nייתכן שאין הרשאות כתיבה או שהדיסק מלא.",
                "נסה להריץ את התוכנה כמנהל או לפנות מקום בדיסק."
            )
        else:
            self.log("מצב התקדמות נשמר בהצלחה")
        return success

    def load_sync_state(self):
        """טעינת מצב התקדמות באמצעות StateManager"""
        try:
            state = self.state_manager.load_state()
            
            # בדיקה אם המצב נטען בהצלחה
            if state.get("step", 0) > 0:
                self.log("מצב התקדמות נטען בהצלחה")
                
                # הצגת מידע על המצב הנטען
                step = state.get("step", 0)
                timestamp = state.get("timestamp", "לא ידוע")
                if timestamp != "לא ידוע":
                    try:
                        from datetime import datetime
                        dt = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
                        timestamp = dt.strftime("%d/%m/%Y %H:%M")
                    except:
                        pass
                
                self.log(f"נטען מצב משלב {step} מתאריך {timestamp}")
            
            # עדכון משתנים גלובליים
            global LOCAL_PATH, COPIED_DICTA
            if "local_path" in state:
                LOCAL_PATH = state["local_path"]
            if "copied_dicta" in state:
                COPIED_DICTA = state["copied_dicta"]
                
            return state
            
        except Exception as e:
            self.handle_state_load_error(str(e))
            return {"step": 0}

    def reset_sync_state(self):
        """איפוס מצב התקדמות באמצעות StateManager"""
        success = self.state_manager.reset_state()
        if success:
            self.log("מצב התקדמות אופס בהצלחה")
        else:
            self.log("שגיאה באיפוס מצב התקדמות")
        return success

    def load_and_set_state(self):
        """טעינת מצב והגדרת כפתורים בהתאם"""
        state = self.load_sync_state()
        current_step = state.get("step", 0)
        
        # עדכון UI מהמצב הטעון
        self.update_ui_from_state(state)
        
        # הצגת הודעת סטטוס מתאימה
        if current_step == 0:
            self.status_label.setText("מוכן לטעינת קבצי נתונים")
        elif current_step == 1:
            self.status_label.setText("מוכן להורדת עדכונים")
            self.log("מצב נטען: אפשר להמשיך מההורדה")
        elif current_step == 2:
            self.status_label.setText("מוכן להחלת עדכונים")
            self.log("מצב נטען: אפשר להמשיך מההחלה")
        elif current_step == 3:
            self.status_label.setText("כל השלבים הושלמו")
            self.log("מצב נטען: כל השלבים הושלמו")
    
    def update_ui_from_state(self, state):
        """עדכון ממשק המשתמש בהתאם למצב הטעון"""
        current_step = state.get("step", 0)
        
        # עדכון תווית השלב
        step_names = {
            0: "שלב 1, טעינת קבצי נתונים",
            1: "שלב 2, הורדת עדכונים", 
            2: "שלב 3, החלת עדכונים",
            3: "הושלם! כל השלבים בוצעו"
        }
        self.step_label.setText(f"שלב נוכחי: {step_names.get(current_step, 'לא ידוע')}")
        
        # עדכון צבע תווית השלב
        if current_step == 3:
            self.step_label.setStyleSheet("""
                color: #2E7D32; 
                font-weight: bold; 
                font-size: 14px;
                background-color: #E8F5E8;
                padding: 8px;
                border-radius: 5px;
                margin: 5px;
            """)
        else:
            self.step_label.setStyleSheet("""
                color: #1976D2; 
                font-weight: bold; 
                font-size: 14px;
                background-color: #E3F2FD;
                padding: 8px;
                border-radius: 5px;
                margin: 5px;
            """)
        
        # איפוס כל הכפתורים
        self.btn_load_manifests.setEnabled(False)
        self.btn_download_updates.setEnabled(False)
        self.btn_apply_updates.setEnabled(False)
        
        # הפעלת כפתורים בהתאם למצב
        if current_step >= 0:
            self.btn_load_manifests.setEnabled(True)
        if current_step >= 1:
            self.btn_download_updates.setEnabled(True)
        if current_step >= 2:
            self.btn_apply_updates.setEnabled(True)
        
        # הפעלת הכפתור הבא בתור
        if current_step == 0:
            self.btn_download_updates.setEnabled(False)
            self.btn_apply_updates.setEnabled(False)
        elif current_step == 1:
            self.btn_apply_updates.setEnabled(False)

    def reset_state(self):
        """איפוס מצב התקדמות עם דיאלוג אישור"""
        reply = QMessageBox.question(self, "איפוס מצב", 
                                "האם אתה בטוח שברצונך לאפס את מצב ההתקדמות?\n\nפעולה זו תמחק את כל ההתקדמות השמורה ותחזיר אותך לשלב הראשון.",
                                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        
        if reply == QMessageBox.StandardButton.Yes:
            success = self.reset_sync_state()
            if success:
                # איפוס משתנים גלובליים
                global LOCAL_PATH, COPIED_DICTA
                LOCAL_PATH = ""
                COPIED_DICTA = False
                
                # עדכון UI למצב התחלתי
                self.load_and_set_state()
                QMessageBox.information(self, "איפוס הושלם", "מצב ההתקדמות אופס בהצלחה!")
            else:
                QMessageBox.warning(self, "שגיאה", "שגיאה באיפוס מצב ההתקדמות")

    def reset_data(self):
        """איפוס נתוני המצב השמורים - אותה פונקציה כמו reset_state"""
        self.reset_state()            

    def log(self, message):
        self.log_text.append(message)
        self.log_text.verticalScrollBar().setValue(self.log_text.verticalScrollBar().maximum())
    
    def show_error_message(self, title, message, details=None):
        """הצגת הודעת שגיאה ידידותית למשתמש"""
        msg_box = QMessageBox(self)
        msg_box.setIcon(QMessageBox.Icon.Critical)
        msg_box.setWindowTitle(title)
        msg_box.setText(message)
        
        if details:
            msg_box.setDetailedText(details)
        
        msg_box.exec()
        self.log(f"שגיאה: {message}")
    
    def show_success_message(self, title, message):
        """הצגת הודעת הצלחה למשתמש"""
        QMessageBox.information(self, title, message)
        self.log(f"הצלחה: {message}")
    
    def handle_state_load_error(self, error_msg):
        """טיפול בשגיאות טעינת מצב"""
        self.log(f"שגיאה בטעינת מצב: {error_msg}")
        self.show_error_message(
            "שגיאה בטעינת מצב",
            "לא ניתן לטעון את מצב ההתקדמות השמור.\nהתוכנה תתחיל מההתחלה.",
            error_msg
        )
        # איפוס למצב התחלתי
        self.update_ui_from_state({"step": 0})
    
    def check_pyinstaller_compatibility(self):
        """בדיקת תאימות PyInstaller ומיקום קובץ המצב"""
        try:
            state_path = self.state_manager.state_file_path
            
            if getattr(sys, 'frozen', False):
                # רץ כ-EXE
                exe_dir = os.path.dirname(sys.executable)
                self.log(f"רץ כ-EXE, תיקיית התוכנה: {exe_dir}")
                self.log(f"קובץ מצב יישמר ב: {state_path}")
                
                # בדיקת הרשאות כתיבה
                try:
                    test_file = os.path.join(exe_dir, "test_write.tmp")
                    with open(test_file, "w") as f:
                        f.write("test")
                    os.remove(test_file)
                    self.log("הרשאות כתיבה: תקינות")
                except:
                    self.log("אזהרה: אין הרשאות כתיבה בתיקיית התוכנה")
                    fallback_dir = os.path.join(os.path.expanduser("~"), "OtzariaSync")
                    self.log(f"קובץ מצב יישמר ב: {fallback_dir}")
            else:
                # רץ כ-Python script
                script_dir = os.path.dirname(os.path.abspath(__file__))
                self.log(f"רץ כ-Python script, תיקיית הסקריפט: {script_dir}")
                self.log(f"קובץ מצב יישמר ב: {state_path}")
                
        except Exception as e:
            self.log(f"שגיאה בבדיקת תאימות: {e}")
    
    def load_manifests(self):
        if self.worker and self.worker.isRunning():
            return
            
        self.progress_bar.setVisible(True)
        self.progress_bar.setValue(0)
        self.btn_load_manifests.setEnabled(False)
        
        # עדכון הודעות סטטוס
        self.status_label.setText("מתחיל טעינת קבצי נתונים...")
        self.log("מתחיל שלב 1: טעינת קבצי נתונים")
        
        self.worker = WorkerThread("load_manifests")
        # איפוס מצב השהיה
        self.is_paused = False
        self.worker.is_paused = False
        self.worker.progress.connect(self.progress_bar.setValue)
        self.worker.status.connect(self.status_label.setText)
        self.worker.status.connect(self.log)
        self.worker.finished.connect(self.on_load_manifests_finished)
        self.worker.manual_selection.connect(self.show_manual_selection)  # חיבור חדש
        self.worker.start()
        self.btn_pause.setEnabled(True)
        self.btn_cancel.setEnabled(True)
        
    def show_manual_selection(self):
        """הצגת חלון בחירת תיקיה ידנית"""
        folder = QFileDialog.getExistingDirectory(self, "בחר את תיקיית אוצריא")
        if folder:
            global LOCAL_PATH
            LOCAL_PATH = folder
            # עצירת החיפוש הנוכחי והתחלת חיפוש חדש
            if self.worker:
                self.worker.stop_search = True
            self.load_manifests()
        else:
            QMessageBox.warning(self, "שגיאה", "לא נבחרה תיקיה")

    # שינוי קל בטיפול בשגיאות
    def on_load_manifests_finished(self, success, message):
        self.progress_bar.setVisible(False)
        self.status_label.setText(message)
        self.log(message)
        self.reset_buttons()
        
        if success:
            # שמירת מצב עם נתונים נוספים
            state_data = {
                "step": 1,
                "manifests_loaded": True,
                "last_sync_time": datetime.now().isoformat()
            }
            self.save_sync_state(state_data)
            self.btn_download_updates.setEnabled(True)
            self.log("שלב 1 הושלם - קבצי המניפסט נטענו")
            QMessageBox.information(self, "הצלחה", message)
        else:
            self.btn_load_manifests.setEnabled(True)
            # שמירת מצב גם במקרה של שגיאה כדי לאפשר המשך
            self.save_state({"step": 0, "error": message})
            QMessageBox.critical(self, "שגיאה", message)
    
    def download_updates(self):
        if self.worker and self.worker.isRunning():
            return
            
        self.progress_bar.setVisible(True)
        self.progress_bar.setValue(0)
        self.btn_download_updates.setEnabled(False)
        
        # עדכון הודעות סטטוס
        self.status_label.setText("מתחיל הורדת עדכונים...")
        self.log("מתחיל שלב 2: הורדת עדכונים")
        
        self.worker = WorkerThread("download_updates")
        # איפוס מצב השהיה
        self.is_paused = False
        self.worker.is_paused = False
        self.worker.progress.connect(self.progress_bar.setValue)
        self.worker.status.connect(self.status_label.setText)
        self.worker.status.connect(self.log)
        self.worker.finished.connect(self.on_download_updates_finished)
        self.worker.start()
        self.btn_pause.setEnabled(True)
        self.btn_cancel.setEnabled(True)
        
    def on_download_updates_finished(self, success, message):
        self.progress_bar.setVisible(False)
        
        # בדיקה אם אין קבצים חדשים
        no_files_to_download = message.endswith("|NO_FILES")
        if no_files_to_download:
            # הסרת הסימון המיוחד מההודעה
            message = message.replace("|NO_FILES", "")
        
        self.status_label.setText(message)
        self.log(message)
        self.reset_buttons()
        
        if success:
            if no_files_to_download:
                # אין קבצים חדשים - נשאר במצב הורדה
                state_data = {
                    "step": 1,  # נשאר בשלב 1
                    "manifests_loaded": True,
                    "updates_downloaded": False,  # לא הורדנו כלום
                    "last_sync_time": datetime.now().isoformat()
                }
                self.save_sync_state(state_data)
                self.btn_download_updates.setEnabled(True)  # אפשר לנסות שוב מאוחר יותר
                self.log("אין קבצים חדשים - ניתן לבדוק שוב מאוחר יותר")
                QMessageBox.information(self, "מעודכן", message)
            else:
                # יש קבצים שהורדו - עובר לשלב הבא
                state_data = {
                    "step": 2,
                    "manifests_loaded": True,
                    "updates_downloaded": True,
                    "last_sync_time": datetime.now().isoformat()
                }
                self.save_sync_state(state_data)
                self.btn_apply_updates.setEnabled(True)
                self.log("שלב 2 הושלם - עדכונים הורדו")
                QMessageBox.information(self, "הצלחה", message)
        else:
            self.btn_download_updates.setEnabled(True)
            # שמירת מצב גם במקרה של שגיאה
            state_data = {
                "step": 1,
                "manifests_loaded": True,
                "updates_downloaded": False,
                "error": message,
                "last_sync_time": datetime.now().isoformat()
            }
            self.save_sync_state(state_data)
            QMessageBox.critical(self, "שגיאה", message)
    
    def apply_updates(self):
        if self.worker and self.worker.isRunning():
            return
            
        self.progress_bar.setVisible(True)
        self.progress_bar.setValue(0)
        self.btn_apply_updates.setEnabled(False)
        
        # עדכון הודעות סטטוס
        self.status_label.setText("מתחיל החלת עדכונים...")
        self.log("מתחיל שלב 3: החלת עדכונים")
        
        self.worker = WorkerThread("apply_updates")
        # איפוס מצב השהיה
        self.is_paused = False
        self.worker.is_paused = False
        self.worker.progress.connect(self.progress_bar.setValue)
        self.worker.status.connect(self.status_label.setText)
        self.worker.status.connect(self.log)
        self.worker.finished.connect(self.on_apply_updates_finished)
        self.worker.start()
        self.btn_pause.setEnabled(True)
        self.btn_cancel.setEnabled(True)
    
    def on_apply_updates_finished(self, success, message):
        self.progress_bar.setVisible(False)
        self.status_label.setText(message)
        self.log(message)
        self.reset_buttons()
        
        if success:
            # שמירת מצב השלמה
            state_data = {
                "step": 3,
                "manifests_loaded": True,
                "updates_downloaded": True,
                "updates_applied": True,
                "completed": True,
                "last_sync_time": datetime.now().isoformat()
            }
            self.save_sync_state(state_data)
            
            # איפוס הכפתורים לתחילת המחזור
            self.btn_load_manifests.setEnabled(True)
            self.btn_download_updates.setEnabled(False)
            self.btn_apply_updates.setEnabled(False)
            self.log("כל השלבים הושלמו בהצלחה!")
            QMessageBox.information(self, "הצלחה", message)
        else:
            self.btn_apply_updates.setEnabled(True)
            # שמירת מצב שגיאה
            state_data = {
                "step": 2,
                "manifests_loaded": True,
                "updates_downloaded": True,
                "updates_applied": False,
                "error": message,
                "last_sync_time": datetime.now().isoformat()
            }
            self.save_sync_state(state_data)
            QMessageBox.critical(self, "שגיאה", message)

    def toggle_pause(self):
        if self.worker and self.worker.isRunning():
            self.is_paused = not self.is_paused
            # העברת מצב ההשהיה ל-worker
            self.worker.is_paused = self.is_paused
            
            if self.is_paused:
                self.btn_pause.setText("המשך")
                self.btn_pause.setStyleSheet("""
                    QPushButton {
                        background-color: #4CAF50;
                        color: white;
                        border: none;
                        border-radius: 5px;
                        font-size: 12px;
                    }
                    QPushButton:hover {
                        background-color: #45a049;
                    }
                """)
                self.status_label.setText("פעולה מושהית")
            else:
                self.btn_pause.setText("השהה")
                self.btn_pause.setStyleSheet("""
                    QPushButton {
                        background-color: #FF9800;
                        color: white;
                        border: none;
                        border-radius: 5px;
                        font-size: 12px;
                    }
                    QPushButton:hover {
                        background-color: #F57C00;
                    }
                """)
                self.status_label.setText("פעולה מתבצעת")
    
    def cancel_operation(self):
        if self.worker and self.worker.isRunning():
            self.is_cancelled = True
            self.worker.stop_search = True
            self.worker.terminate()  # שינוי מ-quit() ל-terminate()
            self.worker.wait(3000)  # המתן מקסימום 3 שניות
            self.progress_bar.setVisible(False)
            self.status_label.setText("פעולה בוטלה")
            self.log("פעולה בוטלה על ידי המשתמש")
            self.reset_buttons()
            
    def reset_buttons(self):
        self.btn_pause.setEnabled(False)
        self.btn_cancel.setEnabled(False)
        self.btn_pause.setText("השהה")
        # איפוס עיצוב כפתור השהיה למצב הרגיל
        self.btn_pause.setStyleSheet("""
            QPushButton {
                background-color: #FF9800;
                color: white;
                border: none;
                border-radius: 5px;
                font-size: 12px;
            }
            QPushButton:hover {
                background-color: #F57C00;
            }
        """)
        self.is_paused = False
        self.is_cancelled = False            

    # פונקציה לטעינת אייקון ממחרוזת Base64
    def load_icon_from_base64(self, base64_string):
        pixmap = QPixmap()
        pixmap.loadFromData(base64.b64decode(base64_string))
        return QIcon(pixmap)

def main():
    if sys.platform == 'win32':
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(myappid)
    app = QApplication(sys.argv)
    
    # הגדרת גופן עברי
    font = QFont("Segoe UI", 10)
    app.setFont(font)
    
    # הגדרת כיוון RTL
    app.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
    
    window = OtzariaSync()
    window.show()
    
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
