import re
import json
import os
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
            if self.stop_search:
                return
            self.status.emit(f"מחפש בכל קבצי כונן {drive}")
            try:
                for root, dirs, files in os.walk(drive):
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
            with open(target_path, "w", encoding="utf-8") as f:
                f.write(response.text)
            
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
        message = f"הורדו {success_count} קבצים בהצלחה"
        
        if all_failed_files:
            message += f"\nנכשלו {len(all_failed_files)} קבצים:"
            for failed in all_failed_files[:5]:
                message += f"\n- {failed}"
            if len(all_failed_files) > 5:
                message += f"\n... ועוד {len(all_failed_files) - 5} קבצים"
        
        self.finished.emit(True, message)
    
    def apply_updates(self):
        self.status.emit("מעדכן קבצים...")
        self.progress.emit(10)
        
        try:
            # העתקת קבצים
            if os.path.exists(BASE_PATH):
                shutil.copytree(BASE_PATH, LOCAL_PATH, dirs_exist_ok=True, 
                              ignore=lambda _, files: [DEL_LIST_FILE_NAME] if DEL_LIST_FILE_NAME in files else [])
                self.status.emit("קבצים הועתקו בהצלחה")
                self.progress.emit(50)
            
            # מחיקת קבצים
            del_list_file_path = os.path.join(BASE_PATH, DEL_LIST_FILE_NAME)
            if os.path.exists(del_list_file_path):
                with open(del_list_file_path, "r", encoding="utf-8") as f:
                    content = f.readlines()
                
                deleted_count = 0
                for file_path in content:
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
            
            # מחיקת תיקיות רקות
            for root, dirs, _ in os.walk(LOCAL_PATH, topdown=False):
                for dir_name in dirs:
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


