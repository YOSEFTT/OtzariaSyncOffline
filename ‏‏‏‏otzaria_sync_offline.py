import re
import json
import os
import base64
import ctypes
import shutil
import requests
import sys
import gc
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
import random
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
icon_base64 = ""

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

class NetworkSpeedMonitor:
    """מחלקה למעקב אחר מהירות הרשת והתאמת מספר החוטים"""
    
    def __init__(self):
        self.download_speeds = []  # רשימת מהירויות הורדה
        self.max_samples = 10  # מספר מדגמים לשמירה
        self.min_workers = 2
        self.max_workers = 10
        self.current_workers = 3  # התחלה עם 3 חוטים
        
    def add_speed_sample(self, bytes_downloaded, time_taken):
        """הוספת מדגם מהירות חדש"""
        if time_taken > 0:
            speed_mbps = (bytes_downloaded / (1024 * 1024)) / time_taken
            self.download_speeds.append(speed_mbps)
            
            # שמירה על מספר מדגמים מוגבל
            if len(self.download_speeds) > self.max_samples:
                self.download_speeds.pop(0)
    
    def get_optimal_workers(self):
        """חישוב מספר החוטים האופטימלי"""
        if len(self.download_speeds) < 3:
            return self.current_workers
        
        avg_speed = sum(self.download_speeds) / len(self.download_speeds)
        
        # התאמת מספר החוטים לפי מהירות ממוצעת
        if avg_speed > 10:  # מהירות גבוהה - יותר חוטים
            optimal = min(self.max_workers, self.current_workers + 1)
        elif avg_speed < 2:  # מהירות נמוכה - פחות חוטים
            optimal = max(self.min_workers, self.current_workers - 1)
        else:
            optimal = self.current_workers
        
        self.current_workers = optimal
        return optimal

class RetryHandler:
    """מחלקה לטיפול בניסיונות חוזרים עם backoff exponential"""
    
    def __init__(self, max_retries=3, base_delay=1.0, max_delay=60.0):
        self.max_retries = max_retries
        self.base_delay = base_delay
        self.max_delay = max_delay
    
    def execute_with_retry(self, func, *args, **kwargs):
        """ביצוע פונקציה עם ניסיונות חוזרים"""
        last_exception = None
        
        for attempt in range(self.max_retries + 1):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                last_exception = e
                
                if attempt == self.max_retries:
                    break
                
                # חישוב זמן המתנה עם jitter
                delay = min(self.base_delay * (2 ** attempt), self.max_delay)
                jitter = random.uniform(0.1, 0.3) * delay
                total_delay = delay + jitter
                
                time.sleep(total_delay)
        
        raise last_exception

class MemoryManager:
    """מחלקה לניהול זיכרון ואופטימיזציה"""
    
    def __init__(self, memory_threshold_mb=500):
        self.memory_threshold = memory_threshold_mb * 1024 * 1024  # המרה לבייטים
        self.last_cleanup = time.time()
        self.cleanup_interval = 30  # ניקוי כל 30 שניות
    
    def get_memory_usage(self):
        """קבלת שימוש זיכרון נוכחי"""
        try:
            process = psutil.Process()
            return process.memory_info().rss
        except:
            return 0
    
    def should_cleanup(self):
        """בדיקה האם צריך לבצע ניקוי זיכרון"""
        current_time = time.time()
        memory_usage = self.get_memory_usage()
        
        return (memory_usage > self.memory_threshold or 
                current_time - self.last_cleanup > self.cleanup_interval)
    
    def cleanup_memory(self):
        """ביצוע ניקוי זיכרון"""
        try:
            gc.collect()  # הפעלת garbage collector
            self.last_cleanup = time.time()
            return True
        except:
            return False
    
    def get_memory_info(self):
        """קבלת מידע על שימוש זיכרון"""
        try:
            process = psutil.Process()
            memory_info = process.memory_info()
            return {
                'rss_mb': memory_info.rss / (1024 * 1024),
                'vms_mb': memory_info.vms / (1024 * 1024),
                'percent': process.memory_percent()
            }
        except:
            return {'rss_mb': 0, 'vms_mb': 0, 'percent': 0}

class WorkerThread(QThread):
    progress = pyqtSignal(int)
    status = pyqtSignal(str)
    finished = pyqtSignal(bool, str)
    manual_selection = pyqtSignal()
    download_progress = pyqtSignal(str, int)  # שם קובץ ואחוז התקדמות
    memory_info = pyqtSignal(dict)  # מידע על זיכרון
    
    def __init__(self, task_type, *args):
        super().__init__()
        self.task_type = task_type
        self.stop_search = False  # דגל לעצירת חיפוש
        self.is_paused = False  # דגל להשהיה
        self.args = args
        self.session = requests.Session()  # שימוש ב session לחיבורים מתמשכים
        
        # אתחול מחלקות עזר
        self.speed_monitor = NetworkSpeedMonitor()
        self.retry_handler = RetryHandler()
        self.memory_manager = MemoryManager()
        
        # הגדרות session משופרות
        self.session.headers.update({
            'User-Agent': 'OtzariaSync/1.0',
            'Accept-Encoding': 'gzip, deflate',
            'Connection': 'keep-alive'
        })
        
        # הגדרת timeout וretries
        from requests.adapters import HTTPAdapter
        from urllib3.util.retry import Retry
        
        retry_strategy = Retry(
            total=3,
            backoff_factor=1,
            status_forcelist=[429, 500, 502, 503, 504],
        )
        adapter = HTTPAdapter(max_retries=retry_strategy)
        self.session.mount("http://", adapter)
        self.session.mount("https://", adapter)
    
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
        """הורדת קובץ יחיד - לשימוש בחוטים מקבילים עם retry ומעקב מהירות"""
        book_name, file_url, target_path = file_info
        
        def download_attempt():
            start_time = time.time()
            
            # בדיקה אם השרת תומך בcompression
            headers = {
                'Accept-Encoding': 'gzip, deflate',
                'User-Agent': 'OtzariaSync/1.0'
            }
            
            response = self.session.get(file_url, timeout=30, headers=headers, stream=True)
            response.raise_for_status()
            
            os.makedirs(os.path.dirname(target_path), exist_ok=True)
            
            # הורדה עם מעקב מהירות
            total_size = int(response.headers.get('content-length', 0))
            downloaded_size = 0
            
            with open(target_path, "wb") as f:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
                        downloaded_size += len(chunk)
            
            # חישוב מהירות והוספה למעקב
            end_time = time.time()
            time_taken = end_time - start_time
            if time_taken > 0:
                self.speed_monitor.add_speed_sample(downloaded_size, time_taken)
            
            return downloaded_size, time_taken
        
        try:
            # ביצוע הורדה עם retry logic
            downloaded_size, time_taken = self.retry_handler.execute_with_retry(download_attempt)
            
            # בדיקת ניקוי זיכרון
            if self.memory_manager.should_cleanup():
                self.memory_manager.cleanup_memory()
                memory_info = self.memory_manager.get_memory_info()
                self.memory_info.emit(memory_info)
            
            return book_name, None, downloaded_size, time_taken  # הצלחה עם נתוני ביצועים
            
        except requests.exceptions.HTTPError as e:
            if e.response and e.response.status_code == 404:
                return book_name, f"קובץ לא נמצא", 0, 0
            else:
                return book_name, f"שגיאה HTTP {e.response.status_code if e.response else 'לא ידועה'}", 0, 0
        except requests.exceptions.Timeout:
            return book_name, "תם זמן ההמתנה", 0, 0
        except requests.exceptions.ConnectionError:
            return book_name, "שגיאת חיבור", 0, 0
        except Exception as e:
            return book_name, f"שגיאה: {str(e)}", 0, 0

    def download_updates(self) -> None:
        global COPIED_DICTA  # הוספה
        self.status.emit("מוריד עדכונים...")
        self.progress.emit(10)
        
        # בדיקת חיבור אינטרנט משופרת
        def test_internet_connection():
            test_urls = [
                "https://raw.githubusercontent.com",
                "https://google.com", 
                "https://github.com"
            ]
            
            for url in test_urls:
                try:
                    response = self.session.get(url, timeout=10)
                    if response.status_code == 200:
                        return True
                except:
                    continue
            return False
        
        try:
            if not self.retry_handler.execute_with_retry(test_internet_connection):
                self.finished.emit(False, "אין חיבור לאינטרנט - נסה שוב מאוחר יותר")
                return
        except Exception as e:
            self.finished.emit(False, f"בעיה בבדיקת חיבור אינטרנט: {str(e)}")
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

        # הורדה מקבילה עם התאמה דינמית של מספר החוטים
        if all_file_tasks:
            self.status.emit(f"מוריד {len(all_file_tasks)} קבצים...")
            
            completed_files = 0
            failed_files = []
            total_downloaded_mb = 0
            start_time = time.time()
            
            # התחלה עם מספר חוטים בסיסי
            current_workers = self.speed_monitor.current_workers
            
            # חלוקת המשימות לקבוצות קטנות להתאמה דינמית
            batch_size = max(5, len(all_file_tasks) // 10)  # לפחות 5, מקסימום 10% מהקבצים
            
            for i in range(0, len(all_file_tasks), batch_size):
                batch_tasks = all_file_tasks[i:i + batch_size]
                
                # בדיקת ביטול
                if self.stop_search:
                    self.status.emit("פעולה בוטלה")
                    return
                
                # התאמת מספר החוטים לפי ביצועים
                if i > 0:  # לא בקבוצה הראשונה
                    optimal_workers = self.speed_monitor.get_optimal_workers()
                    if optimal_workers != current_workers:
                        current_workers = optimal_workers
                        self.status.emit(f"מתאים מספר חוטים ל-{current_workers}")
                
                # הורדת הקבוצה הנוכחית
                with concurrent.futures.ThreadPoolExecutor(max_workers=current_workers) as executor:
                    # שליחת משימות הקבוצה
                    future_to_task = {executor.submit(self.download_file_parallel, task): task for task in batch_tasks}
                    
                    # איסוף תוצאות
                    for future in concurrent.futures.as_completed(future_to_task):
                        # בדיקת השהיה
                        while self.is_paused and not self.stop_search:
                            self.status.emit("פעולה מושהית...")
                            time.sleep(0.5)
                        
                        # בדיקת ביטול
                        if self.stop_search:
                            self.status.emit("פעולה בוטלה")
                            return
                        
                        try:
                            result = future.result()
                            if len(result) == 4:  # תוצאה חדשה עם נתוני ביצועים
                                book_name, error, downloaded_size, time_taken = result
                                if downloaded_size > 0:
                                    total_downloaded_mb += downloaded_size / (1024 * 1024)
                            else:  # תוצאה ישנה
                                book_name, error = result[:2]
                        except Exception as e:
                            book_name = "קובץ לא ידוע"
                            error = f"שגיאה בעיבוד תוצאה: {str(e)}"
                        
                        completed_files += 1
                        
                        if error:
                            failed_files.append(f"{book_name} ({error})")
                            self.status.emit(f"כשל: {book_name}")
                        else:
                            self.status.emit(f"הורד: {book_name}")
                        
                        # עדכון progress עם מידע נוסף
                        progress = 10 + (completed_files / len(all_file_tasks)) * 80
                        self.progress.emit(int(progress))
                        
                        # הצגת סטטיסטיקות כל 10 קבצים
                        if completed_files % 10 == 0:
                            elapsed_time = time.time() - start_time
                            if elapsed_time > 0:
                                avg_speed = total_downloaded_mb / elapsed_time
                                self.status.emit(f"הורדו {completed_files}/{len(all_file_tasks)} | "
                                               f"מהירות: {avg_speed:.1f} MB/s")
            
            all_failed_files.extend(failed_files)
                        
        self.progress.emit(100)
        
        # ניקוי זיכרון סופי
        self.memory_manager.cleanup_memory()
        final_memory = self.memory_manager.get_memory_info()
        
        # סיכום התוצאות
        success_count = len(all_file_tasks) - len(all_failed_files)
        
        if len(all_file_tasks) == 0:
            message = "הספרייה שלך מעודכנת, אין קבצים חדשים להורדה!"
        else:
            elapsed_time = time.time() - start_time
            message = f"הורדו {success_count} קבצים בהצלחה"
            if elapsed_time > 0 and total_downloaded_mb > 0:
                avg_speed = total_downloaded_mb / elapsed_time
                message += f"\nמהירות ממוצעת: {avg_speed:.1f} MB/s"
                message += f"\nסה\"כ הורד: {total_downloaded_mb:.1f} MB"
        
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
            
            # העתקת קבצים עם ניהול זיכרון
            if os.path.exists(BASE_PATH):
                # בדיקת זיכרון לפני העתקה
                initial_memory = self.memory_manager.get_memory_info()
                
                shutil.copytree(BASE_PATH, LOCAL_PATH, dirs_exist_ok=True, 
                              ignore=lambda _, files: [DEL_LIST_FILE_NAME] if DEL_LIST_FILE_NAME in files else [])
                
                # ניקוי זיכרון אחרי העתקה
                self.memory_manager.cleanup_memory()
                post_copy_memory = self.memory_manager.get_memory_info()
                
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
            
            # ניקוי זיכרון סופי
            self.memory_manager.cleanup_memory()
            final_memory = self.memory_manager.get_memory_info()
            
            self.progress.emit(100)
            success_message = ("העדכון הושלם בהצלחה!!\n\n"
                             "כל הספרים נכנסו לתוך תוכנת אוצריא\n")
            self.finished.emit(True, success_message)
            
        except Exception as e:
            # ניקוי זיכרון גם במקרה של שגיאה
            self.memory_manager.cleanup_memory()
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
    
    def update_memory_info(self, memory_info):
        """עדכון מידע זיכרון בממשק"""
        try:
            rss_mb = memory_info.get('rss_mb', 0)
            percent = memory_info.get('percent', 0)
            
            # הצגת מידע זיכרון ביומן אם השימוש גבוה
            if rss_mb > 200:  # מעל 200MB
                self.log(f"שימוש זיכרון: {rss_mb:.0f} MB ({percent:.1f}%)")
                
                # אזהרה אם השימוש גבוה מאוד
                if rss_mb > 500:
                    self.log("אזהרה: שימוש זיכרון גבוה - מבצע ניקוי אוטומטי")
                    
        except Exception as e:
            self.log(f"שגיאה בעדכון מידע זיכרון: {e}")

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
        # חיבור למידע זיכרון אם קיים
        if hasattr(self.worker, 'memory_info'):
            self.worker.memory_info.connect(self.update_memory_info)
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
        # חיבור למידע זיכרון אם קיים
        if hasattr(self.worker, 'memory_info'):
            self.worker.memory_info.connect(self.update_memory_info)
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
        # חיבור למידע זיכרון אם קיים
        if hasattr(self.worker, 'memory_info'):
            self.worker.memory_info.connect(self.update_memory_info)
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

def check_dependencies():
    """בדיקת תלויות נדרשות"""
    missing_deps = []
    
    if missing_deps:
        print("חסרות ספריות נדרשות לתכונות מתקדמות:")
        for dep in missing_deps:
            print(f"- {dep}")
        print("\nהתקן באמצעות: pip install " + " ".join(missing_deps))
        print("התוכנה תפעל במצב בסיסי ללא מעקב זיכרון")
        return False
    
    return True

def main():
    # בדיקת תלויות
    has_all_deps = check_dependencies()
    
    if sys.platform == 'win32':
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(myappid)
    app = QApplication(sys.argv)
    
    # הגדרת גופן עברי
    font = QFont("Segoe UI", 10)
    app.setFont(font)
    
    # הגדרת כיוון RTL
    app.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
    
    window = OtzariaSync()
    
    # הודעה על חסרון תלויות
    if not has_all_deps:
        window.log("אזהרה: חסרות ספריות נדרשות - התוכנה תפעל במצב בסיסי")
    
    window.show()
    
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