class OtzariaSync(QMainWindow):
    def __init__(self):
        super().__init__()
        self.worker = None
        self.is_paused = False
        self.is_cancelled = False
        self.initUI()
        
    def initUI(self):
        self.setWindowTitle("אוצריא - סנכרון אופליין")
        self.setGeometry(100, 100, 600, 500)
        self.setWindowIcon(self.load_icon_from_base64(icon_base64))
        self.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
        
        # Widget מרכזי
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # Layout ראשי
        main_layout = QVBoxLayout()
        main_layout.setSpacing(20)
        main_layout.setContentsMargins(20, 20, 20, 20)
        
        # כותרת
        title_label = QLabel("אוצריא - סנכרון אופליין")
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title_font = QFont()
        title_font.setPointSize(18)
        title_font.setBold(True)
        title_label.setFont(title_font)
        title_label.setStyleSheet("color: #2E4057; margin-bottom: 10px;")
        
        # תת-כותרת
        subtitle_label = QLabel("כלי לסנכרון ספרי אוצריא ללא חיבור אינטרנט")
        subtitle_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        subtitle_label.setStyleSheet("color: #5A6C7D; margin-bottom: 20px;")
        
        # מסגרת לכפתורים
        buttons_frame = QFrame()
        buttons_frame.setFrameStyle(QFrame.Shape.StyledPanel)
        buttons_frame.setStyleSheet("QFrame { background-color: #F8F9FA; border-radius: 10px; }")
        buttons_layout = QVBoxLayout()
        buttons_layout.setSpacing(15)
        buttons_layout.setContentsMargins(20, 20, 20, 20)
        
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

        self.btn_reset_data = QPushButton("איפוס נתונים")
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
        
        # Status label
        self.status_label = QLabel("מוכן לפעולה")
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.status_label.setStyleSheet("color: #2E4057; font-weight: bold;")
        
        # Log text area
        self.log_text = QTextEdit()
        self.log_text.setMaximumHeight(150)
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
        
        buttons_layout.addWidget(self.btn_load_manifests)
        buttons_layout.addWidget(self.btn_download_updates)
        buttons_layout.addWidget(self.btn_apply_updates)
        buttons_frame.setLayout(buttons_layout)
        main_layout.addWidget(buttons_frame)
        main_layout.addWidget(self.progress_bar)
        main_layout.addWidget(self.status_label)
        control_layout.addWidget(self.btn_pause)
        control_layout.addWidget(self.btn_cancel)
        buttons_layout.addLayout(control_layout)
        control_layout.addWidget(self.btn_reset_data)      
        main_layout.addWidget(QLabel("יומן פעולות:"))
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

    def save_state(self, state_data):
        """שמירת מצב התקדמות"""
        try:
            # הוספת מצב השהיה וביטול
            state_data.update({
                "is_paused": getattr(self, 'is_paused', False),
                "is_cancelled": getattr(self, 'is_cancelled', False)
            })
            # שמירה באותה תיקיה כמו התוכנה
            script_dir = os.path.dirname(os.path.abspath(__file__))
            state_path = os.path.join(script_dir, STATE_FILE_NAME)
            with open(state_path, "w", encoding="utf-8") as f:
                json.dump(state_data, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"שגיאה בשמירת מצב: {e}")

    def load_state(self):
        """טעינת מצב התקדמות"""
        try:
            script_dir = os.path.dirname(os.path.abspath(__file__))
            state_path = os.path.join(script_dir, STATE_FILE_NAME)
            if os.path.exists(state_path):
                with open(state_path, "r", encoding="utf-8") as f:
                    state = json.load(f)
                    # בדיקת תקינות המצב
                    if "step" in state and 0 <= state["step"] <= 2:
                        return state
        except Exception as e:
            print(f"שגיאה בטעינת מצב: {e}")
        return {"step": 0}

    def clear_state(self):
        """מחיקת מצב התקדמות"""
        try:
            script_dir = os.path.dirname(os.path.abspath(__file__))
            state_path = os.path.join(script_dir, STATE_FILE_NAME)
            if os.path.exists(state_path):
                os.remove(state_path)
        except Exception as e:
            print(f"שגיאה במחיקת מצב: {e}")

    def load_and_set_state(self):
        """טעינת מצב והגדרת כפתורים בהתאם"""
        state = self.load_state()
        current_step = state.get("step", 0)
        
        # איפוס כל הכפתורים
        self.btn_load_manifests.setEnabled(False)
        self.btn_download_updates.setEnabled(False)
        self.btn_apply_updates.setEnabled(False)
        
        # הפעלת הכפתור הנכון לפי המצב
        if current_step == 0:
            self.btn_load_manifests.setEnabled(True)
            self.status_label.setText("מוכן לטעינת קבצי נתונים")
        elif current_step == 1:
            self.btn_download_updates.setEnabled(True)
            self.status_label.setText("מוכן להורדת עדכונים")
            self.log("אפשר להמשיך מההורדה")
        elif current_step == 2:
            self.btn_apply_updates.setEnabled(True)
            self.status_label.setText("מוכן להחלת עדכונים")
            self.log("אפשר להמשיך מההחלה")

    def reset_state(self):
        """איפוס מצב התקדמות"""
        reply = QMessageBox.question(self, "איפוס מצב", 
                                "האם אתה בטוח שברצונך לאפס את מצב ההתקדמות?",
                                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        
        if reply == QMessageBox.StandardButton.Yes:
            self.clear_state()
            self.load_and_set_state()
            self.log("מצב התקדמות אופס")

    def reset_data(self):
        """איפוס נתוני המצב השמורים"""
        reply = QMessageBox.question(self, "איפוס נתונים", 
                                "האם אתה בטוח שברצונך למחוק את כל הנתונים השמורים?",
                                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        
        if reply == QMessageBox.StandardButton.Yes:
            self.clear_state()
            self.load_and_set_state()
            self.log("נתוני המצב נמחקו")            

    def log(self, message):
        self.log_text.append(message)
        self.log_text.verticalScrollBar().setValue(self.log_text.verticalScrollBar().maximum())
    
    def load_manifests(self):
        if self.worker and self.worker.isRunning():
            return
            
        self.progress_bar.setVisible(True)
        self.progress_bar.setValue(0)
        self.btn_load_manifests.setEnabled(False)
        
        self.worker = WorkerThread("load_manifests")
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
            self.save_state({"step": 1})
            self.btn_download_updates.setEnabled(True)
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
        
        self.worker = WorkerThread("download_updates")
        self.worker.progress.connect(self.progress_bar.setValue)
        self.worker.status.connect(self.status_label.setText)
        self.worker.status.connect(self.log)
        self.worker.finished.connect(self.on_download_updates_finished)
        self.worker.start()
        self.btn_pause.setEnabled(True)
        self.btn_cancel.setEnabled(True)
        
    def on_download_updates_finished(self, success, message):
        self.progress_bar.setVisible(False)
        self.status_label.setText(message)
        self.log(message)
        self.reset_buttons()
        
        if success:
            self.save_state({"step": 2})
            self.btn_apply_updates.setEnabled(True)
            QMessageBox.information(self, "הצלחה", message)
        else:
            self.btn_download_updates.setEnabled(True)
            # שמירת מצב גם במקרה של שגיאה
            self.save_state({"step": 1, "error": message})
            QMessageBox.critical(self, "שגיאה", message)
    
    def apply_updates(self):
        if self.worker and self.worker.isRunning():
            return
            
        self.progress_bar.setVisible(True)
        self.progress_bar.setValue(0)
        self.btn_apply_updates.setEnabled(False)
        
        self.worker = WorkerThread("apply_updates")
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
            self.clear_state()  # מחיקת מצב אחרי השלמה
            # איפוס הכפתורים לתחילת המחזור
            self.btn_load_manifests.setEnabled(True)
            self.btn_download_updates.setEnabled(False)
            self.btn_apply_updates.setEnabled(False)
            QMessageBox.information(self, "הצלחה", message)
        else:
            self.btn_apply_updates.setEnabled(True)
            QMessageBox.critical(self, "שגיאה", message)

    def toggle_pause(self):
        if self.worker and self.worker.isRunning():
            self.is_paused = not self.is_paused
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
        self.is_paused = False
        self.is_cancelled = False            

    # פונקציה לטעינת אייקון ממחרוזת Base64
    def load_icon_from_base64(self, base64_string):
        pixmap = QPixmap()
        pixmap.loadFromData(base64.b64decode(base64_string))
        return QIcon(pixmap)

def main():
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
