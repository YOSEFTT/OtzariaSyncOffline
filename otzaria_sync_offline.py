import re
import json
import os
import base64
import shutil
import requests
import sys
import psutil
import gc
import urllib3
import concurrent.futures
import threading
import time
import random
import urllib.request
import platform
from pathlib import Path

# ייבוא ctypes רק ב-Windows
if sys.platform == 'win32':
    import ctypes
from PyQt6.QtWidgets import (QApplication, QMainWindow, QVBoxLayout, QHBoxLayout, QSpinBox,
                           QWidget, QPushButton, QLabel, QProgressBar, QTextEdit, QDialog,
                           QFileDialog, QMessageBox, QFrame, QSlider, QCheckBox,
                           QGroupBox, QGridLayout, QSpacerItem, QSizePolicy, QMenuBar,
                           QMenu, QStatusBar, QSplitter, QTabWidget, QScrollArea)
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QTimer, QPropertyAnimation, QEasingCurve, QRect, QParallelAnimationGroup, QSequentialAnimationGroup, pyqtProperty, QSettings, QPoint, QSize
from PyQt6.QtGui import (QFont, QPixmap, QPalette, QColor, QIcon, QKeySequence,
                        QClipboard, QAction, QShortcut, QPainter)
from PyQt6.QtWidgets import QGraphicsOpacityEffect
from urllib.parse import urljoin
from datetime import datetime
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

# ניסיון לייבא chardet עם fallback
try:
    import chardet
    HAS_CHARDET = True
except ImportError:
    HAS_CHARDET = False

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

def hebrew_question_dialog(parent, title, text, default_no=False):
    """דיאלוג שאלה עם כפתורים בעברית (כן/לא)"""
    msg_box = QMessageBox(parent)
    msg_box.setWindowTitle(title)
    msg_box.setText(text)
    msg_box.setIcon(QMessageBox.Icon.Question)
    
    # יצירת כפתורים בעברית
    btn_yes = msg_box.addButton("כן", QMessageBox.ButtonRole.YesRole)
    btn_no = msg_box.addButton("לא", QMessageBox.ButtonRole.NoRole)
    
    # הגדרת כפתור ברירת מחדל
    if default_no:
        msg_box.setDefaultButton(btn_no)
    else:
        msg_box.setDefaultButton(btn_yes)
    
    msg_box.exec()
    
    # החזרת True אם נלחץ "כן"
    return msg_box.clickedButton() == btn_yes

def hebrew_info_dialog(parent, title, text):
    """דיאלוג מידע עם כפתור אישור בעברית"""
    msg_box = QMessageBox(parent)
    msg_box.setWindowTitle(title)
    msg_box.setText(text)
    msg_box.setIcon(QMessageBox.Icon.Information)
    msg_box.addButton("אישור", QMessageBox.ButtonRole.AcceptRole)
    msg_box.exec()

def hebrew_warning_dialog(parent, title, text):
    """דיאלוג אזהרה עם כפתור אישור בעברית"""
    msg_box = QMessageBox(parent)
    msg_box.setWindowTitle(title)
    msg_box.setText(text)
    msg_box.setIcon(QMessageBox.Icon.Warning)
    msg_box.addButton("אישור", QMessageBox.ButtonRole.AcceptRole)
    msg_box.exec()

def hebrew_error_dialog(parent, title, text):
    """דיאלוג שגיאה עם כפתור אישור בעברית"""
    msg_box = QMessageBox(parent)
    msg_box.setWindowTitle(title)
    msg_box.setText(text)
    msg_box.setIcon(QMessageBox.Icon.Critical)
    msg_box.addButton("אישור", QMessageBox.ButtonRole.AcceptRole)
    msg_box.exec()

BASE_URL = "https://raw.githubusercontent.com/Y-PLONI/otzaria-library/refs/heads/main/"
BASE_PATH = "אוצריא"
LOCAL_PATH = ""
DEL_LIST_FILE_NAME = "del_list.txt"
MANIFEST_FILE_NAME = "files_manifest.json"
DICTA_MANIFEST_FILE_NAME = "files_manifest_dicta.json"
STATE_FILE_NAME = "sync_state.json"
COPIED_DICTA = False

# מזהה ייחודי לאפליקציה
myappid = 'MIT.LEARN_PYQT.OtzariaSyncoffline'

def get_platform_info():
    """קבלת מידע על הפלטפורמה הנוכחית"""
    return {
        'system': platform.system(),  # 'Windows', 'Linux', 'Darwin' (macOS)
        'machine': platform.machine(),  # 'x86_64', 'arm64', etc.
        'is_windows': sys.platform == 'win32',
        'is_linux': sys.platform.startswith('linux'),
        'is_macos': sys.platform == 'darwin',
        'is_apple_silicon': sys.platform == 'darwin' and platform.machine() == 'arm64'
    }

def get_app_data_dir():
    """קבלת תיקיית נתוני האפליקציה בהתאם לפלטפורמה"""
    platform_info = get_platform_info()
    
    if platform_info['is_windows']:
        # Windows: %APPDATA%
        app_data = os.getenv("APPDATA")
        if app_data:
            return safe_path_handling(app_data)
        return None
    elif platform_info['is_macos']:
        # macOS: ~/Library/Application Support
        return os.path.expanduser("~/Library/Application Support")
    else:
        # Linux: ~/.config או XDG_CONFIG_HOME
        xdg_config = os.getenv("XDG_CONFIG_HOME")
        if xdg_config:
            return xdg_config
        return os.path.expanduser("~/.config")

def get_otzaria_preferences_path():
    """קבלת נתיב קובץ ההעדפות של אוצריא בהתאם לפלטפורמה"""
    platform_info = get_platform_info()
    app_data = get_app_data_dir()
    
    if not app_data:
        return None
    
    if platform_info['is_windows']:
        return str(Path(app_data) / "com.example" / "otzaria" / "app_preferences.isar")
    elif platform_info['is_macos']:
        return str(Path(app_data) / "com.example.otzaria" / "app_preferences.isar")
    else:
        # Linux
        return str(Path(app_data) / "com.example.otzaria" / "app_preferences.isar")

def get_system_drives():
    """קבלת רשימת כוננים/נקודות עיגון בהתאם לפלטפורמה"""
    platform_info = get_platform_info()
    
    if platform_info['is_windows']:
        # Windows: כוננים A-Z
        drives = []
        for i in range(ord('A'), ord('Z') + 1):
            drive = f"{chr(i)}:\\"
            if os.path.exists(drive):
                drives.append(drive)
        return drives
    elif platform_info['is_macos']:
        # macOS: /Volumes + home directory
        drives = [os.path.expanduser("~")]
        volumes_path = "/Volumes"
        if os.path.exists(volumes_path):
            try:
                for volume in os.listdir(volumes_path):
                    volume_path = os.path.join(volumes_path, volume)
                    if os.path.isdir(volume_path):
                        drives.append(volume_path)
            except PermissionError:
                pass
        return drives
    else:
        # Linux: home directory + /media + /mnt
        drives = [os.path.expanduser("~")]
        
        # בדיקת /media (כוננים חיצוניים)
        media_path = f"/media/{os.getenv('USER', '')}"
        if os.path.exists(media_path):
            try:
                for mount in os.listdir(media_path):
                    mount_path = os.path.join(media_path, mount)
                    if os.path.isdir(mount_path):
                        drives.append(mount_path)
            except PermissionError:
                pass
        
        # בדיקת /mnt
        mnt_path = "/mnt"
        if os.path.exists(mnt_path):
            try:
                for mount in os.listdir(mnt_path):
                    mount_path = os.path.join(mnt_path, mount)
                    if os.path.isdir(mount_path):
                        drives.append(mount_path)
            except PermissionError:
                pass
        
        return drives

def get_default_font_family():
    """קבלת גופן ברירת מחדל בהתאם לפלטפורמה"""
    platform_info = get_platform_info()
    
    if platform_info['is_windows']:
        return "Segoe UI"
    elif platform_info['is_macos']:
        return "Helvetica Neue"  # או "SF Pro Text"
    else:
        # Linux
        return "DejaVu Sans"  # או "Noto Sans"

def normalize_path_for_platform(path_str):
    """נרמול נתיב בהתאם לפלטפורמה"""
    if not path_str:
        return path_str
    
    platform_info = get_platform_info()
    
    if platform_info['is_windows']:
        # המרה ל-backslash
        return path_str.replace("/", "\\")
    else:
        # המרה ל-forward slash
        return path_str.replace("\\", "/")

# מחרוזת Base64 של האייקון
icon_base64 = "iVBORw0KGgoAAAANSUhEUgAAAE4AAABTCAYAAAAx4jFYAAAACXBIWXMAAAsTAAALEwEAmpwYAAAMrUlEQVR4nO2cbUwU1xrHnzk7uzis4Eb0UtxLXdSiAWu1KfUioLEfuEXixYYmJlCbaG6x4ocmNn6o1XBjE9GUxNCoFw0aaXJN/YCsNqK1CmxIJLzEXlBseBEWLq8Cru7KyrKz89wPOnRfZnZndpddsfyTk8yceeY5Z35z3ubMmQFEhLkS/BEiFiEiUhSF6K+TP3zNBBKIo9ddiFgEAP8ihPgNXkxvLLjZhAbwhoKbbWgAbyC4UEADAKBnzXMYJAUaIloAYAQABgDgIQBcBYA6iqKm5SY2Z4IvaHzvCQCSAiEEGxsbERHNiHgaEd+SyirsMIIJTg4095CXl4eI+BwRjyJixDw4mcFgMCAiNgiVPue8vFGdA8dxQFFUQD62bNkC+fn5fwOAZkRcJ2ZH+bqT3lRdXZ3Z1NSU0dHRkTgyMrLYarUuCMRfoDp58qQyLS1to1jncOHCBTh16hT89ttvPkuwVquFgYGBAQBIoShqBABcz/Gnyly4cGFPSkpKPcMwXTRNI03TSAh5LUJVVVUvonAngYh4+PDhzrq6usGJiQnWaDR67UxetXsNfJvndxvX2tq6IjU11UDT9KNwwdq9e3cPH+TCQ8QZG4Zh2LKysk6TyeQ4c+aMrzbvqN/gKisrd8TFxd3nS1g4wKWnp4/abDbUaDRos9mwqqqqVw48Z3CEEKRpGleuXPm8ra3NNDY2JgrvVW8bJxvctWvXtjlDC1c1NBgMg9nZ2QgAM7MdcuC5g+ODSqVy1NTUDIjB27lzJyLiGVngfv/992U8tHABI4RgbGys1Wq1cs4XxMMrLCzslgJPDBwPr62tzSRWbRHxKSKqJIPLzMy8EW5ohBAsLi7uuHbtmscFMQzjFRwPjw/e7BISEp6bTCaHUIfx6gnj75LAVVVV/YOm6UfhhkYIwTt37gwIXVBnZ6dPcHJCWVlZp9FoFHw8w5ePZb7BZWVlXX8dShshBHt6eqxCVWh8fJxVq9X2YKXDMAz75MkTVqS61vJsRGdHWlpakpqamlZwHOcSn5iYCOvXr3eJQ0RoamqCvr4+MXcAAEDTNOzduxe2bt0KCxcu9GrrLq1Wq3KPI4TA9PT00E8//RTf3NwMP/zwA5jNZkn+cnJyICLC9ZF0fHwcampqFK2trUMURS1Dz0Fy3MyWWGkrLy//p0ql8rgjR44cwampKZcwOTmJ+/fv93Un8eTJkzgyMoITExOyA8dxHiUgOzsbLRZL58TEBD5+/Birq6sxJibGZ6mKiYnBoaEhj+uor69HlUqF33zzTWdycrJQiTPzfESfVbu7u1e7lzYAAIVCASqVyiUolUpQKBRe73BGRgbk5+eDUqn0aidHX331FbAsu4jPV0pKCuTk5Pg8jxACSqUSlEqlyzXQNA0KhQLu378fuX//fqFTZ2qoKLjR0dG/+HEtolq1apVPuHLV3d0NFEXZ+X1CCKSkpATs9+nTp8pVq1Z5tRFt42w2m0ebEkwhIoyMjIDNZpNkr9FoEABcpj5Onz4N+fn5Vuc4mg58UjstLe1ZaWmp14IjmorD4SBCVTVYYlkWjh07Br/88osk+/b2dhYAXOr5w4cPgRCiDnbetm7duuD7778XOjTBb4T8nYPzfJnNZgOTySTpvGfPntnADRwiAsMwsXa73QEAQWkHIiMj2Q8++GCZSKEZ5DfmzETm8PCwmRDP7A4MDCgWLFjQw+8HOpGZl5fX9+TJE4+b8MpvI78/Z95y3bhxY7KhoQE2btzoEp+QkAAOh2OlzWabRETRaltZWWnktwsKCnTe0nrvvfc84q5evQoAUM/vhxRcIKXh7Nmzy4uKijw6CESEsrIy8sUXX9gtFgsHIrVox44dOkIIcBwHCoXCCAA6sbSsVisQt1nk7du3PwOA6/z+nKmqZrNZ1dzcPLxz506PY4WFhfD06VONWq0epihKtEdDRCCEwPbt23VqtdooZFNeXr5Sr9cbnd9fZGdnAwBcAoAXvJ0ouEDbCiEJPMLI0sGDB5UVFRWCx5YuXQpms1mbnZ1tXr58+aS3PBBCgGEYHUVRRiGb3NxcnV6vN05NTYFGowG9Xs8BwDFnmzlT4gAAWlpalt66davPYDAIHl+6dClcuXJFc+/ePeb06dNdERERDiE7Hh5FUToAMArZ5Obm6r788sveTz75pPf48eM3KYoacD4+p8ABAOzevfut+Ph4a15enuDxwsJCWLx4McnKynpnYGAAampqhg4dOtTlbicFXkVFRUJFRUXC9evXPWYkwtarKpVKKC4uhqNHj8o9NcJut49XVFREGAwGxeDgoIcBIoJOpwMAUFAUtWzDhg2wYsUKQbtXHYYOXsLTSc1EyMA5HJ61ZsmSJf66W2K1Wvv6+/v/umvXLsWlS5dEDRER7t27B3v27BE9zsNLSEgwgkR4IauqXV1dYLPZZjqIQDsfh8Ox3GKxmH788UerWJsnVTw8ORK1DrQHdFddXR2cP38e7Ha7Xy/BhYLD4VhiNpsVGzdu7OM4DsTavdlQSNu47777DhobGyEzMxOio6OD5TbCbrcv7+rqGt+7d+/0+fPn49ra2qjU1FSQOklBURRwHAejo6OSEw0pOJZlobq6Gqqrq2fD/ZKSkhKIjo6eLigo6KupqVHHxcVFL1q0aIFGo1FERERQQs0DDw0Rjb29vTqpic2ZZ1WpMpvNqpKSkndKSkpc4oU6J2doiKiTk86cG8cFS87QQMYwhNefElyg0ADCUFW3bdsGy5YtC7pfi8UCly9f9mnHQ3vx4oUxIiJC5++wKOTgDhw4AJs3bw663/7+fp/geGg///yzMTU1Vef+XlWOwjJ1LnewKdWvN+n1euOVK1dAr9dDQUGB7uHDh7L8u49r37heVUy5ubk6fjsmJiZgf3/KziEYCnmJQ8SgrA4Pt0IO7tSpU/yLj6DKYrEE3ac3hRycXq8PdZKzovk2zk/Ng/NT8+D8VMjbuPLycv59QFA1OjoK+fn5QfcrppCC49evJSUlBX044msZbbAVlqo618dwAPNtnN+aB+enQt45DA8Py16qL0VDQ0NB9+lNIQXHcRx8/PHHszKtFGr5BQ4RA2rgZ3Ntcagk+9Y7HI4/Pj2EPyb4GIYJbs5mUa8W23jEv3rJLc2H2AGxEjU+Pi6YkS1btsyZKpieng6RkZEe8c+ePQOWZSX5kL0Eoqenx+Wu8FPhmzdvlvRVS7iVkJAA3377LahUnp9x3L9/X/AcoUIk2sYplUpB9C0tLTA6Ojrzpop3yjAMnDt3DuLj4+HWrVvw4sULodMFZbVaYWxsTLI9wMtFhEKlRkwKhQJWr14NR44cgXXr1gFFUS5AHA4H3L17V+xcj0ZZFFxUVNRzoXiTyQSlpaVQXFzs8YmRRqOBkpISmJqagunpackLdwwGA3z66aeSbHldvHgRPvzwQ8n2CoUCGIYBhULhAozP44MHD+DXX38VPDcqKsrqHicKLjY29jHfZrn3ghcvXoTPP/8c1q5dOxPnnBmGYWR1Fmq1ml+jJsmeEAJRUVGg0Wgkp+Es96o3OTkJBw8eFK0lb7/9tscgUbSNS0pKahVr7E0mE3z22Wfw6NEj/o24R6b4qiAl+CN+SCQ3DX6bHxlMTk5CUVER1NbWiqaVlJTU7h4nCu7999+viY2NbRMrBe3t7VBYWAhtbW0uwxPnzElRsNfhiUnoJo2NjcGJEyegtLTUw54vNAsXLuzctGnTLQ8Dbwv39u3bd9bXp+VqtRqPHz+OIyMjOD09jSzLIsuy6HA4JAWWZfHmzZuyfstB0zTW19dLTsM5LbvdjmazGW/fvo1JSUle06BpGnNycq4KsfH6b6Wmpqa1GRkZVSzLev94E172cpmZmfDRRx9BYmIiKJVKySWvoaEBDhw4IOuJ4ty5c4KfDokJEWF4eBju3r0L1dXV0NHR4XPMRtN0t16v35eVlXVb0KG3cOjQoRMqlapL7k8NnP+I4yv4++MBOWnITUelUuGuXbv+I8ZF0lrb9PT02nD+GigcYc2aNc39/f2RAYHr7e2NTktLq1WpVG80OL5gJCcnN7a0tKzxxkTyCu/+/v7IjIyMO3y1fVMA8tdB0zSqVKqud999t7G1tXWFLx6yl8gfO3bssHObN9cBOjVBj77++uuTUjn49cfC9vb2ty9fvry3srIys7u7W8NxnM9e93UUIQS0Wu1/c3Nz6/Ly8v69YcOGTqnnBvSrRwCA2traTR0dHesHBwfjnz9/vpDjOMKyrMujHEVRnNj8FyIS9zjBjAYwcUoI4fg8UBTFMQwzpdVq/5eYmPggOTn5rlarnZLrM2Bwf1bNjZnH11Dz4PzUPDg/NQ/OT/0fMGYuV8QJHfwAAAAASUVORK5CYII="

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
        
        # ניקוי רק אם באמת נדרש (זיכרון גבוה או זמן רב)
        return (memory_usage > self.memory_threshold or 
                current_time - self.last_cleanup > self.cleanup_interval * 2)  # הכפלת הזמן
    
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

class AnimationManager:
    """מנהל אנימציות מרכזי לכל האפליקציה"""
    
    def __init__(self):
        self.animations = {}  # מילון לשמירת אנימציות פעילות
        self.animation_groups = {}  # מילון לשמירת קבוצות אנימציות
        self.animation_cache = {}  # cache לאנימציות שנוצרו
        self.max_concurrent_animations = 10  # הגבלת מספר אנימציות בו-זמניות
        
    def create_fade_animation(self, widget, duration=300, start_opacity=0, end_opacity=1):
        """יצירת אנימציית fade in/out"""
        try:
            # בדיקה אם יש כבר אנימציה פעילה לווידג'ט זה
            widget_id = id(widget)
            if widget_id in self.animations:
                self.animations[widget_id].stop()
            
            # יצירת אנימציה חדשה
            animation = QPropertyAnimation(widget, b"windowOpacity")
            animation.setDuration(duration)
            animation.setStartValue(start_opacity)
            animation.setEndValue(end_opacity)
            animation.setEasingCurve(QEasingCurve.Type.OutCubic)
            
            # שמירה במילון האנימציות
            self.animations[widget_id] = animation
            
            # ניקוי האנימציה כשהיא מסתיימת
            animation.finished.connect(lambda: self._cleanup_animation(widget_id))
            
            return animation
            
        except Exception as e:
            print(f"שגיאה ביצירת אנימציית fade: {e}")
            return None
    
    def create_slide_animation(self, widget, duration=300, start_pos=None, end_pos=None):
        """יצירת אנימציית slide"""
        try:
            widget_id = id(widget)
            if widget_id in self.animations:
                self.animations[widget_id].stop()
            
            # קביעת מיקומים ברירת מחדל
            if start_pos is None:
                start_pos = widget.pos()
            if end_pos is None:
                end_pos = widget.pos()
            
            animation = QPropertyAnimation(widget, b"pos")
            animation.setDuration(duration)
            animation.setStartValue(start_pos)
            animation.setEndValue(end_pos)
            animation.setEasingCurve(QEasingCurve.Type.OutCubic)
            
            self.animations[widget_id] = animation
            animation.finished.connect(lambda: self._cleanup_animation(widget_id))
            
            return animation
            
        except Exception as e:
            print(f"שגיאה ביצירת אנימציית slide: {e}")
            return None
    
    def create_scale_animation(self, widget, duration=200, start_scale=1.0, end_scale=1.05):
        """יצירת אנימציית scale (הגדלה/הקטנה)"""
        try:
            widget_id = id(widget)
            if widget_id in self.animations:
                self.animations[widget_id].stop()
            
            # יצירת אנימציה לגודל
            animation = QPropertyAnimation(widget, b"geometry")
            animation.setDuration(duration)
            
            # חישוב גיאומטריה חדשה
            current_rect = widget.geometry()
            center = current_rect.center()
            
            # גיאומטריה התחלתית
            start_width = int(current_rect.width() * start_scale)
            start_height = int(current_rect.height() * start_scale)
            start_rect = QRect(
                center.x() - start_width // 2,
                center.y() - start_height // 2,
                start_width,
                start_height
            )
            
            # גיאומטריה סופית
            end_width = int(current_rect.width() * end_scale)
            end_height = int(current_rect.height() * end_scale)
            end_rect = QRect(
                center.x() - end_width // 2,
                center.y() - end_height // 2,
                end_width,
                end_height
            )
            
            animation.setStartValue(start_rect)
            animation.setEndValue(end_rect)
            animation.setEasingCurve(QEasingCurve.Type.OutCubic)
            
            self.animations[widget_id] = animation
            animation.finished.connect(lambda: self._cleanup_animation(widget_id))
            
            return animation
            
        except Exception as e:
            print(f"שגיאה ביצירת אנימציית scale: {e}")
            return None
    
    def create_progress_animation(self, progress_bar, start_value, end_value, duration=1000):
        """יצירת אנימציה למד התקדמות"""
        try:
            widget_id = id(progress_bar)
            if widget_id in self.animations:
                self.animations[widget_id].stop()
            
            animation = QPropertyAnimation(progress_bar, b"value")
            animation.setDuration(duration)
            animation.setStartValue(start_value)
            animation.setEndValue(end_value)
            animation.setEasingCurve(QEasingCurve.Type.OutCubic)
            
            self.animations[widget_id] = animation
            animation.finished.connect(lambda: self._cleanup_animation(widget_id))
            
            return animation
            
        except Exception as e:
            print(f"שגיאה ביצירת אנימציית progress: {e}")
            return None
    
    def animate_button_click(self, button):
        """אנימציה ללחיצה על כפתור"""
        try:
            # אנימציה קצרה של הקטנה והגדלה
            scale_down = self.create_scale_animation(button, duration=100, start_scale=1.0, end_scale=0.95)
            scale_up = self.create_scale_animation(button, duration=100, start_scale=0.95, end_scale=1.0)
            
            if scale_down and scale_up:
                # יצירת רצף אנימציות
                group = QSequentialAnimationGroup()
                group.addAnimation(scale_down)
                group.addAnimation(scale_up)
                
                widget_id = id(button)
                self.animation_groups[widget_id] = group
                group.finished.connect(lambda: self._cleanup_animation_group(widget_id))
                
                group.start()
                return group
            
        except Exception as e:
            print(f"שגיאה באנימציית לחיצת כפתור: {e}")
            return None
    
    def animate_tab_transition(self, tab_widget, from_index, to_index):
        """אנימציה למעבר בין טאבים"""
        try:
            # אנימציה פשוטה של fade out ו fade in
            current_widget = tab_widget.widget(from_index)
            new_widget = tab_widget.widget(to_index)
            
            if current_widget and new_widget:
                fade_out = self.create_fade_animation(current_widget, duration=150, start_opacity=1, end_opacity=0)
                fade_in = self.create_fade_animation(new_widget, duration=150, start_opacity=0, end_opacity=1)
                
                if fade_out and fade_in:
                    group = QSequentialAnimationGroup()
                    group.addAnimation(fade_out)
                    group.addAnimation(fade_in)
                    
                    widget_id = id(tab_widget)
                    self.animation_groups[widget_id] = group
                    group.finished.connect(lambda: self._cleanup_animation_group(widget_id))
                    
                    group.start()
                    return group
            
        except Exception as e:
            print(f"שגיאה באנימציית מעבר טאבים: {e}")
            return None
    
    def stop_all_animations(self):
        """עצירת כל האנימציות הפעילות"""
        try:
            # עצירת אנימציות יחידות
            for animation in self.animations.values():
                if animation:
                    animation.stop()
            
            # עצירת קבוצות אנימציות
            for group in self.animation_groups.values():
                if group:
                    group.stop()
            
            # ניקוי המילונים
            self.animations.clear()
            self.animation_groups.clear()
            
        except Exception as e:
            print(f"שגיאה בעצירת אנימציות: {e}")
    
    def _cleanup_animation(self, widget_id):
        """ניקוי אנימציה שהסתיימה"""
        try:
            if widget_id in self.animations:
                del self.animations[widget_id]
        except Exception as e:
            print(f"שגיאה בניקוי אנימציה: {e}")
    
    def _cleanup_animation_group(self, widget_id):
        """ניקוי קבוצת אנימציות שהסתיימה"""
        try:
            if widget_id in self.animation_groups:
                del self.animation_groups[widget_id]
        except Exception as e:
            print(f"שגיאה בניקוי קבוצת אנימציות: {e}")
    
    def get_active_animations_count(self):
        """קבלת מספר האנימציות הפעילות"""
        return len(self.animations) + len(self.animation_groups)
    
    def is_animation_running(self, widget):
        """בדיקה האם יש אנימציה פעילה לווידג'ט"""
        widget_id = id(widget)
        return widget_id in self.animations or widget_id in self.animation_groups

class IconManager:
    """מנהל אייקונים לאפליקציה"""
    
    def __init__(self):
        self.icon_cache = {}  # cache לאייקונים שנטענו
        self.icon_theme = "default"
        self.icon_size = 16
        
        # מיפוי שמות אייקונים לסמלים טקסטואליים
        self.text_icons = {
            'play': '▶️',
            'pause': '⏸️',
            'stop': '⏹️',
            'folder': '📁',
            'settings': '⚙️',
            'download': '⬇️',
            'upload': '⬆️',
            'refresh': '🔄',
            'sync': '🔄',
            'check': '✅',
            'error': '❌',
            'warning': '⚠️',
            'info': 'ℹ️',
            'help': '❓',
            'close': '✖️',
            'minimize': '➖',
            'maximize': '⬜',
            'home': '🏠',
            'search': '🔍',
            'edit': '✏️',
            'delete': '🗑️',
            'add': '➕',
            'remove': '➖',
            'save': '💾',
            'open': '📂',
            'new': '📄',
            'copy': '📋',
            'cut': '✂️',
            'paste': '📋',
            'undo': '↶',
            'redo': '↷',
            'zoom_in': '🔍➕',
            'zoom_out': '🔍➖',
            'fullscreen': '⛶',
            'exit_fullscreen': '⛶',
            'menu': '☰',
            'more': '⋯',
            'up': '⬆️',
            'down': '⬇️',
            'left': '⬅️',
            'right': '➡️',
            'back': '⬅️',
            'forward': '➡️',
            'first': '⏮️',
            'last': '⏭️',
            'previous': '⏪',
            'next': '⏩'
        }
        
        # מיפוי לאייקונים של PyQt6
        self.qt_icons = {
            'folder': QApplication.style().standardIcon(QApplication.style().StandardPixmap.SP_DirIcon),
            'file': QApplication.style().standardIcon(QApplication.style().StandardPixmap.SP_FileIcon),
            'help': QApplication.style().standardIcon(QApplication.style().StandardPixmap.SP_MessageBoxQuestion),
            'info': QApplication.style().standardIcon(QApplication.style().StandardPixmap.SP_MessageBoxInformation),
            'warning': QApplication.style().standardIcon(QApplication.style().StandardPixmap.SP_MessageBoxWarning),
            'error': QApplication.style().standardIcon(QApplication.style().StandardPixmap.SP_MessageBoxCritical),
            'refresh': QApplication.style().standardIcon(QApplication.style().StandardPixmap.SP_BrowserReload),
            'close': QApplication.style().standardIcon(QApplication.style().StandardPixmap.SP_DialogCloseButton),
            'save': QApplication.style().standardIcon(QApplication.style().StandardPixmap.SP_DialogSaveButton),
            'open': QApplication.style().standardIcon(QApplication.style().StandardPixmap.SP_DialogOpenButton),
            'apply': QApplication.style().standardIcon(QApplication.style().StandardPixmap.SP_DialogApplyButton),
            'cancel': QApplication.style().standardIcon(QApplication.style().StandardPixmap.SP_DialogCancelButton),
            'ok': QApplication.style().standardIcon(QApplication.style().StandardPixmap.SP_DialogOkButton),
            'up': QApplication.style().standardIcon(QApplication.style().StandardPixmap.SP_ArrowUp),
            'down': QApplication.style().standardIcon(QApplication.style().StandardPixmap.SP_ArrowDown),
            'left': QApplication.style().standardIcon(QApplication.style().StandardPixmap.SP_ArrowLeft),
            'right': QApplication.style().standardIcon(QApplication.style().StandardPixmap.SP_ArrowRight),
            'back': QApplication.style().standardIcon(QApplication.style().StandardPixmap.SP_ArrowBack),
            'forward': QApplication.style().standardIcon(QApplication.style().StandardPixmap.SP_ArrowForward)
        }
    
    def get_icon(self, icon_name, size=None, color=None, theme="light"):
        """קבלת אייקון לפי שם עם תמיכה בערכות נושא"""
        try:
            if size is None:
                size = self.icon_size
            
            # התאמת צבע לערכת נושא אם לא צוין צבע ספציפי
            if color is None:
                color = "#FFFFFF" if theme == "dark" else "#333333"
            
            # בדיקה ב-cache
            cache_key = f"{icon_name}_{size}_{color}_{theme}"
            if cache_key in self.icon_cache:
                return self.icon_cache[cache_key]
            
            icon = None
            
            # ניסיון לטעון אייקון מערכת של PyQt6
            if icon_name in self.qt_icons:
                icon = self.qt_icons[icon_name]
            
            # אם לא נמצא, יצירת אייקון טקסטואלי
            if not icon or icon.isNull():
                if icon_name in self.text_icons:
                    icon = self.create_icon_from_text(
                        self.text_icons[icon_name], 
                        color, 
                        size
                    )
                else:
                    # fallback לטקסט פשוט
                    fallback_color = "#CCCCCC" if theme == "dark" else "#666666"
                    icon = self.create_icon_from_text(
                        icon_name[:2].upper(), 
                        fallback_color, 
                        size
                    )
            
            # שמירה ב-cache
            if icon:
                self.icon_cache[cache_key] = icon
            
            return icon
            
        except Exception as e:
            print(f"שגיאה בטעינת אייקון {icon_name}: {e}")
            # fallback לאייקון ברירת מחדל
            fallback_color = "#999999" if theme == "light" else "#CCCCCC"
            return self.create_icon_from_text("?", fallback_color, size or 16)
    
    def create_icon_from_text(self, text, color="#333333", size=16):
        """יצירת אייקון מטקסט"""
        try:
            
            # יצירת pixmap
            pixmap = QPixmap(size, size)
            pixmap.fill(QColor(0, 0, 0, 0))  # רקע שקוף
            
            # יצירת painter
            painter = QPainter(pixmap)
            painter.setRenderHint(QPainter.RenderHint.Antialiasing)
            
            # הגדרת גופן
            font = QFont()
            font.setPixelSize(int(size * 0.7))  # 70% מגודל האייקון
            font.setBold(True)
            painter.setFont(font)
            
            # הגדרת צבע
            painter.setPen(QColor(color))
            
            # ציור הטקסט במרכז
            painter.drawText(pixmap.rect(), Qt.AlignmentFlag.AlignCenter, text)
            
            painter.end()
            
            return QIcon(pixmap)
            
        except Exception as e:
            print(f"שגיאה ביצירת אייקון מטקסט: {e}")
            return QIcon()  # אייקון ריק
    
    def load_system_icon(self, icon_name):
        """טעינת אייקון מערכת"""
        try:
            if icon_name in self.qt_icons:
                return self.qt_icons[icon_name]
            return QIcon()
        except Exception as e:
            print(f"שגיאה בטעינת אייקון מערכת: {e}")
            return QIcon()
    
    def cache_icon(self, name, icon):
        """שמירת אייקון ב-cache"""
        try:
            if icon and not icon.isNull():
                self.icon_cache[name] = icon
                return True
            return False
        except Exception as e:
            print(f"שגיאה בשמירת אייקון ב-cache: {e}")
            return False
    
    def clear_cache(self):
        """ניקוי cache האייקונים"""
        try:
            self.icon_cache.clear()
            return True
        except Exception as e:
            print(f"שגיאה בניקוי cache: {e}")
            return False
    
    def set_icon_size(self, size):
        """הגדרת גודל אייקון ברירת מחדל"""
        try:
            if 8 <= size <= 128:  # הגבלת טווח סביר
                self.icon_size = size
                # ניקוי cache כדי שהאייקונים ייטענו בגודל החדש
                self.clear_cache()
                return True
            return False
        except Exception as e:
            print(f"שגיאה בהגדרת גודל אייקון: {e}")
            return False
    
    def get_available_icons(self):
        """קבלת רשימת אייקונים זמינים"""
        try:
            available = set()
            available.update(self.text_icons.keys())
            available.update(self.qt_icons.keys())
            return sorted(list(available))
        except Exception as e:
            print(f"שגיאה בקבלת רשימת אייקונים: {e}")
            return []
    
    def create_button_with_icon(self, text, icon_name, parent=None, theme="light"):
        """יצירת כפתור עם אייקון"""
        try:
            button = QPushButton(text, parent)
            icon = self.get_icon(icon_name, theme=theme)
            if icon and not icon.isNull():
                button.setIcon(icon)
                button.setIconSize(QSize(self.icon_size, self.icon_size))
            return button
        except Exception as e:
            print(f"שגיאה ביצירת כפתור עם אייקון: {e}")
            return QPushButton(text, parent)
    
    def update_icons_for_theme(self, theme="light"):
        """עדכון כל האייקונים בcache לערכת נושא חדשה"""
        try:
            # ניקוי cache כדי לאלץ יצירה מחדש עם הצבעים החדשים
            old_cache = self.icon_cache.copy()
            self.icon_cache.clear()
            
            # יצירה מחדש של אייקונים נפוצים עם הצבעים החדשים
            common_icons = ['play', 'pause', 'stop', 'folder', 'settings', 'download', 'sync', 'refresh']
            for icon_name in common_icons:
                self.get_icon(icon_name, theme=theme)
            
            return True
        except Exception as e:
            print(f"שגיאה בעדכון אייקונים לערכת נושא: {e}")
            return False

class WorkerThread(QThread):
    progress = pyqtSignal(int)
    status = pyqtSignal(str)
    finished = pyqtSignal(bool, str)
    manual_selection = pyqtSignal()
    download_progress = pyqtSignal(str, int, float, int, int)  # שם קובץ, אחוז, מהירות, קבצים שהושלמו, סה"כ קבצים
    memory_info = pyqtSignal(dict)  # מידע על זיכרון
    stats_update = pyqtSignal(dict)  # עדכון סטטיסטיקות
    
    def __init__(self, task_type, *args):
        super().__init__()
        self.task_type = task_type
        self.stop_search = False  # דגל לעצירת חיפוש
        self.is_paused = False  # דגל להשהיה
        self.manual_selected = False  # דגל לבחירה ידנית
        self.pause_message_sent = False  # דגל למניעת הודעות השהיה חוזרות
        self.args = args
        self.session = requests.Session()  # שימוש ב session לחיבורים מתמשכים
        
        # אתחול מחלקות עזר
        self.speed_monitor = NetworkSpeedMonitor()
        self.retry_handler = RetryHandler()
        self.memory_manager = MemoryManager()
        
        # הגדרות session משופרות
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'application/json, text/plain, */*',
            'Accept-Language': 'he-IL,he;q=0.9,en-US;q=0.8,en;q=0.7',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
            'Cache-Control': 'no-cache',
            'Pragma': 'no-cache',
            'Sec-Ch-Ua': '"Not_A Brand";v="8", "Chromium";v="120", "Google Chrome";v="120"',
            'Sec-Ch-Ua-Mobile': '?0',
            'Sec-Ch-Ua-Platform': '"Windows"',
            'Sec-Fetch-Dest': 'empty',
            'Sec-Fetch-Mode': 'cors',
            'Sec-Fetch-Site': 'cross-site'
        })
        
        # הגדרת proxy מהמערכת
        try:
            import urllib.request
            proxy_handler = urllib.request.ProxyHandler()
            proxy_dict = proxy_handler.proxies
            if proxy_dict:
                self.session.proxies.update(proxy_dict)
        except:
            pass
        
        # הגדרת SSL - פחות מחמיר
        urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
        self.session.verify = False  # זהירות: פחות בטוח אבל עוזר עם בעיות SSL
        
        # הגדרת timeout וretries        
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
        
        try:
            self.stop_search = False
            
            def validate_otzaria_folder(path):
                """בדיקה שהתיקיה מכילה את כל הקבצים והתיקיות הנדרשות"""
                try:
                    # טיפול בטוח בנתיב
                    safe_path = safe_path_handling(path)
                    self.status.emit(f"🔍 בודק תיקיה: {safe_path}")
                    
                    if not safe_path or not Path(safe_path).exists():
                        self.status.emit(f"❌ הנתיב לא קיים: {safe_path}")
                        return False
                    
                    # רשימת קבצים ותיקיות בנתיב
                    try:
                        items = list(Path(safe_path).iterdir())
                        item_names = [item.name for item in items]
                        self.status.emit(f"📋 קבצים ותיקיות בנתיב: {item_names}")
                    except Exception as e:
                        self.status.emit(f"❌ שגיאה ברישום תוכן: {e}")
                    
                    required_items = {
                        "אוצריא": "folder",
                        "links": "folder",
                        MANIFEST_FILE_NAME: "file"
                    }
                    
                    missing_items = []
                    for item, item_type in required_items.items():
                        # שימוש ב-pathlib לטיפול נכון בנתיבים
                        item_path = Path(safe_path) / item
                        
                        if item_type == "folder":
                            if not item_path.is_dir():
                                missing_items.append(f"תיקיה: {item}")
                            else:
                                self.status.emit(f"✅ נמצאה תיקיה: {item}")
                        elif item_type == "file":
                            if not item_path.is_file():
                                missing_items.append(f"קובץ: {item}")
                            else:
                                self.status.emit(f"✅ נמצא קובץ: {item}")
                    
                    if missing_items:
                        self.status.emit(f"❌ חסרים: {', '.join(missing_items)}")
                        return False
                    
                    self.status.emit("✅ כל הקבצים והתיקיות הנדרשים נמצאו")
                    return True
                    
                except Exception as e:
                    # במקרה של שגיאה, נחזור False
                    self.status.emit(f"❌ שגיאה בבדיקת תיקיה: {e}")
                    return False
            
            # שלב 1: חיפוש במיקום ברירת מחדל (תלוי פלטפורמה)
            platform_info = get_platform_info()
            
            if platform_info['is_windows']:
                self.status.emit("מחפש בכונן C...")
                default_path = safe_path_handling("C:\\אוצריא")
            elif platform_info['is_macos']:
                self.status.emit("מחפש בתיקיית הבית...")
                default_path = os.path.expanduser("~/אוצריא")
            else:
                self.status.emit("מחפש בתיקיית הבית...")
                default_path = os.path.expanduser("~/אוצריא")
            
            self.progress.emit(10)
            
            if default_path and Path(default_path).exists() and validate_otzaria_folder(default_path):
                LOCAL_PATH = default_path
                self.status.emit(f"נמצאה תיקיית אוצריא: {LOCAL_PATH}")
                self.copy_manifests_and_finish()
                return
            
            if self.stop_search:
                return
            
            # שלב 2: חיפוש בקובץ העדפות
            self.status.emit("לא נמצא במיקום ברירת מחדל, מחפש בקובץ ההגדרות של תוכנת אוצריא...")
            self.progress.emit(20)
            
            try:
                # שימוש בפונקציה cross-platform לקבלת נתיב נתוני האפליקציה
                APP_DATA = get_app_data_dir()
                self.status.emit(f"🔍 תיקיית נתוני אפליקציה: {APP_DATA}")
                
                if APP_DATA:
                    self.status.emit("✅ משתמש בטיפול משופר בנתיבים")
                    
                    # קבלת נתיב קובץ ההעדפות בהתאם לפלטפורמה
                    FILE_PATH = get_otzaria_preferences_path()
                    self.status.emit(f"🎯 נתיב קובץ העדפות מלא: {FILE_PATH}")
                    
                    # בדיקת קיום הקובץ
                    file_exists = os.path.exists(FILE_PATH)
                    path_exists = Path(FILE_PATH).exists()
                    self.status.emit(f"📄 קובץ קיים (os.path.exists): {file_exists}")
                    self.status.emit(f"📄 קובץ קיים (Path.exists): {path_exists}")
                    
                    if file_exists or path_exists:
                        # מידע על הקובץ
                        try:
                            file_path_obj = Path(FILE_PATH)
                            file_size = file_path_obj.stat().st_size
                            self.status.emit(f"📊 גודל קובץ: {file_size} בייטים")
                            
                            # בדיקת הרשאות
                            readable = os.access(FILE_PATH, os.R_OK)
                            self.status.emit(f"🔐 הרשאת קריאה: {readable}")
                        except Exception as e:
                            self.status.emit(f"❌ שגיאה בקבלת מידע על הקובץ: {e}")
                        
                        self.status.emit("✅ נמצא קובץ העדפות, מנסה לקרוא...")
                        try:
                            self.status.emit("📖 קורא קובץ העדפות בינארי (ISAR database)...")
                            
                            # קריאה בינארית של הקובץ כמו שהוצע
                            with open(FILE_PATH, "rb") as f:
                                content = f.read().decode("utf-8", errors="ignore")
                            
                            self.status.emit(f"✅ קרא {len(content)} תווים מהקובץ הבינארי")
                            
                            # חיפוש הנתיב עם הביטוי הרגולרי שעובד
                            self.status.emit("🔍 מחפש נתיב ספרייה בתוכן הקובץ...")
                            pattern = re.compile(r'key-library-path.*?"([^"]+)"', re.DOTALL | re.UNICODE)
                            m = pattern.search(content)
                            
                            if m:
                                raw_path = m.group(1)
                                self.status.emit(f"✅ נמצא נתיב גולמי: {raw_path}")
                                
                                # המרת נתיב לפורמט הפלטפורמה הנוכחית
                                preferences_path = normalize_path_for_platform(raw_path)
                                preferences_path = safe_path_handling(preferences_path)
                                self.status.emit(f"🛠️ נתיב מעובד: {preferences_path}")
                                
                                # בדיקת קיום הנתיב
                                if preferences_path and Path(preferences_path).exists():
                                    self.status.emit(f"📂 הנתיב קיים במערכת")
                                    
                                    # בדיקת תקינות התיקיה
                                    if validate_otzaria_folder(preferences_path):
                                        LOCAL_PATH = preferences_path
                                        self.status.emit(f"🎉 נמצאה תיקיית אוצריא מקובץ ההגדרות: {LOCAL_PATH}")
                                        self.copy_manifests_and_finish()
                                        return
                                    else:
                                        self.status.emit("❌ התיקיה לא מכילה את הקבצים הנדרשים של אוצריא")
                                else:
                                    self.status.emit(f"❌ הנתיב {preferences_path} לא קיים במערכת")
                            else:
                                self.status.emit("❌ לא נמצא נתיב ספרייה בקובץ ההעדפות")
                                # הצגת חלק מהתוכן לדיבוג
                                preview = content[:300].replace('\x00', '').strip()
                                if preview:
                                    self.status.emit(f"👀 תצוגה מקדימה של התוכן: {preview[:100]}...")
                                else:
                                    self.status.emit("📄 הקובץ נראה ריק או לא מכיל טקסט קריא")
                        except Exception as file_error:
                            self.status.emit(f"❌ שגיאה בקריאת קובץ ההגדרות: {str(file_error)}")
                    else:
                        self.status.emit("❌ קובץ ההעדפות לא נמצא")
                        
                        # בדיקת סיבות אפשריות
                        self.status.emit("🔍 בודק סיבות אפשריות:")
                        
                        # בדיקה אם התיקיה הראשית קיימת
                        parent_dir = Path(FILE_PATH).parent
                        self.status.emit(f"📁 תיקיית אב קיימת: {parent_dir.exists()} ({parent_dir})")
                        
                        # חיפוש קבצים דומים
                        if parent_dir.exists():
                            try:
                                similar_files = [f.name for f in parent_dir.iterdir() if f.is_file() and 'pref' in f.name.lower()]
                                if similar_files:
                                    self.status.emit(f"📋 קבצים דומים נמצאו: {similar_files}")
                                else:
                                    self.status.emit("📋 לא נמצאו קבצים דומים")
                            except Exception as e:
                                self.status.emit(f"❌ שגיאה בחיפוש קבצים דומים: {e}")
                        
                        # בדיקה אם יש תיקיות אחרות של אוצריא
                        try:
                            com_example_path = Path(APP_DATA) / "com.example"
                            if com_example_path.exists():
                                otzaria_dirs = [d.name for d in com_example_path.iterdir() if d.is_dir() and 'otzar' in d.name.lower()]
                                if otzaria_dirs:
                                    self.status.emit(f"📁 תיקיות אוצריא אחרות: {otzaria_dirs}")
                        except Exception as e:
                            self.status.emit(f"❌ שגיאה בחיפוש תיקיות אוצריא: {e}")
                else:
                    self.status.emit("❌ לא ניתן לגשת למשתנה APPDATA")
            except Exception as e:
                self.status.emit(f"שגיאה בחיפוש בקובץ ההגדרות של תוכנת אוצריא: {str(e)}")
            
            if self.stop_search:
                return
            
            # שלב 3: חיפוש בתיקיות הבסיסיות של כל הכוננים/נקודות עיגון
            self.status.emit("מחפש בתיקיות הבסיסיות של כל הכוננים...")
            self.progress.emit(40)
            
            drives = get_system_drives()
            
            for drive in drives:
                # בדיקת השהיה
                while self.is_paused and not self.stop_search:
                    if not self.pause_message_sent:
                        self.status.emit("פעולה מושהית...")
                        self.pause_message_sent = True
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
            self.status.emit("מחפש בכל המחשב... לחץ על 'בחר תיקיה ידנית' כדי לעצור את החיפוש ולבחור בעצמך")
            self.progress.emit(60)
            
            # שליחת signal לאפשרות בחירה ידנית
            self.manual_selection.emit()
            
            # המתנה קצרה לאפשר למשתמש לבחור ידנית
            time.sleep(2)
            
            # בדיקה אם נעשתה בחירה ידנית
            if self.manual_selected or self.stop_search:
                return
            
            # המשך חיפוש בכל המחשב רק אם לא נעשתה בחירה ידנית
            for drive in drives:
                # בדיקת בחירה ידנית או עצירה
                if self.manual_selected or self.stop_search:
                    return
                    
                # בדיקת השהיה
                while self.is_paused and not self.stop_search:
                    if not self.pause_message_sent:
                        self.status.emit("פעולה מושהית...")
                        self.pause_message_sent = True
                    time.sleep(0.5)
                
                if self.stop_search or self.manual_selected:
                    return
                    
                self.status.emit(f"מחפש בכל קבצי כונן {drive}")
                try:
                    for root, dirs, files in os.walk(drive):
                        # בדיקת בחירה ידנית או השהיה בלולאה הפנימית
                        if self.manual_selected or self.stop_search:
                            return
                            
                        while self.is_paused and not self.stop_search:
                            if not self.pause_message_sent:
                                self.status.emit("פעולה מושהית...")
                                self.pause_message_sent = True
                            time.sleep(0.5)
                        
                        if self.stop_search or self.manual_selected:
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
        
        except Exception as e:
            self.finished.emit(False, f"שגיאה בחיפוש תיקיית אוצריא: {str(e)}")

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
            src = os.path.join(LOCAL_PATH, DICTA_MANIFEST_FILE_NAME)
            if os.path.exists(src):
                dst = os.path.join(BASE_PATH, DICTA_MANIFEST_FILE_NAME)
                shutil.copy(src, dst)
                self.status.emit(f"הועתק: {DICTA_MANIFEST_FILE_NAME}")
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
                "https://github.com/Y-PLONI/otzaria-library"
            ]
            
            for url in test_urls:
                try:
                    # ניסיון ראשון עם הגדרות רגילות
                    response = self.session.get(url, timeout=15)
                    if response.status_code == 200:
                        return True
                except requests.exceptions.SSLError:
                    # אם יש בעיית SSL, נסה בלי אימות
                    try:
                        response = self.session.get(url, timeout=15, verify=False)
                        if response.status_code == 200:
                            return True
                    except:
                        continue
                except requests.exceptions.ProxyError:
                    # אם יש בעיית proxy, נסה בלי proxy
                    try:
                        temp_session = requests.Session()
                        temp_session.headers.update(self.session.headers)
                        temp_session.proxies = {}
                        response = temp_session.get(url, timeout=15, verify=False)
                        if response.status_code == 200:
                            # אם עבד בלי proxy, עדכן את ה-session הראשי
                            self.session.proxies = {}
                            return True
                    except:
                        continue
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
            manifests_to_process = [MANIFEST_FILE_NAME, DICTA_MANIFEST_FILE_NAME]
        else:  # אם אין קובץ דיקטה - סנכרן רק את הרגיל
            manifests_to_process = [MANIFEST_FILE_NAME]        

        all_failed_files = []
        all_file_tasks = []  # רשימת כל הקבצים להורדה
        
        # איסוף כל המשימות
        all_deleted_files = []  # רשימת קבצים שנמחקו
        
        for manifest_file in manifests_to_process:
            self.status.emit(f"מעבד: {manifest_file}")
            
            new_manifest_url = f"{BASE_URL}/{manifest_file}"
            old_manifest_file_path = os.path.join(BASE_PATH, manifest_file)
            
            try:
                # השהיה קצרה למניעת חסימה מצד השרת
                time.sleep(0.5)
                response = self.session.get(new_manifest_url, timeout=30)
                if response.status_code != 200:
                    self.finished.emit(False, f"שגיאה בהורדת {manifest_file}: קוד שגיאה {response.status_code}")
                    return
                
                # בדיקה שהתגובה היא JSON ולא HTML (למשל דף שגיאה)
                content_type = response.headers.get('Content-Type', '')
                if 'application/json' not in content_type and 'text/json' not in content_type:
                    # ננסה בכל זאת לפרסר, אבל נשמור את התוכן למקרה של שגיאה
                    response_text = response.text[:500]  # שומר רק 500 תווים ראשונים לדיבוג
                else:
                    response_text = None
                
                try:
                    new_manifest_content = response.json()
                except json.JSONDecodeError as json_err:
                    error_msg = f"שגיאה בפענוח {manifest_file}: התגובה מהשרת אינה JSON תקין.\n"
                    error_msg += f"סוג תוכן: {content_type}\n"
                    if response_text:
                        error_msg += f"תחילת התגובה: {response_text[:200]}..."
                    self.finished.emit(False, error_msg)
                    return
                
                with open(old_manifest_file_path, "r", encoding="utf-8") as f:
                    old_manifest_content = json.load(f)
                
                if new_manifest_content == old_manifest_content:
                    self.status.emit(f"אין עדכונים בקובץ ה-{manifest_file}")
                    continue

                # הכנת משימות הורדה
                for book_name, value in new_manifest_content.items():
                    if value["hash"] != old_manifest_content.get(book_name, {}).get("hash"):
                        # חישוב target_path לפי הלוגיקה החדשה
                        target_folder_components = book_name.split("/")
                        file_type = "אוצריא" if "אוצריא" in target_folder_components else "links"
                        target_path_parts = target_folder_components[target_folder_components.index(file_type):]
                        target_path = os.path.join(BASE_PATH, *target_path_parts)
                        
                        file_url = f"{BASE_URL}{book_name}"
                        
                        all_file_tasks.append((book_name, file_url, target_path))

                # איסוף קבצים שנמחקו מהמניפסט
                del_list = [book_name.replace("/", os.sep) for book_name in old_manifest_content if book_name not in new_manifest_content]
                all_deleted_files.extend(del_list)

                # עדכון המניפסט
                with open(old_manifest_file_path, "w", encoding="utf-8") as f:
                    json.dump(new_manifest_content, f, indent=2, ensure_ascii=False)
                    
            except Exception as e:
                self.finished.emit(False, f"שגיאה בעיבוד {manifest_file}: {str(e)}")
                return
        
        # כתיבת קובץ del_list אם יש קבצים שנמחקו
        if all_deleted_files:
            del_list_file_path = os.path.join(BASE_PATH, DEL_LIST_FILE_NAME)
            with open(del_list_file_path, "a", encoding="utf-8") as f:
                f.write("\n".join(all_deleted_files) + "\n")

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
                            if not self.pause_message_sent:
                                self.status.emit("פעולה מושהית...")
                                self.pause_message_sent = True
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
                        
                        # חישוב מהירות נוכחית
                        elapsed_time = time.time() - start_time
                        current_speed = 0
                        if elapsed_time > 0:
                            current_speed = total_downloaded_mb / elapsed_time
                        
                        # שליחת עדכון התקדמות מפורט
                        self.download_progress.emit(
                            book_name, 
                            int(progress), 
                            current_speed, 
                            completed_files, 
                            len(all_file_tasks)
                        )
                        
                        # הצגת סטטיסטיקות כל 10 קבצים
                        if completed_files % 10 == 0:
                            if elapsed_time > 0:
                                self.status.emit(f"הורדו {completed_files}/{len(all_file_tasks)} | "
                                               f"מהירות: {current_speed:.1f} MB/s")
                                
                            # שליחת עדכון סטטיסטיקות
                            stats_data = {
                                'total_files': len(all_file_tasks),
                                'completed_files': completed_files,
                                'total_size_mb': total_downloaded_mb,
                                'current_speed': current_speed,
                                'elapsed_time': elapsed_time
                            }
                            self.stats_update.emit(stats_data)
            
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
                if not self.pause_message_sent:
                    self.status.emit("פעולה מושהית...")
                    self.pause_message_sent = True
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
                if not self.pause_message_sent:
                    self.status.emit("פעולה מושהית...")
                    self.pause_message_sent = True
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
                        if not self.pause_message_sent:
                            self.status.emit("פעולה מושהית...")
                            self.pause_message_sent = True
                        time.sleep(0.5)
                    
                    if self.stop_search:
                        self.status.emit("פעולה בוטלה")
                        return
                    
                    file_path = file_path.strip()
                    if not file_path:
                        continue
                    full_path = os.path.join(LOCAL_PATH, file_path)
                    if os.path.exists(full_path):
                        os.remove(full_path)
                        deleted_count += 1
                
                os.remove(del_list_file_path)
                self.status.emit(f"נמחקו {deleted_count} קבצים")
                self.progress.emit(80)
            
            # בדיקת השהיה לפני מחיקת תיקיות רקות
            while self.is_paused and not self.stop_search:
                if not self.pause_message_sent:
                    self.status.emit("פעולה מושהית...")
                    self.pause_message_sent = True
                time.sleep(0.5)
            
            if self.stop_search:
                self.status.emit("פעולה בוטלה")
                return
            
            # מחיקת תיקיות רקות
            for root, dirs, _ in os.walk(LOCAL_PATH, topdown=False):
                for dir_name in dirs:
                    # בדיקת השהיה בכל תיקיה
                    while self.is_paused and not self.stop_search:
                        if not self.pause_message_sent:
                            self.status.emit("פעולה מושהית...")
                            self.pause_message_sent = True
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
            success_message = ("הסנכרון הושלם בהצלחה!!\n"
                                "כל הספרים נכנסו לתוך תוכנת אוצריא")
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
        
class AnimatedButton(QPushButton):
    """כפתור עם אנימציות חלקות משופרות
    
    שינויים חדשים:
    - כפתורים לא פעילים לא מגיבים ל-hover (לא גדלים ולא משתנים)
    - כפתורים לא פעילים מוצגים באותו צבע המקורי אבל מוחלש באמצעות QGraphicsOpacityEffect
    - ניתן להתאים את רמת השקיפות באמצעות set_disabled_opacity()
    """
    def __init__(self, text, parent=None):
        super().__init__(text, parent)
        
        # הפניה למנהל האנימציות (יוגדר מאוחר יותר)
        self.animation_manager = None
        
        # אנימציות בסיסיות (fallback)
        self.geometry_animation = QPropertyAnimation(self, b"geometry")
        self.geometry_animation.setDuration(200)
        self.geometry_animation.setEasingCurve(QEasingCurve.Type.OutCubic)
        
        # אנימציית שקיפות
        self.opacity_animation = QPropertyAnimation(self, b"windowOpacity")
        self.opacity_animation.setDuration(150)
        self.opacity_animation.setEasingCurve(QEasingCurve.Type.OutCubic)
        
        # סגנונות
        self.original_style = ""
        self.hover_style = ""
        self.disabled_style = ""
        self.pressed_style = ""
        
        # מצבים
        self.is_animating = False
        self.hover_animation_active = False
        
        # הגדרות אנימציה
        self.hover_scale = 1.02
        self.click_scale = 0.98
        self.animation_duration = 150
        
        # אפקטים ויזואליים
        self.shadow_enabled = True
        self.glow_enabled = False
        
        # אפקט שקיפות לכפתורים לא פעילים
        self.disabled_opacity = 0.4  # רמת השקיפות לכפתורים לא פעילים
        
    def set_animation_manager(self, animation_manager):
        """הגדרת מנהל האנימציות"""
        self.animation_manager = animation_manager
    
    def set_styles(self, original, hover, disabled=None, pressed=None):
        """הגדרת סגנונות לכל המצבים"""
        self.original_style = original
        self.hover_style = hover
        # עכשיו לא נשתמש בסגנון disabled נפרד, אלא באפקט שקיפות
        self.disabled_style = disabled or original
        self.pressed_style = pressed or hover
        
        # הגדרת הסגנון הנוכחי עם כל המצבים כולל pressed
        combined_style = original + hover
        # אם יש סגנון pressed נפרד, נוסיף אותו
        if pressed and pressed != hover:
            combined_style += pressed
        self.setStyleSheet(combined_style)
        
        # עדכון אפקט השקיפות בהתאם למצב הכפתור
        self._update_opacity_effect()
    
    def _create_faded_style(self, original_style):
        """יצירת סגנון מוחלש מהסגנון המקורי"""
        try:
            # נוסיף opacity לכל הכפתור כדי ליצור אפקט מוחלש
            if "opacity:" in original_style:
                # אם כבר יש opacity, נחליף אותו
                import re
                faded_style = re.sub(r'opacity:\s*[\d.]+;', 'opacity: 0.5;', original_style)
            else:
                # נוסיף opacity חדש
                faded_style = original_style.replace("QPushButton {", "QPushButton { opacity: 0.5;")
            
            return faded_style
        except:
            # במקרה של שגיאה, נחזיר את הסגנון המקורי עם opacity
            return original_style.replace("QPushButton {", "QPushButton { opacity: 0.5;")
    
    def setEnabled(self, enabled):
        """עדכון מצב הכפתור עם אפקט שקיפות"""
        super().setEnabled(enabled)
        self._update_opacity_effect()
    
    def _update_opacity_effect(self):
        """עדכון אפקט השקיפות בהתאם למצב הכפתור"""
        if self.isEnabled():
            # כפתור פעיל - הסרת אפקט שקיפות
            self.setGraphicsEffect(None)
        else:
            # כפתור לא פעיל - הוספת אפקט שקיפות
            opacity_effect = QGraphicsOpacityEffect()
            opacity_effect.setOpacity(self.disabled_opacity)
            self.setGraphicsEffect(opacity_effect)
    
    def set_disabled_opacity(self, opacity):
        """הגדרת רמת השקיפות לכפתורים לא פעילים
        
        Args:
            opacity (float): רמת השקיפות בין 0.1 (שקוף מאוד) ל-1.0 (אטום)
                           ערכים נמוכים יותר = כפתור יותר מוחלש
        
        דוגמה:
            button.set_disabled_opacity(0.3)  # כפתור מוחלש מאוד
            button.set_disabled_opacity(0.6)  # כפתור מוחלש בינוני
        """
        self.disabled_opacity = max(0.1, min(1.0, opacity))  # בין 0.1 ל-1.0
        
        # עדכון האפקט אם הכפתור כרגע לא פעיל
        self._update_opacity_effect()
    
    def set_animation_settings(self, hover_scale=1.02, click_scale=0.98, duration=150):
        """הגדרת פרמטרי אנימציה"""
        self.hover_scale = hover_scale
        self.click_scale = click_scale
        self.animation_duration = duration
    
    def enable_shadow(self, enabled=True):
        """הפעלה/כיבוי של אפקט צל"""
        self.shadow_enabled = enabled
        self._update_visual_effects()
    
    def enable_glow(self, enabled=True):
        """הפעלה/כיבוי של אפקט זוהר"""
        self.glow_enabled = enabled
        self._update_visual_effects()
    
    def _update_visual_effects(self):
        """עדכון אפקטים ויזואליים"""
        try:
            effects = []
            
            if self.shadow_enabled:
                effects.append("box-shadow: 0 2px 4px rgba(0,0,0,0.1);")
            
            if self.glow_enabled and self.hover_animation_active:
                effects.append("box-shadow: 0 0 10px rgba(66, 165, 245, 0.5);")
            
            # הוספת האפקטים לסגנון הנוכחי
            current_style = self.styleSheet()
            if effects:
                effect_style = " ".join(effects)
                # הוספה בזהירות כדי לא לשבור את הסגנון הקיים
                if "box-shadow" not in current_style:
                    current_style = current_style.rstrip('}') + effect_style + '}'
            
        except Exception as e:
            print(f"שגיאה בעדכון אפקטים ויזואליים: {e}")
    
    def enterEvent(self, event):
        """אירוע כניסה של העכבר"""
        try:
            # אם הכפתור לא פעיל - לא לעשות כלום (לא hover ולא אנימציה)
            if not self.isEnabled():
                return
                
            if self.is_animating:
                return
            
            self.hover_animation_active = True
            
            # החלפת סגנון
            self.setStyleSheet(self.hover_style)
            self._update_visual_effects()
            
            # אנימציית הגדלה
            if self.animation_manager:
                # שימוש במנהל האנימציות
                animation = self.animation_manager.create_scale_animation(
                    self, duration=self.animation_duration, 
                    start_scale=1.0, end_scale=self.hover_scale
                )
                if animation:
                    animation.start()
            else:
                # fallback לאנימציה בסיסית
                self._animate_scale(1.0, self.hover_scale)
            
            super().enterEvent(event)
            
        except Exception as e:
            print(f"שגיאה באירוע כניסת עכבר: {e}")
            super().enterEvent(event)
    
    def leaveEvent(self, event):
        """אירוע יציאה של העכבר"""
        try:
            # אם הכפתור לא פעיל - לא לעשות כלום
            if not self.isEnabled():
                return
                
            self.hover_animation_active = False
            
            # החלפת סגנון מיידית
            self.setStyleSheet(self.original_style)
            self._update_visual_effects()
            
            # ביטול כל האנימציות הפעילות
            if hasattr(self, 'geometry_animation') and self.geometry_animation.state() == QPropertyAnimation.State.Running:
                self.geometry_animation.stop()
            
            # אנימציית הקטנה חזרה
            if self.animation_manager:
                animation = self.animation_manager.create_scale_animation(
                    self, duration=100,  # מהירות יותר לחזרה
                    start_scale=self.hover_scale, end_scale=1.0
                )
                if animation:
                    animation.start()
            else:
                self._animate_scale(self.hover_scale, 1.0)
            
            super().leaveEvent(event)
            
        except Exception as e:
            print(f"שגיאה באירוע יציאת עכבר: {e}")
            super().leaveEvent(event)
    
    def mousePressEvent(self, event):
        """אירוע לחיצה על הכפתור"""
        try:
            # אם הכפתור לא פעיל - לא לעשות כלום
            if not self.isEnabled():
                return
            
            # החלפת סגנון ללחיצה
            if self.pressed_style:
                self.setStyleSheet(self.pressed_style)
            
            # אנימציית לחיצה
            if self.animation_manager:
                self.animation_manager.animate_button_click(self)
            else:
                self._animate_click()
            
            super().mousePressEvent(event)
            
        except Exception as e:
            print(f"שגיאה באירוע לחיצה: {e}")
            super().mousePressEvent(event)
    
    def mouseReleaseEvent(self, event):
        """אירוע שחרור הכפתור"""
        try:
            # חזרה לסגנון hover אם העכבר עדיין מעל הכפתור
            if self.underMouse() and self.isEnabled():
                self.setStyleSheet(self.hover_style)
            elif self.isEnabled():
                self.setStyleSheet(self.original_style)
            
            super().mouseReleaseEvent(event)
            
        except Exception as e:
            print(f"שגיאה באירוע שחרור: {e}")
            super().mouseReleaseEvent(event)
    
    def changeEvent(self, event):
        """אירוע שינוי מצב הכפתור"""
        try:
            if event.type() == event.Type.EnabledChange:
                if self.isEnabled():
                    # כפתור הופך לפעיל - חזרה לסגנון רגיל
                    self.setStyleSheet(self.original_style)
                    # הסרת אפקט השקיפות
                    self.setGraphicsEffect(None)
                else:
                    # כפתור הופך ללא פעיל - שימוש בסגנון מקורי עם אפקט שקיפות
                    self.setStyleSheet(self.original_style)
                    # עדכון אפקט השקיפות
                    self._update_opacity_effect()
            
            super().changeEvent(event)
            
        except Exception as e:
            print(f"שגיאה באירוע שינוי מצב: {e}")
            super().changeEvent(event)
    
    def _animate_scale(self, start_scale, end_scale):
        """אנימציית הגדלה/הקטנה בסיסית (fallback)"""
        try:
            # אם הכפתור לא פעיל - לא לעשות אנימציה
            if not self.isEnabled() or self.is_animating:
                return
            
            self.is_animating = True
            
            # חישוב גיאומטריה
            current_rect = self.geometry()
            center = current_rect.center()
            
            end_width = int(current_rect.width() * end_scale)
            end_height = int(current_rect.height() * end_scale)
            end_rect = QRect(
                center.x() - end_width // 2,
                center.y() - end_height // 2,
                end_width,
                end_height
            )
            
            # הגדרת אנימציה
            self.geometry_animation.setStartValue(current_rect)
            self.geometry_animation.setEndValue(end_rect)
            self.geometry_animation.setDuration(self.animation_duration)
            
            # חיבור לסיום
            self.geometry_animation.finished.connect(self._on_animation_finished)
            
            # הפעלה
            self.geometry_animation.start()
            
        except Exception as e:
            print(f"שגיאה באנימציית scale: {e}")
            self.is_animating = False
    
    def _animate_click(self):
        """אנימציית לחיצה בסיסית (fallback)"""
        try:
            # אנימציה קצרה של הקטנה והגדלה
            QTimer.singleShot(0, lambda: self._animate_scale(1.0, self.click_scale))
            QTimer.singleShot(100, lambda: self._animate_scale(self.click_scale, 1.0))
            
        except Exception as e:
            print(f"שגיאה באנימציית לחיצה: {e}")
    
    def _on_animation_finished(self):
        """קריאה חוזרת לסיום אנימציה"""
        self.is_animating = False
        try:
            self.geometry_animation.finished.disconnect()
        except:
            pass
    
    def stop_animations(self):
        """עצירת כל האנימציות"""
        try:
            self.is_animating = False
            self.geometry_animation.stop()
            self.opacity_animation.stop()
            
            if self.animation_manager:
                # עצירת אנימציות במנהל
                widget_id = id(self)
                if widget_id in self.animation_manager.animations:
                    self.animation_manager.animations[widget_id].stop()
                if widget_id in self.animation_manager.animation_groups:
                    self.animation_manager.animation_groups[widget_id].stop()
                    
        except Exception as e:
            print(f"שגיאה בעצירת אנימציות: {e}")

class EnhancedProgressBar(QProgressBar):
    """מד התקדמות משופר עם אנימציות ומידע מפורט"""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.animation_manager = None
        self.current_file = ""
        self.download_speed = 0
        self.time_remaining = 0
        self.files_completed = 0
        self.total_files = 0
        self.bytes_downloaded = 0
        self.total_bytes = 0
        self.start_time = None
        self.last_update_time = time.time()
        
        # אנימציה לעדכון ערך
        self.value_animation = QPropertyAnimation(self, b"value")
        self.value_animation.setDuration(300)
        self.value_animation.setEasingCurve(QEasingCurve.Type.OutCubic)
        
    def set_animation_manager(self, animation_manager):
        """הגדרת מנהל האנימציות"""
        self.animation_manager = animation_manager
        
    def update_progress_animated(self, value):
        """עדכון התקדמות עם אנימציה"""
        try:
            if self.value_animation.state() == QPropertyAnimation.State.Running:
                self.value_animation.stop()
            
            self.value_animation.setStartValue(self.value())
            self.value_animation.setEndValue(value)
            self.value_animation.start()
        except Exception as e:
            # fallback לעדכון רגיל
            self.setValue(value)
    
    def set_detailed_stats(self, **kwargs):
        """עדכון סטטיסטיקות מפורטות"""
        if 'current_file' in kwargs:
            self.current_file = kwargs['current_file']
        if 'download_speed' in kwargs:
            self.download_speed = kwargs['download_speed']
        if 'time_remaining' in kwargs:
            self.time_remaining = kwargs['time_remaining']
        if 'files_completed' in kwargs:
            self.files_completed = kwargs['files_completed']
        if 'total_files' in kwargs:
            self.total_files = kwargs['total_files']
        if 'bytes_downloaded' in kwargs:
            self.bytes_downloaded = kwargs['bytes_downloaded']
        if 'total_bytes' in kwargs:
            self.total_bytes = kwargs['total_bytes']
        if 'start_time' in kwargs:
            self.start_time = kwargs['start_time']
            
        self.update_display_text()
        
    def update_display_text(self):
        """עדכון הטקסט המוצג"""
        try:
            parts = []
            
            # אחוז התקדמות
            parts.append(f"{self.value()}%")
            
            # קבצים
            if self.total_files > 0:
                parts.append(f"{self.files_completed}/{self.total_files} קבצים")
            
            # מהירות הורדה
            if self.download_speed > 0:
                parts.append(f"{self.download_speed:.1f} MB/s")
            
            # זמן נותר
            if self.time_remaining > 0:
                time_str = self.format_time_remaining(self.time_remaining)
                parts.append(f"נותר: {time_str}")
            
            # גודל קבצים
            if self.total_bytes > 0:
                downloaded_str = self.format_file_size(self.bytes_downloaded)
                total_str = self.format_file_size(self.total_bytes)
                parts.append(f"{downloaded_str}/{total_str}")
            
            # קובץ נוכחי (רק אם יש מקום)
            display_text = " | ".join(parts)
            if len(display_text) < 100 and self.current_file:
                # הצגת שם קובץ מקוצר
                short_filename = self.current_file.split('/')[-1]
                if len(short_filename) > 30:
                    short_filename = short_filename[:27] + "..."
                display_text += f" | {short_filename}"
            
            self.setFormat(display_text)
            
        except Exception as e:
            # fallback לתצוגה בסיסית
            self.setFormat(f"{self.value()}%")
    
    def format_time_remaining(self, seconds):
        """פורמט זמן נותר"""
        try:
            if seconds < 60:
                return f"{int(seconds)}ש"
            elif seconds < 3600:
                mins = int(seconds // 60)
                secs = int(seconds % 60)
                return f"{mins}:{secs:02d}"
            else:
                hours = int(seconds // 3600)
                mins = int((seconds % 3600) // 60)
                return f"{hours}:{mins:02d}:00"
        except:
            return "לא ידוע"
    
    def format_file_size(self, bytes_size):
        """פורמט גודל קובץ"""
        try:
            if bytes_size < 1024:
                return f"{bytes_size}B"
            elif bytes_size < 1024**2:
                return f"{bytes_size/1024:.1f}KB"
            elif bytes_size < 1024**3:
                return f"{bytes_size/(1024**2):.1f}MB"
            else:
                return f"{bytes_size/(1024**3):.1f}GB"
        except:
            return "0B"
    
    def reset_stats(self):
        """איפוס כל הסטטיסטיקות"""
        self.current_file = ""
        self.download_speed = 0
        self.time_remaining = 0
        self.files_completed = 0
        self.total_files = 0
        self.bytes_downloaded = 0
        self.total_bytes = 0
        self.start_time = None
        self.setValue(0)
        self.setFormat("0%")
    
    def set_stats(self, speed=0, time_remaining=0, files_processed=0, total_files=0):
        """מתודה לתאימות לאחור עם הקוד הישן"""
        try:
            self.set_detailed_stats(
                download_speed=speed,
                time_remaining=time_remaining,
                files_completed=files_processed,
                total_files=total_files
            )
        except Exception as e:
            print(f"שגיאה בעדכון סטטיסטיקות progress bar (תאימות לאחור): {e}")



class ThemeManager:
    """מנהל ערכות נושא - מצב כהה/בהיר"""
    
    def __init__(self, settings):
        self.settings = settings
        self.current_theme = self.settings.value("theme", "light", type=str)
        self.themes = {
            "light": self._create_light_theme(),
            "dark": self._create_dark_theme()
        }
    
    def _create_light_theme(self):
        """יצירת ערכת נושא בהירה"""
        return {
            "name": "light",
            "background_color": "#FFFFFF",
            "text_color": "#2E4057",
            "primary_color": "#4CAF50",
            "secondary_color": "#2196F3",
            "accent_color": "#FF9800",
            "button_colors": {
                "primary": "qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #4CAF50, stop:1 #45a049)",
                "secondary": "qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #2196F3, stop:1 #1976D2)",
                "accent": "qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #FF9800, stop:1 #F57C00)",
                "danger": "qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #f44336, stop:1 #da190b)",
                "warning": "qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #FF9800, stop:1 #F57C00)",
                "disabled": "#CCCCCC"
            },
            "progress_bar_colors": {
                "background": "#F5F5F5",
                "border": "#E0E0E0",
                "chunk": "qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #4CAF50, stop:0.5 #66BB6A, stop:1 #4CAF50)"
            },
            "border_colors": {
                "normal": "#CCCCCC",
                "focus": "#2196F3",
                "error": "#f44336"
            },
            "panel_colors": {
                "background": "#F8F9FA",
                "border": "#E0E0E0"
            }
        }
    
    def _create_dark_theme(self):
        """יצירת ערכת נושא כהה"""
        return {
            "name": "dark",
            "background_color": "#2B2B2B",
            "text_color": "#FFFFFF",
            "primary_color": "#66BB6A",
            "secondary_color": "#42A5F5",
            "accent_color": "#FFB74D",
            "button_colors": {
                "primary": "qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #66BB6A, stop:1 #4CAF50)",
                "secondary": "qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #42A5F5, stop:1 #2196F3)",
                "accent": "qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #FFB74D, stop:1 #FF9800)",
                "danger": "qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #EF5350, stop:1 #f44336)",
                "warning": "qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #FFB74D, stop:1 #FF9800)",
                "disabled": "#555555"
            },
            "progress_bar_colors": {
                "background": "#3C3C3C",
                "border": "#555555",
                "chunk": "qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #66BB6A, stop:0.5 #4CAF50, stop:1 #66BB6A)"
            },
            "border_colors": {
                "normal": "#555555",
                "focus": "#42A5F5",
                "error": "#EF5350"
            },
            "panel_colors": {
                "background": "#3C3C3C",
                "border": "#555555"
            }
        }
    
    def apply_theme(self, theme_name, widget):
        """החלת ערכת נושא על ווידג'ט"""
        try:
            if theme_name not in self.themes:
                theme_name = "light"
            
            theme = self.themes[theme_name]
            self.current_theme = theme_name
            
            # החלת סגנון כללי על החלון הראשי
            if hasattr(widget, 'setStyleSheet'):
                main_style = self._generate_main_stylesheet(theme)
                widget.setStyleSheet(main_style)
            
            # עדכון אייקונים לערכת הנושא החדשה
            if hasattr(widget, 'icon_manager'):
                widget.icon_manager.update_icons_for_theme(theme_name)
            
            # עדכון כל הכפתורים
            self._update_buttons_theme(widget, theme)
            
            # עדכון כפתורי שליטה על היומן
            self._update_log_control_buttons_theme(theme)
            
            # עדכון מדי התקדמות
            self._update_progress_bars_theme(widget, theme)
            
            # עדכון פאנלים
            self._update_panels_theme(widget, theme)
            
            return True
            
        except Exception as e:
            print(f"שגיאה בהחלת ערכת נושא: {e}")
            return False
    
    def _generate_main_stylesheet(self, theme):
        """יצירת stylesheet ראשי"""
        return f"""
            QMainWindow {{
                background-color: {theme['background_color']};
                color: {theme['text_color']};
            }}
            QLabel {{
                color: {theme['text_color']};
            }}
            QTextEdit {{
                background-color: {theme['panel_colors']['background']};
                border: 1px solid {theme['border_colors']['normal']};
                border-radius: 5px;
                color: {theme['text_color']};
            }}
            QGroupBox {{
                color: {theme['text_color']};
                border: 2px solid {theme['border_colors']['normal']};
                border-radius: 5px;
                margin-top: 10px;
                font-weight: bold;
            }}
            QGroupBox::title {{
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px 0 5px;
            }}
            QTabWidget::pane {{
                border: 1px solid {theme['border_colors']['normal']};
                background-color: {theme['background_color']};
            }}
            QTabBar::tab {{
                background-color: {theme['panel_colors']['background']};
                color: {theme['text_color']};
                padding: 8px 16px;
                margin-right: 2px;
                border-top-left-radius: 5px;
                border-top-right-radius: 5px;
            }}
            QTabBar::tab:selected {{
                background-color: {theme['background_color']};
                border-bottom: 2px solid {theme['primary_color']};
            }}
            QStatusBar {{
                background-color: {theme['panel_colors']['background']};
                color: {theme['text_color']};
                border-top: 1px solid {theme['border_colors']['normal']};
            }}
        """
    
    def _update_buttons_theme(self, widget, theme):
        """עדכון כפתורים לערכת נושא"""
        try:
            # חיפוש כל הכפתורים בווידג'ט
            buttons = widget.findChildren(QPushButton)
            for button in buttons:
                if hasattr(button, 'set_styles'):
                    # כפתור מונפש - עדכון הסגנונות
                    self._update_animated_button_theme(button, theme)
                else:
                    # כפתור רגיל
                    self._update_regular_button_theme(button, theme)
        except Exception as e:
            print(f"שגיאה בעדכון כפתורים: {e}")
    
    def _update_animated_button_theme(self, button, theme):
        """עדכון כפתור מונפש לערכת נושא"""
        try:
            # זיהוי סוג הכפתור לפי הטקסט או המאפיינים
            text = button.text().lower()
            
            if "טען" in text or "folder" in text:
                color_key = "primary"
            elif "הורד" in text or "download" in text:
                color_key = "secondary"
            elif "עדכן" in text or "sync" in text:
                color_key = "accent"
            elif "בטל" in text or "stop" in text:
                color_key = "danger"
            elif "השהה" in text or "pause" in text:
                color_key = "warning"
            else:
                color_key = "primary"
            
            original_style = f"""
                QPushButton {{
                    background: {theme['button_colors'][color_key]};
                    color: white;
                    border: none;
                    border-radius: 12px;
                    font-size: 16px;
                    font-weight: bold;
                    padding: 10px;
                }}
            """
            
            # יצירת hover style עם צבע מעט יותר בהיר
            hover_style = original_style  # הסרת transform שגורם לשגיאות
            
            # הגדרת הסגנונות עם הסגנון המוחלש החדש
            button.set_styles(original_style, hover_style)
            
        except Exception as e:
            print(f"שגיאה בעדכון כפתור מונפש: {e}")
    
    def _update_log_control_buttons_theme(self, theme):
        """עדכון כפתורי שליטה על יומן הפעולות לערכת נושא"""
        try:
            if hasattr(self, 'btn_expand_log') and hasattr(self, 'btn_shrink_log'):
                if theme == "dark":
                    style = """
                        QPushButton {
                            background-color: #424242;
                            border: 1px solid #616161;
                            border-radius: 3px;
                            color: white;
                            font-size: 12px;
                        }
                        QPushButton:hover {
                            background-color: #616161;
                        }
                    """
                else:
                    style = """
                        QPushButton {
                            background-color: #E3F2FD;
                            border: 1px solid #BBDEFB;
                            border-radius: 3px;
                            font-size: 12px;
                        }
                        QPushButton:hover {
                            background-color: #BBDEFB;
                        }
                    """
                self.btn_expand_log.setStyleSheet(style)
                self.btn_shrink_log.setStyleSheet(style)
        except Exception as e:
            print(f"שגיאה בעדכון כפתורי שליטה על היומן: {e}")
    
    def _update_regular_button_theme(self, button, theme):
        """עדכון כפתור רגיל לערכת נושא"""
        try:
            # בדיקה אם הכפתור צריך לשמור על הצבעים הספציפיים שלו
            button_text = button.text()
            
            # כפתורים שצריכים לשמור על הצבעים הספציפיים שלהם
            if button_text == "איפוס מצב":
                # כפתור איפוס מצב - סגול
                style = """
                    QPushButton {
                        background-color: #9C27B0;
                        color: white;
                        border: none;
                        border-radius: 5px;
                        font-size: 12px;
                        padding: 5px 10px;
                    }
                    QPushButton:hover {
                        background-color: #7B1FA2;
                    }
                    QPushButton:disabled {
                        opacity: 0.4;
                        background-color: #CCCCCC;
                        color: #888888;
                    }
                """
            elif button_text == "בטל":
                # כפתור ביטול - אדום
                style = """
                    QPushButton {
                        background-color: #f44336;
                        color: white;
                        border: none;
                        border-radius: 5px;
                        font-size: 12px;
                        padding: 5px 10px;
                    }
                    QPushButton:hover {
                        background-color: #da190b;
                    }
                    QPushButton:disabled {
                        opacity: 0.6;
                    }
                """
            elif button_text in ["השהה", "המשך"]:
                # כפתור השהיה/המשך - כתום
                style = """
                    QPushButton {
                        background-color: #FF9800;
                        color: white;
                        border: none;
                        border-radius: 5px;
                        font-size: 12px;
                        padding: 5px 10px;
                    }
                    QPushButton:hover {
                        background-color: #F57C00;
                    }
                    QPushButton:disabled {
                        opacity: 0.6;
                    }
                """
            else:
                # כפתורים רגילים - צבעי הערכה
                style = f"""
                    QPushButton {{
                        background-color: {theme['primary_color']};
                        color: white;
                        border: none;
                        border-radius: 5px;
                        font-size: 12px;
                        padding: 5px 10px;
                    }}
                    QPushButton:hover {{
                        background-color: {theme['secondary_color']};
                    }}
                    QPushButton:disabled {{
                        opacity: 0.6;
                    }}
                """
            
            button.setStyleSheet(style)
        except Exception as e:
            print(f"שגיאה בעדכון כפתור רגיל: {e}")
    
    def _update_progress_bars_theme(self, widget, theme):
        """עדכון מדי התקדמות לערכת נושא"""
        try:
            progress_bars = widget.findChildren(QProgressBar)
            for pb in progress_bars:
                style = f"""
                    QProgressBar {{
                        border: 2px solid {theme['progress_bar_colors']['border']};
                        border-radius: 15px;
                        text-align: center;
                        font-weight: bold;
                        font-size: 12px;
                        background-color: {theme['progress_bar_colors']['background']};
                        color: {theme['text_color']};
                    }}
                    QProgressBar::chunk {{
                        background: {theme['progress_bar_colors']['chunk']};
                        border-radius: 13px;
                        margin: 2px;
                    }}
                """
                pb.setStyleSheet(style)
        except Exception as e:
            print(f"שגיאה בעדכון מדי התקדמות: {e}")
    
    def _update_panels_theme(self, widget, theme):
        """עדכון פאנלים לערכת נושא"""
        try:
            frames = widget.findChildren(QFrame)
            for frame in frames:
                if frame.frameStyle() == QFrame.Shape.StyledPanel:
                    style = f"""
                        QFrame {{
                            background-color: {theme['panel_colors']['background']};
                            border: 1px solid {theme['panel_colors']['border']};
                            border-radius: 10px;
                        }}
                    """
                    frame.setStyleSheet(style)
        except Exception as e:
            print(f"שגיאה בעדכון פאנלים: {e}")
    
    def toggle_theme(self, widget):
        """החלפה בין ערכות נושא"""
        try:
            new_theme = "dark" if self.current_theme == "light" else "light"
            success = self.apply_theme(new_theme, widget)
            if success:
                self.save_theme_preference()
            return success
        except Exception as e:
            print(f"שגיאה בהחלפת ערכת נושא: {e}")
            return False
    
    def get_current_theme_colors(self):
        """קבלת צבעי ערכת הנושא הנוכחית"""
        return self.themes.get(self.current_theme, self.themes["light"])
    
    def save_theme_preference(self):
        """שמירת העדפת ערכת נושא"""
        try:
            self.settings.setValue("theme", self.current_theme)
            self.settings.sync()
            return True
        except Exception as e:
            print(f"שגיאה בשמירת העדפת ערכת נושא: {e}")
            return False

class FontManager:
    """מנהל גודל גופן"""
    
    def __init__(self, settings):
        self.settings = settings
        self.base_font_size = 10
        self.min_font_size = 8
        self.max_font_size = 20
        self.current_font_size = self.load_font_size()
        
    def load_font_size(self):
        """טעינת גודל גופן משמור"""
        try:
            size = self.settings.value("font_size", self.base_font_size, type=int)
            # וידוא שהגודל בטווח המותר
            return max(self.min_font_size, min(self.max_font_size, size))
        except Exception as e:
            print(f"שגיאה בטעינת גודל גופן: {e}")
            return self.base_font_size
    
    def increase_font_size(self, widget):
        """הגדלת גודל גופן"""
        try:
            new_size = min(self.current_font_size + 1, self.max_font_size)
            if new_size != self.current_font_size:
                self.current_font_size = new_size
                self.apply_font_to_widget(widget)
                self.save_font_size()
                return True
            return False
        except Exception as e:
            print(f"שגיאה בהגדלת גופן: {e}")
            return False
    
    def decrease_font_size(self, widget):
        """הקטנת גודל גופן"""
        try:
            new_size = max(self.current_font_size - 1, self.min_font_size)
            if new_size != self.current_font_size:
                self.current_font_size = new_size
                self.apply_font_to_widget(widget)
                self.save_font_size()
                return True
            return False
        except Exception as e:
            print(f"שגיאה בהקטנת גופן: {e}")
            return False
    
    def set_font_size(self, size, widget):
        """הגדרת גודל גופן ספציפי"""
        try:
            if self.min_font_size <= size <= self.max_font_size:
                self.current_font_size = size
                self.apply_font_to_widget(widget)
                self.save_font_size()
                return True
            return False
        except Exception as e:
            print(f"שגיאה בהגדרת גודל גופן: {e}")
            return False
    
    def apply_font_to_widget(self, widget, size=None):
        """החלת גודל גופן על ווידג'ט וכל הילדים שלו"""
        try:
            if size is None:
                size = self.current_font_size
            
            # עדכון הגופן של הווידג'ט הראשי
            font = widget.font()
            font.setPointSize(size)
            widget.setFont(font)
            
            # עדכון כל הווידג'טים הילדים
            self._apply_font_recursive(widget, size)
            
            # התאמת גודל החלון אם נדרש
            self._adjust_window_size(widget, size)
            
            return True
            
        except Exception as e:
            print(f"שגיאה בהחלת גופן: {e}")
            return False
    
    def _apply_font_recursive(self, widget, size):
        """החלת גופן באופן רקורסיבי על כל הווידג'טים"""
        try:
            # רשימת סוגי ווידג'טים שצריכים עדכון גופן
            font_widgets = (QLabel, QPushButton, QTextEdit, QGroupBox, 
                          QTabWidget, QProgressBar, QStatusBar, QMenuBar, QMenu)
            
            for child in widget.findChildren(QWidget):
                if isinstance(child, font_widgets):
                    font = child.font()
                    
                    # התאמת גודל לפי סוג הווידג'ט
                    if isinstance(child, QLabel):
                        # בדיקה אם זו כותרת (גופן גדול יותר)
                        if child.font().pointSize() > self.base_font_size + 5:
                            font.setPointSize(size + 8)  # כותרת ראשית
                        elif child.font().pointSize() > self.base_font_size + 2:
                            font.setPointSize(size + 4)  # כותרת משנית
                        else:
                            font.setPointSize(size)
                    elif isinstance(child, QPushButton):
                        # כפתורים גדולים יותר
                        if child.minimumHeight() > 50:
                            font.setPointSize(size + 2)
                        else:
                            font.setPointSize(size)
                    elif isinstance(child, QTextEdit):
                        # טקסט עריכה - גופן קצת יותר קטן
                        font.setPointSize(max(8, size - 1))
                    else:
                        font.setPointSize(size)
                    
                    child.setFont(font)
                    
        except Exception as e:
            print(f"שגיאה בהחלת גופן רקורסיבי: {e}")
    
    def _adjust_window_size(self, widget, size):
        """התאמת גודל חלון לגודל גופן"""
        try:
            if hasattr(widget, 'resize'):
                # קבלת גודל מסך זמין
                screen = QApplication.primaryScreen().availableGeometry()
                
                # חישוב יחס השינוי (מוגבל)
                size_ratio = min(size / self.base_font_size, 1.5)  # מגביל את היחס
                
                # גודל נוכחי
                current_size = widget.size()
                
                # חישוב גודל חדש
                new_width = min(int(current_size.width() * size_ratio), int(screen.width() * 0.9))
                new_height = min(int(current_size.height() * size_ratio), int(screen.height() * 0.9))
                
                # וידוא מינימום
                new_width = max(new_width, 600)
                new_height = max(new_height, 400)
                
                # עדכון גודל רק אם נדרש
                if new_width != current_size.width() or new_height != current_size.height():
                    widget.resize(new_width, new_height)
                    
                    # מרכוז החלון במסך
                    x = (screen.width() - new_width) // 2
                    y = (screen.height() - new_height) // 2
                    widget.move(max(0, x), max(0, y))
                    
        except Exception as e:
            print(f"שגיאה בהתאמת גודל חלון: {e}")
    
    def reset_to_default(self, widget):
        """איפוס לגודל ברירת מחדל"""
        try:
            self.current_font_size = self.base_font_size
            self.apply_font_to_widget(widget)
            self.save_font_size()
            return True
        except Exception as e:
            print(f"שגיאה באיפוס גודל גופן: {e}")
            return False
    
    def save_font_size(self):
        """שמירת גודל גופן"""
        try:
            self.settings.setValue("font_size", self.current_font_size)
            self.settings.sync()
            return True
        except Exception as e:
            print(f"שגיאה בשמירת גודל גופן: {e}")
            return False
    
    def get_font_info(self):
        """קבלת מידע על הגופן הנוכחי"""
        return {
            "current_size": self.current_font_size,
            "base_size": self.base_font_size,
            "min_size": self.min_font_size,
            "max_size": self.max_font_size,
            "can_increase": self.current_font_size < self.max_font_size,
            "can_decrease": self.current_font_size > self.min_font_size
        }

class AdvancedStatsWidget(QGroupBox):
    """ווידג'ט סטטיסטיקות מתקדם"""
    def __init__(self, parent=None):
        super().__init__("סטטיסטיקות מפורטות", parent)
        self.collapsible = True
        self.is_collapsed = False
        self.init_ui()
        
    def init_ui(self):
        layout = QVBoxLayout()
        
        # כותרת עם כפתור הצגה/הסתרה
        header_layout = QHBoxLayout()
        self.toggle_button = QPushButton("🔽")
        self.toggle_button.setMaximumWidth(30)
        self.toggle_button.clicked.connect(self.toggle_visibility)
        
        header_label = QLabel("סטטיסטיקות מפורטות")
        header_label.setStyleSheet("font-weight: bold; font-size: 14px;")
        
        header_layout.addWidget(header_label)
        header_layout.addStretch()
        header_layout.addWidget(self.toggle_button)
        
        # תוכן הסטטיסטיקות
        self.content_widget = QWidget()
        content_layout = QGridLayout()
        
        # סטטיסטיקות בסיסיות
        self.books_count_label = QLabel("0")
        self.files_size_label = QLabel("0 MB")
        self.last_sync_label = QLabel("אף פעם")
        self.download_speed_label = QLabel("0 MB/s")
        
        # סטטיסטיקות מתקדמות
        self.memory_usage_label = QLabel("0 MB")
        self.active_threads_label = QLabel("0")
        self.errors_count_label = QLabel("0")
        self.elapsed_time_label = QLabel("00:00:00")
        self.avg_speed_label = QLabel("0 MB/s")
        self.eta_label = QLabel("לא ידוע")
        
        # הוספת תוויות לגריד
        row = 0
        stats_items = [
            ("כמות ספרים:", self.books_count_label),
            ("גודל קבצים:", self.files_size_label),
            ("מהירות נוכחית:", self.download_speed_label),
            ("מהירות ממוצעת:", self.avg_speed_label),
            ("זמן שעבר:", self.elapsed_time_label),
            ("זמן משוער לסיום:", self.eta_label),
            ("שימוש זיכרון:", self.memory_usage_label),
            ("חוטים פעילים:", self.active_threads_label),
            ("שגיאות:", self.errors_count_label),
            ("סנכרון אחרון:", self.last_sync_label)
        ]
        
        for label_text, value_label in stats_items:
            label = QLabel(label_text)
            label.setStyleSheet("font-weight: bold;")
            content_layout.addWidget(label, row, 0)
            content_layout.addWidget(value_label, row, 1)
            row += 1
        
        self.content_widget.setLayout(content_layout)
        
        # הוספה לlayout הראשי
        layout.addLayout(header_layout)
        layout.addWidget(self.content_widget)
        
        self.setLayout(layout)
        
    def toggle_visibility(self):
        """החלפת מצב הצגה/הסתרה"""
        try:
            self.is_collapsed = not self.is_collapsed
            self.content_widget.setVisible(not self.is_collapsed)
            self.toggle_button.setText("🔼" if self.is_collapsed else "🔽")
        except Exception as e:
            print(f"שגיאה בהחלפת מצב תצוגה: {e}")
    
    def update_real_time_stats(self, stats_dict):
        """עדכון סטטיסטיקות בזמן אמת"""
        try:
            if 'books_count' in stats_dict:
                self.books_count_label.setText(str(stats_dict['books_count']))
            if 'total_size_mb' in stats_dict:
                self.files_size_label.setText(f"{stats_dict['total_size_mb']:.1f} MB")
            if 'download_speed' in stats_dict:
                self.download_speed_label.setText(f"{stats_dict['download_speed']:.1f} MB/s")
            if 'avg_speed' in stats_dict:
                self.avg_speed_label.setText(f"{stats_dict['avg_speed']:.1f} MB/s")
            if 'memory_usage_mb' in stats_dict:
                self.memory_usage_label.setText(f"{stats_dict['memory_usage_mb']:.1f} MB")
            if 'active_threads' in stats_dict:
                self.active_threads_label.setText(str(stats_dict['active_threads']))
            if 'errors_count' in stats_dict:
                self.errors_count_label.setText(str(stats_dict['errors_count']))
            if 'elapsed_time' in stats_dict:
                self.elapsed_time_label.setText(self._format_time(stats_dict['elapsed_time']))
            if 'eta' in stats_dict:
                self.eta_label.setText(self._format_time(stats_dict['eta']) if stats_dict['eta'] > 0 else "לא ידוע")
            if 'last_sync' in stats_dict:
                self.last_sync_label.setText(stats_dict['last_sync'])
                
        except Exception as e:
            print(f"שגיאה בעדכון סטטיסטיקות: {e}")
    
    def _format_time(self, seconds):
        """פורמט זמן בשניות לפורמט HH:MM:SS"""
        try:
            if seconds < 0:
                return "לא ידוע"
            hours = int(seconds // 3600)
            minutes = int((seconds % 3600) // 60)
            secs = int(seconds % 60)
            return f"{hours:02d}:{minutes:02d}:{secs:02d}"
        except:
            return "00:00:00"
    
    def export_stats(self):
        """ייצוא סטטיסטיקות לקובץ"""
        try:
            from datetime import datetime
            
            stats_data = {
                "timestamp": datetime.now().isoformat(),
                "books_count": self.books_count_label.text(),
                "files_size": self.files_size_label.text(),
                "download_speed": self.download_speed_label.text(),
                "avg_speed": self.avg_speed_label.text(),
                "memory_usage": self.memory_usage_label.text(),
                "active_threads": self.active_threads_label.text(),
                "errors_count": self.errors_count_label.text(),
                "elapsed_time": self.elapsed_time_label.text(),
                "eta": self.eta_label.text(),
                "last_sync": self.last_sync_label.text()
            }
            
            filename = f"otzaria_sync_stats_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            
            import json
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(stats_data, f, indent=2, ensure_ascii=False)
            
            return filename
            
        except Exception as e:
            print(f"שגיאה בייצוא סטטיסטיקות: {e}")
            return None
    
    def update_stats(self, books=None, size_mb=None, last_sync=None, speed=None):
        """מתודה לתאימות לאחור עם הקוד הישן"""
        try:
            stats_dict = {}
            if books is not None:
                stats_dict['books_count'] = books
            if size_mb is not None:
                stats_dict['total_size_mb'] = size_mb
            if last_sync is not None:
                stats_dict['last_sync'] = last_sync
            if speed is not None:
                stats_dict['download_speed'] = speed
            
            # קריאה למתודה החדשה
            self.update_real_time_stats(stats_dict)
            
        except Exception as e:
            print(f"שגיאה בעדכון סטטיסטיקות (תאימות לאחור): {e}")



class ShortcutManager:
    """מנהל קיצורי מקלדת"""
    
    def __init__(self, main_window):
        self.main_window = main_window
        self.shortcuts = {}
        self.descriptions = {}
        
    def setup_shortcuts(self):
        """הגדרת כל קיצורי המקלדת"""
        try:
            # קיצורי פעולות בסיסיות
            self.add_shortcut("Ctrl+S", self._start_sync, "התחלת תהליך סנכרון")
            self.add_shortcut("Ctrl+P", self._toggle_pause, "השהיה/המשכה של התהליך")
            self.add_shortcut("Ctrl+Q", self._quit_application, "יציאה מהאפליקציה")
            self.add_shortcut("Ctrl+O", self._open_folder_dialog, "פתיחת דיאלוג בחירת תיקיה")
            
            # קיצורי ערכת נושא וגופן
            self.add_shortcut("Ctrl+D", self._toggle_theme, "החלפה בין מצב כהה לבהיר")
            self.add_shortcut("Ctrl+Shift+R", self._refresh_theme, "רענון ערכת נושא")
            self.add_shortcut("Ctrl++", self._increase_font, "הגדלת גודל גופן")
            self.add_shortcut("Ctrl+-", self._decrease_font, "הקטנת גודל גופן")
            self.add_shortcut("Ctrl+0", self._reset_font, "איפוס גודל גופן לברירת מחדל")
            
            # קיצורי עזרה ומידע
            self.add_shortcut("F1", self._show_help, "הצגת עזרה וקיצורי מקלדת")
            self.add_shortcut("Ctrl+I", self._show_info, "הצגת מידע על האפליקציה")
            
            # קיצורי ניווט
            self.add_shortcut("Ctrl+1", lambda: self._switch_tab(0), "מעבר לטאב סנכרון")
            self.add_shortcut("Ctrl+2", lambda: self._switch_tab(1), "מעבר לטאב הגדרות")
            self.add_shortcut("Ctrl+3", lambda: self._switch_tab(2), "מעבר לטאב סטטיסטיקות")
            
            # קיצורי פעולות מתקדמות
            self.add_shortcut("Ctrl+R", self._reset_data, "איפוס מצב התקדמות")
            self.add_shortcut("Ctrl+E", self._export_stats, "ייצוא סטטיסטיקות")
            self.add_shortcut("Escape", self._cancel_operation, "ביטול פעולה נוכחית")
            
            # קיצורי מקלדת לשליטה על איזור היומן
            self.add_shortcut("Ctrl+Up", self._expand_log, "הגדלת איזור יומן הפעולות")
            self.add_shortcut("Ctrl+Down", self._shrink_log, "הקטנת איזור יומן הפעולות")
            
            return True
            
        except Exception as e:
            print(f"שגיאה בהגדרת קיצורי מקלדת: {e}")
            return False
    
    def add_shortcut(self, key_sequence, callback, description):
        """הוספת קיצור מקלדת"""
        try:
            # בדיקת התנגשות עם קיצורים קיימים
            if key_sequence in self.shortcuts:
                print(f"אזהרה: קיצור {key_sequence} כבר קיים")
                return False
            
            # יצירת QShortcut
            shortcut = QShortcut(QKeySequence(key_sequence), self.main_window)
            shortcut.activated.connect(callback)
            
            # שמירה במאגר
            self.shortcuts[key_sequence] = shortcut
            self.descriptions[key_sequence] = description
            
            return True
            
        except Exception as e:
            print(f"שגיאה בהוספת קיצור {key_sequence}: {e}")
            return False
    
    def remove_shortcut(self, key_sequence):
        """הסרת קיצור מקלדת"""
        try:
            if key_sequence in self.shortcuts:
                self.shortcuts[key_sequence].deleteLater()
                del self.shortcuts[key_sequence]
                del self.descriptions[key_sequence]
                return True
            return False
        except Exception as e:
            print(f"שגיאה בהסרת קיצור {key_sequence}: {e}")
            return False
    
    def _start_sync(self):
        """התחלת תהליך סנכרון"""
        try:
            if hasattr(self.main_window, 'btn_load_manifests') and self.main_window.btn_load_manifests.isEnabled():
                self.main_window.load_manifests()
            elif hasattr(self.main_window, 'btn_download_updates') and self.main_window.btn_download_updates.isEnabled():
                self.main_window.download_updates()
            elif hasattr(self.main_window, 'btn_apply_updates') and self.main_window.btn_apply_updates.isEnabled():
                self.main_window.apply_updates()
        except Exception as e:
            print(f"שגיאה בהתחלת סנכרון: {e}")
    
    def _toggle_pause(self):
        """השהיה/המשכה של התהליך"""
        try:
            if hasattr(self.main_window, 'btn_pause') and self.main_window.btn_pause.isEnabled():
                self.main_window.toggle_pause()
        except Exception as e:
            print(f"שגיאה בהשהיה/המשכה: {e}")
    
    def _quit_application(self):
        """יציאה מהאפליקציה"""
        try:
            self.main_window.close()
        except Exception as e:
            print(f"שגיאה ביציאה מהאפליקציה: {e}")
    
    def _open_folder_dialog(self):
        """פתיחת דיאלוג בחירת תיקיה"""
        try:
            if hasattr(self.main_window, 'select_folder_manually'):
                self.main_window.select_folder_manually()
        except Exception as e:
            print(f"שגיאה בפתיחת דיאלוג תיקיה: {e}")
    
    def _toggle_theme(self):
        """החלפה בין ערכות נושא"""
        try:
            if hasattr(self.main_window, 'theme_manager'):
                self.main_window.theme_manager.toggle_theme(self.main_window)
        except Exception as e:
            print(f"שגיאה בהחלפת ערכת נושא: {e}")
    
    def _refresh_theme(self):
        """רענון ערכת נושא"""
        try:
            if hasattr(self.main_window, 'refresh_theme'):
                self.main_window.refresh_theme()
                self.main_window.status_bar.showMessage("ערכת הנושא רוענה", 2000)
        except Exception as e:
            print(f"שגיאה ברענון ערכת נושא: {e}")
    
    def _increase_font(self):
        """הגדלת גודל גופן"""
        try:
            if hasattr(self.main_window, 'font_manager'):
                success = self.main_window.font_manager.increase_font_size(self.main_window)
                if success:
                    self.main_window.status_bar.showMessage(f"גודל גופן: {self.main_window.font_manager.current_font_size}", 2000)
        except Exception as e:
            print(f"שגיאה בהגדלת גופן: {e}")
    
    def _decrease_font(self):
        """הקטנת גודל גופן"""
        try:
            if hasattr(self.main_window, 'font_manager'):
                success = self.main_window.font_manager.decrease_font_size(self.main_window)
                if success:
                    self.main_window.status_bar.showMessage(f"גודל גופן: {self.main_window.font_manager.current_font_size}", 2000)
        except Exception as e:
            print(f"שגיאה בהקטנת גופן: {e}")
    
    def _reset_font(self):
        """איפוס גודל גופן"""
        try:
            if hasattr(self.main_window, 'font_manager'):
                success = self.main_window.font_manager.reset_to_default(self.main_window)
                if success:
                    self.main_window.status_bar.showMessage("גודל גופן אופס לברירת מחדל", 2000)
        except Exception as e:
            print(f"שגיאה באיפוס גופן: {e}")
    
    def _switch_tab(self, tab_index):
        """מעבר לטאב ספציפי"""
        try:
            if hasattr(self.main_window, 'tab_widget'):
                if 0 <= tab_index < self.main_window.tab_widget.count():
                    self.main_window.tab_widget.setCurrentIndex(tab_index)
        except Exception as e:
            print(f"שגיאה במעבר לטאב: {e}")
    
    def _reset_data(self):
        """איפוס מצב התקדמות"""
        try:
            if hasattr(self.main_window, 'reset_data'):
                self.main_window.reset_data()
        except Exception as e:
            print(f"שגיאה באיפוס נתונים: {e}")
    
    def _export_stats(self):
        """ייצוא סטטיסטיקות"""
        try:
            if hasattr(self.main_window, 'stats_widget'):
                filename = self.main_window.stats_widget.export_stats()
                if filename:
                    self.main_window.status_bar.showMessage(f"סטטיסטיקות יוצאו ל: {filename}", 3000)
        except Exception as e:
            print(f"שגיאה בייצוא סטטיסטיקות: {e}")
    
    def _cancel_operation(self):
        """ביטול פעולה נוכחית"""
        try:
            if hasattr(self.main_window, 'btn_cancel') and self.main_window.btn_cancel.isEnabled():
                self.main_window.cancel_operation()
        except Exception as e:
            print(f"שגיאה בביטול פעולה: {e}")
    
    def _expand_log(self):
        """הגדלת איזור יומן הפעולות"""
        try:
            if hasattr(self.main_window, 'expand_log_area'):
                self.main_window.expand_log_area()
        except Exception as e:
            print(f"שגיאה בהגדלת איזור היומן: {e}")
    
    def _shrink_log(self):
        """הקטנת איזור יומן הפעולות"""
        try:
            if hasattr(self.main_window, 'shrink_log_area'):
                self.main_window.shrink_log_area()
        except Exception as e:
            print(f"שגיאה בהקטנת איזור היומן: {e}")
    
    def _show_help(self):
        """הצגת דיאלוג עזרה"""
        self.show_help_dialog()
    
    def _show_info(self):
        """הצגת מידע על האפליקציה"""
        try:
            hebrew_info_dialog(
                self.main_window,
                "אודות אוצריא - סנכרון אופליין",
                "אוצריא - סנכרון אופליין\n"
                 "גרסה 3.2.1\n\n"
                "תוכנה לסנכרון ספרי אוצריא ללא חיבור אינטרנט\n\n"
                "פותח על ידי מתנדבי אוצריא  להצלחת לומדי התורה הקדושה\n"
                "ובפרט אלו שזכו להתנתק מהרשת לגמרי, אשריהם ואשרי חלקם!!!\n\n"
                "לחץ F1 לקבלת עזרה וקיצורי מקלדת"
            )
        except Exception as e:
            print(f"שגיאה בהצגת מידע: {e}")
    
    def show_help_dialog(self):
        """הצגת דיאלוג עזרה עם קיצורי מקלדת"""
        try:
            help_text = "קיצורי מקלדת זמינים:\n\n"
            
            # קיבוץ קיצורים לפי קטגוריות
            categories = {
                "פעולות בסיסיות": ["Ctrl+S", "Ctrl+P", "Ctrl+Q", "Ctrl+O", "Escape"],
                "ערכת נושא וגופן": ["Ctrl+D", "Ctrl++", "Ctrl+-", "Ctrl+0"],
                "ניווט": ["Ctrl+1", "Ctrl+2", "Ctrl+3"],
                "פעולות מתקדמות": ["Ctrl+R", "Ctrl+E", "Ctrl+Up", "Ctrl+Down"],
                "עזרה": ["F1", "Ctrl+I"]
            }
            
            for category, shortcuts in categories.items():
                help_text += f"{category}:\n"
                for shortcut in shortcuts:
                    if shortcut in self.descriptions:
                        help_text += f"  {shortcut} - {self.descriptions[shortcut]}\n"
                help_text += "\n"
            
            # יצירת דיאלוג עזרה
            help_dialog = QMessageBox(self.main_window)
            help_dialog.setWindowTitle("עזרה - קיצורי מקלדת")
            help_dialog.setText(help_text)
            help_dialog.setIcon(QMessageBox.Icon.Information)
            help_dialog.setStandardButtons(QMessageBox.StandardButton.Ok)
            
            # הגדרת גודל החלון
            help_dialog.setMinimumWidth(500)
            help_dialog.setMinimumHeight(400)
            
            help_dialog.exec()
            
        except Exception as e:
            print(f"שגיאה בהצגת עזרה: {e}")
    
    def get_shortcuts_list(self):
        """קבלת רשימת כל הקיצורים"""
        return list(self.shortcuts.keys())
    
    def get_shortcut_description(self, key_sequence):
        """קבלת תיאור קיצור"""
        return self.descriptions.get(key_sequence, "")
    
    def is_shortcut_available(self, key_sequence):
        """בדיקה האם קיצור זמין"""
        return key_sequence not in self.shortcuts

class OtzariaSync(QMainWindow):
    def __init__(self):
        super().__init__()
        self.worker = None
        self.is_paused = False
        self.is_cancelled = False
        self.state_manager = StateManager()
        
        # הגדרות אפליקציה
        self.settings = QSettings("OtzariaSync", "Settings")
        
        # אתחול כל המנהלים
        try:
            self.animation_manager = AnimationManager()
            self.icon_manager = IconManager()
            self.theme_manager = ThemeManager(self.settings)
            self.font_manager = FontManager(self.settings)
            self.shortcut_manager = ShortcutManager(self)
            
            print("כל המנהלים אותחלו בהצלחה")
        except Exception as e:
            print(f"שגיאה באתחול מנהלים: {e}")
            # fallback למנהלים בסיסיים
            self.animation_manager = None
            self.icon_manager = IconManager()
            self.theme_manager = None
            self.font_manager = None
            self.shortcut_manager = None
        
        # סטטיסטיקות
        self.total_books = 0
        self.total_size_mb = 0
        self.current_speed = 0
        
        # מעקב טאבים לאנימציות
        self._previous_tab_index = 0
        
        # אתחול UI
        self.initUI()
        
        # הגדרת קיצורי מקלדת
        if self.shortcut_manager:
            self.shortcut_manager.setup_shortcuts()
        
        # החלת ערכת נושא וגופן
        self.apply_initial_settings()
        
    def initUI(self):
        self.setWindowTitle("אוצריא - סנכרון אופליין")
        
        # התאמת גודל חלון למסך
        screen = QApplication.primaryScreen().availableGeometry()
        window_width = min(1200, int(screen.width() * 0.85))
        window_height = min(700, int(screen.height() * 0.85))
        
        self.setGeometry(100, 100, window_width, window_height)
        self.setMinimumSize(600, 400)  # הקטנת מינימום
        self.setMaximumSize(screen.width(), screen.height())
        
        # הפעלת כפתור הרחבה למסך מלא
        self.setWindowFlags(self.windowFlags() | Qt.WindowType.WindowMaximizeButtonHint)
        
        self.setWindowIcon(self.load_icon_from_base64(icon_base64))
        self.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
        
        # הסרת תפריט עליון (לפי בקשת המשתמש)
        # self.create_menu_bar()  # מוסתר - קיצורי מקלדת עדיין פעילים
        
        # יצירת status bar
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.status_bar.showMessage("מוכן לפעולה")
        
        # Widget מרכזי עם גלילה
        central_widget = QWidget()
        scroll_area = QScrollArea()
        scroll_area.setWidget(central_widget)
        scroll_area.setWidgetResizable(True)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.setCentralWidget(scroll_area)
        
        # Layout ראשי
        main_layout = QVBoxLayout()
        main_layout.setSpacing(10)  # הקטנת spacing
        main_layout.setContentsMargins(15, 15, 15, 15)  # הקטנת margins
        
        # יצירת טאבים
        self.tab_widget = QTabWidget()
        
        # חיבור אנימציות טאבים
        if self.animation_manager:
            self.tab_widget.currentChanged.connect(self.on_tab_changed)
        
        # טאב ראשי - סנכרון
        sync_tab = QWidget()
        sync_layout = QVBoxLayout()
        
        # טאב הגדרות
        settings_tab = QWidget()
        settings_layout = QVBoxLayout()
        
        # טאב סטטיסטיקות
        stats_tab = QWidget()
        stats_layout = QVBoxLayout()
        
        # === טאב סנכרון ===
        # כותרת עם אנימציה
        title_label = QLabel("אוצריא - סנכרון אופליין")
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title_font = QFont()
        title_font.setPointSize(20)
        title_font.setBold(True)
        title_label.setFont(title_font)
        title_label.setStyleSheet("color: #2E4057; margin-bottom: 0px; padding: 1px;")
        
        # תת-כותרת
        subtitle_label = QLabel("תוכנה לסנכרון ספרי אוצריא ללא חיבור אינטרנט")
        subtitle_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        subtitle_label.setStyleSheet("color: #5A6C7D; margin-bottom: 10px; font-size: 14px;")
        
        # מסגרת לכפתורים
        buttons_frame = QFrame()
        buttons_frame.setFrameStyle(QFrame.Shape.StyledPanel)
        buttons_frame.setStyleSheet("QFrame { background-color: #F8F9FA; border-radius: 10px; }")
        buttons_layout = QVBoxLayout()
        buttons_layout.setSpacing(8)  # הקטנה נוספת
        buttons_layout.setContentsMargins(12, 12, 12, 12)  # הקטנה נוספת
        
        # כפתורים משופרים עם אייקונים
        self.btn_load_manifests = AnimatedButton("   טען קבצי נתוני ספרים")
        self.btn_load_manifests.setIcon(self.icon_manager.get_icon('folder', size=24))
        self.btn_load_manifests.setIconSize(QSize(24, 24))
        self.btn_load_manifests.setToolTip("מחפש את תיקיית אוצריא במחשב, וטוען את קבצי המניפסט מתיקיית התוכנה\nקיצור מקלדת: Ctrl+S")
        self.btn_load_manifests.setMinimumHeight(50)  # הקטנה מ-60 ל-50
        self.btn_load_manifests.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        original_style = """
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #4CAF50, stop:1 #45a049);
                color: white;
                border: none;
                border-radius: 12px;
                font-size: 16px;
                font-weight: bold;
                padding: 10px;
            }
        """
        hover_style = """
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #5CBF60, stop:1 #4CAF50);
                color: white;
                border: none;
                border-radius: 12px;
                font-size: 16px;
                font-weight: bold;
                padding: 10px;
            }
        """
        self.btn_load_manifests.set_styles(original_style, hover_style)
        self.btn_load_manifests.set_disabled_opacity(0.3)  # שקיפות חזקה יותר
        self.btn_load_manifests.clicked.connect(self.load_manifests)
        
        # כפתור 2
        self.btn_download_updates = AnimatedButton("   הורד קבצים חדשים וקבצים שהתעדכנו")
        self.btn_download_updates.setIcon(self.icon_manager.get_icon('download', size=24))
        self.btn_download_updates.setIconSize(QSize(24, 24))
        self.btn_download_updates.setToolTip("מוריד קבצים חדשים ומעודכנים מהשרת\nזמין רק לאחר טעינת קבצי הנתונים")
        self.btn_download_updates.setMinimumHeight(50)  # הקטנה מ-60 ל-50
        self.btn_download_updates.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        original_style2 = """
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #2196F3, stop:1 #1976D2);
                color: white;
                border: none;
                border-radius: 12px;
                font-size: 16px;
                font-weight: bold;
                padding: 10px;
            }
        """
        hover_style2 = """
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #42A5F5, stop:1 #2196F3);
                color: white;
                border: none;
                border-radius: 12px;
                font-size: 16px;
                font-weight: bold;
                padding: 10px;
            }
        """
        self.btn_download_updates.set_styles(original_style2, hover_style2)
        self.btn_download_updates.set_disabled_opacity(0.3)  # שקיפות חזקה יותר
        self.btn_download_updates.clicked.connect(self.download_updates)
        self.btn_download_updates.setEnabled(False)
        
        # כפתור 3
        self.btn_apply_updates = AnimatedButton("   עדכן שינויים לתוך מאגר הספרים")
        self.btn_apply_updates.setIcon(self.icon_manager.get_icon('sync', size=24))
        self.btn_apply_updates.setIconSize(QSize(24, 24))
        self.btn_apply_updates.setToolTip("מעתיק את הקבצים החדשים לתיקיית אוצריא\nזמין רק לאחר הורדת העדכונים")
        self.btn_apply_updates.setMinimumHeight(50)  # הקטנה מ-60 ל-50
        self.btn_apply_updates.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        original_style3 = """
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #FF9800, stop:1 #F57C00);
                color: white;
                border: none;
                border-radius: 12px;
                font-size: 16px;
                font-weight: bold;
                padding: 10px;
            }
        """
        hover_style3 = """
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #FFB74D, stop:1 #FF9800);
                color: white;
                border: none;
                border-radius: 12px;
                font-size: 16px;
                font-weight: bold;
                padding: 10px;
            }
        """
        self.btn_apply_updates.set_styles(original_style3, hover_style3)
        self.btn_apply_updates.set_disabled_opacity(0.3)  # שקיפות חזקה יותר
        self.btn_apply_updates.clicked.connect(self.apply_updates)
        self.btn_apply_updates.setEnabled(False)
        
        # כפתורי בקרה
        control_layout = QHBoxLayout()
        control_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)  # מרכוז הכפתורים
        
        self.btn_pause = AnimatedButton("   השהה")
        self.btn_pause.setIcon(self.icon_manager.get_icon('pause', size=16))
        self.btn_pause.setIconSize(QSize(16, 16))
        self.btn_pause.setToolTip("השהה או המשך את התהליך הנוכחי\nקיצור מקלדת: Ctrl+P")
        self.btn_pause.setMinimumHeight(40)
        self.btn_pause.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)  # רוחב קבוע
        self.btn_pause.setMinimumWidth(120)  # רוחב מינימלי
        pause_original_style = """
            QPushButton {
                background-color: #FF9800 !important;
                color: white !important;
                border: none !important;
                border-radius: 5px !important;
                font-size: 12px !important;
            }
            QPushButton:pressed {
                background-color: #E65100 !important;
                border-radius: 5px !important;
            }
        """
        pause_hover_style = """
            QPushButton:hover:enabled {
                background-color: #F57C00 !important;
                border-radius: 5px !important;
            }
        """
        self.btn_pause.set_styles(pause_original_style, pause_hover_style)
        self.btn_pause.set_disabled_opacity(0.5)  # שקיפות בינונית
        self.btn_pause.clicked.connect(self.toggle_pause)
        self.btn_pause.setEnabled(False)
        
        self.btn_cancel = AnimatedButton("   בטל")
        self.btn_cancel.setIcon(self.icon_manager.get_icon('stop', size=16))
        self.btn_cancel.setIconSize(QSize(16, 16))
        self.btn_cancel.setToolTip("בטל את התהליך הנוכחי\nקיצור מקלדת: Escape")
        self.btn_cancel.setMinimumHeight(40)
        self.btn_cancel.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)  # רוחב קבוע
        self.btn_cancel.setMinimumWidth(120)  # רוחב מינימלי
        cancel_complete_style = """
            QPushButton {
                background-color: #f44336 !important;
                color: white !important;
                border: none !important;
                border-radius: 5px !important;
                font-size: 12px !important;
            }
            QPushButton:hover:enabled {
                background-color: #da190b !important;
                border-radius: 5px !important;
            }
            QPushButton:pressed {
                background-color: #c62828 !important;
                border-radius: 5px !important;
            }
        """
        self.btn_cancel.set_disabled_opacity(0.5)  # שקיפות בינונית
        # החלה מיידית של הסגנון המלא
        self.btn_cancel.setStyleSheet(cancel_complete_style)
        self.btn_cancel.clicked.connect(self.cancel_operation)
        self.btn_cancel.setEnabled(False)

        self.btn_reset_data = AnimatedButton("   איפוס מצב")
        self.btn_reset_data.setIcon(self.icon_manager.get_icon('refresh', size=16))
        self.btn_reset_data.setIconSize(QSize(16, 16))
        self.btn_reset_data.setToolTip("מאפס את מצב ההתקדמות ומתחיל מחדש\nקיצור מקלדת: Ctrl+R")
        self.btn_reset_data.setMinimumHeight(40)
        self.btn_reset_data.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)  # רוחב קבוע
        self.btn_reset_data.setMinimumWidth(120)  # רוחב מינימלי (הכפתור הרחב ביותר)
        reset_complete_style = """
            QPushButton {
                background-color: #9C27B0 !important;
                color: white !important;
                border: none !important;
                border-radius: 5px !important;
                font-size: 12px !important;
            }
            QPushButton:hover:enabled {
                background-color: #7B1FA2 !important;
                border-radius: 5px !important;
            }
            QPushButton:pressed {
                background-color: #6A1B9A !important;
                border-radius: 5px !important;
            }
        """
        self.btn_reset_data.set_disabled_opacity(0.5)  # שקיפות בינונית
        self.btn_reset_data.clicked.connect(self.reset_data)
        self.btn_reset_data.setEnabled(False)  # שיפור UX: לא פעיל בפתיחת התוכנה, רק אחרי שלב ראשון
        
        # החלת הסגנון המלא מיד
        self.btn_reset_data.setStyleSheet(reset_complete_style)

        # שיפורי UX שבוצעו:
        # 1. כפתורי 'השהה' ו'בטל' פעילים רק במהלך פעולות
        # 2. כפתור 'איפוס מצב' פעיל רק אחרי שלב ראשון
        # 3. איזור יומן הפעולות ניתן להגדלה/הקטנה עם כפתורים וקיצורי מקלדת

        # כפתור בחירה ידנית
        self.btn_manual_select = QPushButton("📁 בחר תיקיה ידנית")
        self.btn_manual_select.setMinimumHeight(40)
        self.btn_manual_select.setStyleSheet("""
            QPushButton {
                border-radius: 8px;
                background-color: #607D8B;
                color: white;
                font-weight: bold;
                font-size: 12px;
            }
            QPushButton:hover {
                background-color: #546E7A;
            }
        """)
        self.btn_manual_select.clicked.connect(self.show_manual_selection)
        self.btn_manual_select.setVisible(False)  # מוסתר בהתחלה

        # Progress bar משופר
        self.progress_bar = EnhancedProgressBar()
        self.progress_bar.setVisible(False)
        self.progress_bar.setMinimumHeight(30)
        self.progress_bar.setStyleSheet("""
            QProgressBar {
                border: 2px solid #E0E0E0;
                border-radius: 15px;
                text-align: center;
                font-weight: bold;
                font-size: 12px;
                background-color: #F5F5F5;
            }
            QProgressBar::chunk {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, 
                    stop:0 #4CAF50, stop:0.5 #66BB6A, stop:1 #4CAF50);
                border-radius: 13px;
                margin: 2px;
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
        
        # Log text area with resizable functionality
        self.log_text = QTextEdit()
        self.log_text.setMinimumHeight(80)   # גובה מינימלי
        self.log_text.setMaximumHeight(300)  # גובה מקסימלי מוגדל
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

        # הוספת רכיבים לטאב סנכרון
        sync_layout.addWidget(title_label)
        sync_layout.addWidget(subtitle_label)
        sync_layout.addWidget(self.status_label)
        
        # שורה ראשונה - שלושת הכפתורים הראשיים באותה שורה
        main_buttons_row = QHBoxLayout()
        main_buttons_row.setSpacing(10)
        main_buttons_row.addWidget(self.btn_load_manifests)
        main_buttons_row.addWidget(self.btn_download_updates)
        main_buttons_row.addWidget(self.btn_apply_updates)
        buttons_layout.addLayout(main_buttons_row)
        
        # שורה שנייה - כפתור בחירה ידנית (יוצג רק כשצריך)
        manual_select_row = QHBoxLayout()
        manual_select_row.addWidget(self.btn_manual_select)
        buttons_layout.addLayout(manual_select_row)
        
        buttons_frame.setLayout(buttons_layout)
        sync_layout.addWidget(buttons_frame)
        
        sync_layout.addWidget(self.step_label)
        sync_layout.addWidget(self.progress_bar)
        
        control_layout.addWidget(self.btn_pause)
        control_layout.addWidget(self.btn_cancel)
        control_layout.addWidget(self.btn_reset_data)
        buttons_layout.addLayout(control_layout)
        
        # יומן פעולות עם כפתורי שליטה - שיפור UI לאפשר הגדלה/הקטנה של איזור היומן
        log_header_layout = QHBoxLayout()
        log_label = QLabel("יומן פעולות:")
        log_label.setStyleSheet("margin-bottom: 5px; margin-top: 10px; font-weight: bold; font-size: 14px;")
        
        # כפתורי שליטה על גודל יומן הפעולות
        self.btn_expand_log = QPushButton("▲")
        self.btn_expand_log.setMaximumWidth(30)
        self.btn_expand_log.setMaximumHeight(25)
        self.btn_expand_log.setToolTip("הגדל את איזור יומן הפעולות\nקיצור מקלדת: Ctrl+⬆")
        self.btn_expand_log.setStyleSheet("""
            QPushButton {
                background-color: #E3F2FD;
                border: 1px solid #BBDEFB;
                border-radius: 3px;
                font-size: 12px;
            }
            QPushButton:hover {
                background-color: #BBDEFB;
            }
        """)
        self.btn_expand_log.clicked.connect(self.expand_log_area)
        
        self.btn_shrink_log = QPushButton("▼")
        self.btn_shrink_log.setMaximumWidth(30)
        self.btn_shrink_log.setMaximumHeight(25)
        self.btn_shrink_log.setToolTip("הקטן את איזור יומן הפעולות\nקיצור מקלדת: Ctrl+⬇")
        self.btn_shrink_log.setStyleSheet("""
            QPushButton {
                background-color: #E3F2FD;
                border: 1px solid #BBDEFB;
                border-radius: 3px;
                font-size: 12px;
            }
            QPushButton:hover {
                background-color: #BBDEFB;
            }
        """)
        self.btn_shrink_log.clicked.connect(self.shrink_log_area)
        
        log_header_layout.addWidget(log_label)
        log_header_layout.addStretch()
        log_header_layout.addWidget(self.btn_shrink_log)
        log_header_layout.addWidget(self.btn_expand_log)
        
        sync_layout.addLayout(log_header_layout)
        sync_layout.addWidget(self.log_text)
        
        sync_tab.setLayout(sync_layout)
        
        # === טאב הגדרות ===
        self.setup_enhanced_settings_tab(settings_layout)
        settings_tab.setLayout(settings_layout)
        
        # === טאב סטטיסטיקות ===
        self.stats_widget = AdvancedStatsWidget()
        stats_layout.addWidget(self.stats_widget)
        
        # גרף התקדמות (placeholder)
        progress_group = QGroupBox("התקדמות כללית")
        progress_layout = QVBoxLayout()
        
        self.overall_progress = QProgressBar()
        self.overall_progress.setStyleSheet("""
            QProgressBar {
                border: 2px solid #E0E0E0;
                border-radius: 10px;
                text-align: center;
                font-weight: bold;
                background-color: #F5F5F5;
            }
            QProgressBar::chunk {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, 
                    stop:0 #2196F3, stop:1 #42A5F5);
                border-radius: 8px;
                margin: 2px;
            }
        """)
        progress_layout.addWidget(self.overall_progress)
        progress_group.setLayout(progress_layout)
        stats_layout.addWidget(progress_group)
        
        stats_layout.addStretch()
        stats_tab.setLayout(stats_layout)
        
        # === טאב הוראות והדרכות ===
        instructions_tab = QWidget()
        instructions_layout = QVBoxLayout()
        
        # יצירת scroll area לתוכן ההדרכות
        instructions_scroll = QScrollArea()
        instructions_scroll.setWidgetResizable(True)
        instructions_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        instructions_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        
        # Widget לתוכן ההדרכות
        instructions_content = QWidget()
        instructions_content_layout = QVBoxLayout()
        
        # תוכן ההדרכות עם HTML ו-CSS
        instructions_text = QTextEdit()
        instructions_text.setReadOnly(True)
        instructions_text.setHtml("""
        <style>
            body {
                font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                direction: rtl;
                text-align: right;
                padding: 20px;
                background-color: #f9f9f9;
            }
            h1 {
                color: #2E4057;
                border-bottom: 3px solid #4CAF50;
                padding-bottom: 10px;
                margin-top: 20px;
                margin-bottom: 20px;
                font-size: 28px;
            }
            h2 {
                color: #1976D2;
                margin-top: 25px;
                margin-bottom: 15px;
                font-size: 22px;
                border-right: 5px solid #2196F3;
                padding-right: 10px;
            }
            /* עיצוב כותרות בתוך הטבלאות */
            td h3 {
                color: #FF9800;
                margin-top: 0;
                margin-bottom: 5px;
                font-size: 18px;
            }
            /* צבע כותרת שונה בתוך ההודעה האדומה */
            .red-box h3 {
                color: #D32F2F; 
                text-align: center;
            }
            /* צבע כותרת בתוך השלבים */
            .blue-box h3 {
                color: #1565C0;
            }
            p {
                line-height: 1.6;
                margin-bottom: 10px;
                font-size: 15px;
                color: #333;
            }
            ul {
                margin-top: 0;
                margin-bottom: 10px;
            }
            li {
                margin-bottom: 5px;
            }
            code {
                background-color: #f0f0f0;
                padding: 2px 6px;
                font-family: 'Courier New', monospace;
                font-size: 13px;
                color: #d63384;
            }
            a {
                color: #2196F3;
                text-decoration: none;
                font-weight: bold;
            }
            /* מחלקות עזר לטבלאות */
            .tips-table {
                margin-top: 15px;
                margin-bottom: 15px;
            }
            td.red-box {
                text-align: center;
            }

            td.red-box h3 {
                color: #D32F2F;
            }                                  
        </style>
        <p></p>
        <h1>📚 מדריך שימוש - תוכנת סנכרון אוצריא אופליין</h1>
        <p></p>
        <!-- הודעה חשובה - בתוך טבלה כדי להבטיח רצף צבע -->
        <table width="100%" bgcolor="#FFEBEE" border="0" cellpadding="15" cellspacing="0" style="margin-bottom: 20px; border-right: 6px solid #F44336;">
            <tr>
                <td class="red-box">
                    <h3>⚠️ הודעה חשובה למשתמשים עם גירסת ספרייה 53 ומטה</h3>
                    <p>אם יש לך גירסת ספרייה מספר 53 או נמוך מזה, תוכנת הסנכרון אופליין תצטרך להוריד את כל המאגר כולו מחדש עקב שינויים במבנה הספרייה באתר.</p>
                    <p><strong>מכיוון שזה לוקח המון זמן, מומלץ מאוד להוריד את המאגר כולו מחדש דרך קובץ הזיפ מכאן:</strong>
                    <br><a href="https://github.com/Y-PLONI/otzaria-library/releases/download/latest/otzaria_latest.zip">https://github.com/Y-PLONI/otzaria-library/releases/download/latest/otzaria_latest.zip</a>
                    <br>ולהשתמש בתוכנה זו רק בשביל הסנכרונים הבאים</p>
                </td>
            </tr>
        </table>
        
        <h2>🎯 מהי תוכנת הסנכרון?</h2>
        <p>תוכנת הסנכרון האופליין של אוצריא מאפשרת לך לעדכן את ספריית אוצריא שלך ללא צורך לחבר את המחשב שלך לרשת האינטרנט.<br>
        התוכנה מורידה את הקבצים החדשים והמעודכנים בלבד, וחוסכת לך זמן יקר, וכן ניצול חבילת הגלישה.</p>
        
        <h2>📋 שלבי השימוש</h2>
        
        <!-- שלבי השימוש - כולם בתוך טבלה אחת גדולה -->
        <table width="100%" bgcolor="#E3F2FD" border="0" cellpadding="15" cellspacing="0" style="margin-bottom: 20px; border-right: 6px solid #2196F3;">
            <tr>
                <td class="blue-box">
                    <!-- שלב 1 -->
                    <div style="margin-bottom: 20px;">
                        <h3>שלב 1: טעינת קבצי נתוני ספרים</h3>
                        <p>לחץ על הכפתור <strong>"טען קבצי נתוני ספרים"</strong> (או השתמש בקיצור <code>Ctrl+S</code>)</p>
                        <ul>
                            <li>התוכנה תחפש אוטומטית את תיקיית אוצריא במחשב שלך</li>
                            <li>אם התיקיה לא נמצאת, תוכל לבחור אותה ידנית</li>
                            <li>התוכנה תטען את קבצי המניפסט (רשימת הספרים והקבצים)</li>
                        </ul>
                    </div>

                    <!-- שלב 2 -->
                    <div style="margin-bottom: 20px;">
                        <h3>שלב 2: הורדת קבצים חדשים ומעודכנים</h3>
                        <p>לחץ על הכפתור <strong>"הורד קבצים חדשים וקבצים שהתעדכנו"</strong></p>
                        <ul>
                            <li>התוכנה תשווה בין הקבצים שלך לבין הגרסה העדכנית ביותר</li>
                            <li>תוריד רק את הקבצים החדשים והמעודכנים</li>
                            <li>תוכל לעקוב אחר ההתקדמות בסרגל ההתקדמות וביומן הפעולות</li>
                        </ul>
                    </div>

                    <!-- שלב 3 -->
                    <div style="margin-bottom: 0;">
                        <h3>שלב 3: עדכון שינויים למאגר הספרים</h3>
                        <p>לחץ על הכפתור <strong>"עדכן שינויים לתוך מאגר הספרים"</strong></p>
                        <ul>
                            <li>התוכנה תעתיק את הקבצים החדשים לתיקיית אוצריא</li>
                            <li>תמחק קבצים ישנים שכבר לא נחוצים</li>
                            <li>תעדכן את קבצי המניפסט</li>
                        </ul>
                    </div>
                </td>
            </tr>
        </table>
        
        <h2>💡 טיפים שימושיים</h2>
        
        <table width="100%" bgcolor="#E8F5E9" border="0" cellpadding="10" cellspacing="0" class="tips-table" style="border-right: 5px solid #4CAF50;">
            <tr><td>
                <h3 style="color: #2E7D32;">✅ טיפ 1: הכנס את קובץ התוכנה [הזאת] לתיקייה נפרדת</h3>
                <p style="margin-bottom: 0;"><strong>מומלץ מאוד!!</strong> להכניס את התוכנה לאחר ההורדה [לפני התחלת הסנכרון] לתיקיי' בפני עצמה, כי היא יוצרת הרבה קבצים במיקום שלה, וזה יכול לגרום לכם לבלגן.
                <br>אם לא עשיתם את זה עדיין, תוכלו עכשיו לסגור את התוכנה, ולהעביר אותה למיקום אחר, ואחר כך להפעיל אותה שוב.</p>
            </td></tr>
        </table>
        
        <table width="100%" bgcolor="#E8F5E9" border="0" cellpadding="10" cellspacing="0" class="tips-table" style="border-right: 5px solid #4CAF50;">
            <tr><td>
                <h3 style="color: #2E7D32;">✅ טיפ 2: הכנס את התוכנה לכונן נייד</h3>
                <p style="margin-bottom: 0;">הכנס את התוכנה לכונן נשלף, כמו דיסק אונקי או כרטיס זיכרון וכדו', כדי שתוכל להעבירה אח"כ בקלות לחדר המחשבים.</p>
            </td></tr>
        </table>
                                          
        <table width="100%" bgcolor="#E8F5E9" border="0" cellpadding="10" cellspacing="0" class="tips-table" style="border-right: 5px solid #4CAF50;">
            <tr><td>
                <h3 style="color: #2E7D32;">✅ טיפ 3: בדוק את גרסת הספרייה</h3>
                <p style="margin-bottom: 0;">פתח את <strong>"אודות"</strong> שבתוך תוכנת <strong>אוצריא</strong>, כדי לראות את גרסת הספרייה הנוכחית שלך. באם המידע לא קיים שם, תוכל לפתוח דרך סייר הקבצים את הקובץ בשם 'גרסת ספרייה' שנמצא בתיקיית 'אודות התוכנה'.</p>
            </td></tr>
        </table>
        
        <table width="100%" bgcolor="#E8F5E9" border="0" cellpadding="10" cellspacing="0" class="tips-table" style="border-right: 5px solid #4CAF50;">
            <tr><td>
                <h3 style="color: #2E7D32;">✅ טיפ 4: התאם אישית את התוכנה</h3>
                <p style="margin-bottom: 0;">בטאב <strong>"הגדרות"</strong> תוכל להתאים את ערכת הנושא, וגודל הגופן, לפי העדפותיך.</p>
            </td></tr>
        </table>
        
        <table width="100%" bgcolor="#E8F5E9" border="0" cellpadding="10" cellspacing="0" class="tips-table" style="border-right: 5px solid #4CAF50;">
            <tr><td>
                <h3 style="color: #2E7D32;">✅ טיפ 5: עקוב אחר ההתקדמות</h3>
                <p style="margin-bottom: 0;">יומן הפעולות מציג מידע מפורט על כל פעולה. אם משהו לא עובד כצפוי, בדוק את היומן לפרטים נוספים.
                <br>נסה לפתור את התקלה לפי ההדרכות ב 'פתרון בעיות נפוצות' (שנמצא בהמשך עמוד זה).<br>
                אם לא הסתדרת בעצמך, תוכל לשלוח אלינו את פירוט התקלה, בדרכים שמופיעים ב 'צור קשר ותמיכה'.</p>
            </td></tr>
        </table>
        
        <table width="100%" bgcolor="#FFF3E0" border="0" cellpadding="10" cellspacing="0" class="tips-table" style="border-right: 5px solid #FF9800;">
            <tr><td>
                <h3 style="color: #E65100;">⚠️ אזהרה: אל תסגור את התוכנה באמצע פעולה</h3>
                <p style="margin-bottom: 0;">סגירת התוכנה באמצע הורדה או עדכון עלולה לגרום לבעיות. השתמש בכפתור "בטל" כדי לעצור פעולה בצורה מסודרת.</p>
            </td></tr>
        </table>
               
        <h2>⌨️ קיצורי מקלדת</h2>
        <ul>
            <li><code>Ctrl+I</code> - הצגת מידע על האפליקציה</li>
            <li><code>F1</code> - הצגת עזרה וקיצורי מקלדת</li>
            <li><code>Ctrl+S</code> - טען קבצי נתוני ספרים</li>
            <li><code>Ctrl+P</code> - השהה/המשך פעולה</li>
            <li><code>Ctrl+R</code> - איפוס מצב</li>
            <li><code>Escape</code> - ביטול פעולה</li>
            <li><code>Ctrl+⬆</code> - הגדלת איזור יומן הפעולות</li>
            <li><code>Ctrl+⬇</code> - הקטנת איזור יומן הפעולות</li>
            <li><code>Ctrl+T</code> - החלפת ערכת נושא (בהיר/כהה)</li>
            <li><code>Ctrl++</code> - הגדלת גופן</li>
            <li><code>Ctrl+-</code> - הקטנת גופן</li>
            <li><code>Ctrl+1</code> - מעבר לטאב סנכרון</li>
            <li><code>Ctrl+2</code> - מעבר לטאב הגדרות</li>
            <li><code>Ctrl+3</code> - מעבר לטאב סטטיסטיקות</li>
            <li><code>Space</code> - השהה/המשך פעולה</li>
            <li><code>Ctrl+Shift+R</code> - רענון ערכת נושא</li>
            <li><code>Alt+1</code> - שלב ראשון (טעינת קבצי נתונים)</li>
            <li><code>Alt+2</code> - שלב שני (הורדת עדכונים)</li>
            <li><code>Alt+3</code> - שלב שלישי (החלת עדכונים)</li>
            <li><code>Ctrl+Q</code> - יציאה</li>
            <li><code>Ctrl+O</code> - פתיחת דיאלוג בחירת תיקיה</li>
            <li><code>Ctrl+0</code> - איפוס גודל גופן לברירת מחדל</li>
            <li><code>Ctrl+E</code> - ייצוא סטטיסטיקות</li>
        </ul>
                                                                                           
        <h2>🔧 פתרון בעיות נפוצות</h2>
        
        <h3>❓ התוכנה לא מוצאת את תיקיית אוצריא</h3>
        <p>לחץ על הכפתור <strong>"בחר תיקיה ידנית"</strong> שמופיע במהלך החיפוש, ובחר את התיקיה הנכונה.</p>
        
        <h3>❓ התוכנה תקועה</h3>
        <p>לחץ על כפתור <strong>"בטל"</strong> או על מקש <code>Escape</code>, ולאחר מכן על <strong>"איפוס מצב"</strong> כדי להתחיל מחדש.</p>
        
        <h2>📞 צור קשר ותמיכה</h2>
        <p>אם נתקלת בבעיה או שיש לך שאלה, אנא פנה לתמיכה דרך:</p>
        <ul>
            <li>פתיחת Issues בגיטהאב, בכתובת: <a href="https://github.com/YOSEFTT/OtzariaSyncOffline/issues">https://github.com/YOSEFTT/OtzariaSyncOffline/issues</a></li>
            <li>שליחת מייל, לכתובת: <a href="https://mail.google.com/mail/u/0/?view=cm&fs=1&to=otzaria.1%40gmail.com%E2%80%AC">otzaria.1@gmail.com</a></li>
        </ul>
        
        <p style="text-align: center; margin-top: 30px; color: #888; font-size: 13px;">
            תוכנת סנכרון אוצריא אופליין | גרסה 3.2.1 | MIT License
        </p>
        """)
        
        instructions_content_layout.addWidget(instructions_text)
        instructions_content.setLayout(instructions_content_layout)
        instructions_scroll.setWidget(instructions_content)
        instructions_layout.addWidget(instructions_scroll)
        instructions_tab.setLayout(instructions_layout)
        
        # הוספת טאבים
        self.tab_widget.addTab(sync_tab, "🔄 סנכרון")
        self.tab_widget.addTab(settings_tab, "⚙️ הגדרות")
        self.tab_widget.addTab(stats_tab, "📊 סטטיסטיקות")
        self.tab_widget.addTab(instructions_tab, "📖 הוראות והדרכות")
        
        main_layout.addWidget(self.tab_widget)
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
        
    def create_menu_bar(self):
        """יצירת מנו עליון"""
        menubar = self.menuBar()
        
        # מנו קובץ
        file_menu = menubar.addMenu('קובץ')
        
        # פעולות
        reset_action = QAction('איפוס מצב', self)
        reset_action.setShortcut('Ctrl+R')
        reset_action.triggered.connect(self.reset_state)
        file_menu.addAction(reset_action)
        
        file_menu.addSeparator()
        
        exit_action = QAction('יציאה', self)
        exit_action.setShortcut('Ctrl+Q')
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)
        
        # מנו תצוגה
        view_menu = menubar.addMenu('תצוגה')
        
        theme_action = QAction('החלף ערכת צבעים', self)
        theme_action.setShortcut('Ctrl+T')
        theme_action.triggered.connect(self.toggle_theme)
        view_menu.addAction(theme_action)
        
        font_increase = QAction('הגדל גופן', self)
        font_increase.setShortcut('Ctrl++')
        font_increase.triggered.connect(self.increase_font)
        view_menu.addAction(font_increase)
        
        font_decrease = QAction('הקטן גופן', self)
        font_decrease.setShortcut('Ctrl+-')
        font_decrease.triggered.connect(self.decrease_font)
        view_menu.addAction(font_decrease)
        
    def setup_settings_tab(self, layout):
        """הגדרת טאב ההגדרות"""
        # קבוצת ערכת צבעים
        theme_group = QGroupBox("ערכת צבעים")
        theme_layout = QVBoxLayout()
        
        self.dark_mode_checkbox = QCheckBox("מצב כהה")
        current_dark_mode = self.theme_manager.current_theme == "dark" if self.theme_manager else self.settings.value("dark_mode", False, type=bool)
        self.dark_mode_checkbox.setChecked(current_dark_mode)
        self.dark_mode_checkbox.toggled.connect(self.toggle_theme)
        theme_layout.addWidget(self.dark_mode_checkbox)
        
        theme_group.setLayout(theme_layout)
        layout.addWidget(theme_group)
        
        # קבוצת גופן
        font_group = QGroupBox("הגדרות גופן")
        font_layout = QVBoxLayout()
        
        font_size_layout = QHBoxLayout()
        font_size_layout.addWidget(QLabel("גודל גופן:"))
        
        self.font_slider = QSlider(Qt.Orientation.Horizontal)
        self.font_slider.setMinimum(8)
        self.font_slider.setMaximum(20)
        current_font_size = self.font_manager.current_font_size if self.font_manager else self.settings.value("font_size", 10, type=int)
        self.font_slider.setValue(current_font_size)
        self.font_slider.valueChanged.connect(self.change_font_size)
        
        self.font_size_label = QLabel(str(current_font_size))
        
        font_size_layout.addWidget(self.font_slider)
        font_size_layout.addWidget(self.font_size_label)
        
        font_layout.addLayout(font_size_layout)
        font_group.setLayout(font_layout)
        layout.addWidget(font_group)
        
        # קבוצת קיצורי מקלדת
        shortcuts_group = QGroupBox("קיצורי מקלדת")
        shortcuts_layout = QVBoxLayout()
        
        shortcuts_text = """
        Alt+1 - שלב ראשון (טעינת קבצי נתונים)
        Alt+2 - שלב שני (הורדת עדכונים)
        Alt+3 - שלב שלישי (החלת עדכונים)
        Ctrl+T - החלף ערכת צבעים
        Ctrl+Shift+R - רענון ערכת נושא
        Ctrl+R - איפוס מצב
        Ctrl++ - הגדל גופן
        Ctrl+- - הקטן גופן
        Ctrl+Up - הגדל איזור יומן הפעולות
        Ctrl+Down - הקטן איזור יומן הפעולות
        Space - השהה/המשך
        Escape - בטל פעולה
        """
        
        shortcuts_label = QLabel(shortcuts_text)
        shortcuts_label.setStyleSheet("font-family: monospace; background-color: #F5F5F5; padding: 10px; border-radius: 5px;")
        shortcuts_layout.addWidget(shortcuts_label)
        
        shortcuts_group.setLayout(shortcuts_layout)
        layout.addWidget(shortcuts_group)
        
        layout.addStretch()
        
    def setup_enhanced_settings_tab(self, layout):
        """הגדרת טאב הגדרות משופר"""
        
        # יצירת scroll area לטאב הגדרות
        scroll_area = QScrollArea()
        scroll_widget = QWidget()
        scroll_layout = QVBoxLayout()
        
        # === קבוצת ערכת נושא ===
        theme_group = QGroupBox("🎨 ערכת נושא")
        theme_layout = QVBoxLayout()
        
        # כפתורי בחירת ערכת נושא
        theme_buttons_layout = QHBoxLayout()
        
        self.light_theme_btn = QPushButton("☀️ בהיר")
        self.light_theme_btn.setCheckable(True)
        self.light_theme_btn.clicked.connect(lambda: self.set_theme_mode("light"))
        
        self.dark_theme_btn = QPushButton("🌙 כהה")
        self.dark_theme_btn.setCheckable(True)
        self.dark_theme_btn.clicked.connect(lambda: self.set_theme_mode("dark"))
        
        # הגדרת מצב נוכחי
        current_theme = self.theme_manager.current_theme if self.theme_manager else ("dark" if self.settings.value("dark_mode", False, type=bool) else "light")
        if current_theme == "light":
            self.light_theme_btn.setChecked(True)
        else:
            self.dark_theme_btn.setChecked(True)
        
        theme_buttons_layout.addWidget(self.light_theme_btn)
        theme_buttons_layout.addWidget(self.dark_theme_btn)
        theme_layout.addLayout(theme_buttons_layout)
        
        theme_group.setLayout(theme_layout)
        scroll_layout.addWidget(theme_group)
        
        # === קבוצת גופן ===
        font_group = QGroupBox("🔤 הגדרות גופן")
        font_layout = QVBoxLayout()
        
        # גודל גופן עם slider ו-spinbox
        font_size_layout = QHBoxLayout()
        font_size_layout.addWidget(QLabel("גודל גופן:"))
        
        current_font_size = self.font_manager.current_font_size if self.font_manager else self.settings.value("font_size", 10, type=int)
        
        self.font_slider_new = QSlider(Qt.Orientation.Horizontal)
        self.font_slider_new.setMinimum(8)
        self.font_slider_new.setMaximum(20)
        self.font_slider_new.setValue(current_font_size)
        self.font_slider_new.valueChanged.connect(self.on_font_slider_changed)
        
        from PyQt6.QtWidgets import QSpinBox
        self.font_spinbox = QSpinBox()
        self.font_spinbox.setMinimum(8)
        self.font_spinbox.setMaximum(20)
        self.font_spinbox.setValue(current_font_size)
        self.font_spinbox.valueChanged.connect(self.on_font_spinbox_changed)
        
        font_size_layout.addWidget(self.font_slider_new)
        font_size_layout.addWidget(self.font_spinbox)
        font_layout.addLayout(font_size_layout)
        
        # כפתורי גופן מהירים
        font_buttons_layout = QHBoxLayout()
        
        font_decrease_btn = QPushButton("➖ הקטן")
        font_decrease_btn.clicked.connect(self.decrease_font_size)
        
        font_reset_btn = QPushButton("🔄 איפוס")
        font_reset_btn.clicked.connect(self.reset_font_size)
        
        font_increase_btn = QPushButton("➕ הגדל")
        font_increase_btn.clicked.connect(self.increase_font_size)
        
        font_buttons_layout.addWidget(font_decrease_btn)
        font_buttons_layout.addWidget(font_reset_btn)
        font_buttons_layout.addWidget(font_increase_btn)
        font_layout.addLayout(font_buttons_layout)
        
        # תצוגה מקדימה של גופן
        self.font_preview = QLabel("דוגמה לטקסט בגופן הנוכחי - סנכרון אוצריא")
        self.font_preview.setStyleSheet("padding: 10px; border: 1px solid #ccc; border-radius: 5px; background-color: #f9f9f9;")
        font_layout.addWidget(self.font_preview)
        
        font_group.setLayout(font_layout)
        scroll_layout.addWidget(font_group)
        
        # === כפתורי פעולה ===
        actions_layout = QHBoxLayout()
        
        reset_all_btn = QPushButton("🔄 איפוס כל ההגדרות")
        reset_all_btn.clicked.connect(self.reset_all_settings)
        reset_all_btn.setStyleSheet("background-color: #f44336; color: white; padding: 8px; border-radius: 5px;")
        
        show_shortcuts_btn = QPushButton("⌨️ קיצורי מקלדת")
        show_shortcuts_btn.clicked.connect(self.show_keyboard_shortcuts_help)
        
        actions_layout.addWidget(reset_all_btn)
        actions_layout.addWidget(show_shortcuts_btn)
        
        scroll_layout.addLayout(actions_layout)
        scroll_layout.addStretch()
        
        # הגדרת scroll area
        scroll_widget.setLayout(scroll_layout)
        scroll_area.setWidget(scroll_widget)
        scroll_area.setWidgetResizable(True)
        
        # הוספה ל-layout הראשי
        layout.addWidget(scroll_area)
    
    # פונקציות טיפול בהגדרות משופרות
    def set_theme_mode(self, theme_name):
        """הגדרת מצב ערכת נושא"""
        try:
            if self.theme_manager:
                success = self.theme_manager.apply_theme(theme_name, self)
                if success:
                    # עדכון כפתורים
                    self.light_theme_btn.setChecked(theme_name == "light")
                    self.dark_theme_btn.setChecked(theme_name == "dark")
                    
                    theme_display = "בהיר" if theme_name == "light" else "כהה"
                    self.status_bar.showMessage(f"עבר למצב {theme_display}", 2000)
        except Exception as e:
            print(f"שגיאה בהגדרת ערכת נושא: {e}")
    
    def on_font_slider_changed(self, value):
        """טיפול בשינוי slider הגופן"""
        try:
            if hasattr(self, 'font_spinbox'):
                self.font_spinbox.setValue(value)
            
            if self.font_manager:
                self.font_manager.set_font_size(value, self)
            
            # עדכון תצוגה מקדימה
            if hasattr(self, 'font_preview'):
                font = self.font_preview.font()
                font.setPointSize(value)
                self.font_preview.setFont(font)
                
        except Exception as e:
            print(f"שגיאה בשינוי גופן: {e}")
    
    def on_font_spinbox_changed(self, value):
        """טיפול בשינוי spinbox הגופן"""
        try:
            if hasattr(self, 'font_slider_new'):
                self.font_slider_new.setValue(value)
            
            if self.font_manager:
                self.font_manager.set_font_size(value, self)
                
        except Exception as e:
            print(f"שגיאה בשינוי גופן: {e}")
    
    def reset_font_size(self):
        """איפוס גודל גופן לברירת מחדל"""
        try:
            if self.font_manager:
                success = self.font_manager.reset_to_default(self)
                if success:
                    # עדכון בקרות
                    if hasattr(self, 'font_slider_new'):
                        self.font_slider_new.setValue(self.font_manager.base_font_size)
                    if hasattr(self, 'font_spinbox'):
                        self.font_spinbox.setValue(self.font_manager.base_font_size)
                    
                    self.status_bar.showMessage("גודל גופן אופס לברירת מחדל", 2000)
        except Exception as e:
            print(f"שגיאה באיפוס גופן: {e}")
    
    def reset_all_settings(self):
        """איפוס כל ההגדרות לברירת מחדל"""
        try:
            if hebrew_question_dialog(
                self,
                "איפוס הגדרות",
                "האם אתה בטוח שברצונך לאפס את כל ההגדרות לברירת מחדל?"
            ):
                # איפוס הגדרות
                self.settings.clear()
                
                # איפוס מנהלים
                if self.theme_manager:
                    self.theme_manager.apply_theme("light", self)
                if self.font_manager:
                    self.font_manager.reset_to_default(self)
                
                # עדכון בקרות
                if hasattr(self, 'light_theme_btn'):
                    self.light_theme_btn.setChecked(True)
                    self.dark_theme_btn.setChecked(False)
                
                hebrew_info_dialog(self, "הושלם", "כל ההגדרות אופסו לברירת מחדל")
                
        except Exception as e:
            print(f"שגיאה באיפוס הגדרות: {e}")
            hebrew_error_dialog(self, "שגיאה", f"שגיאה באיפוס הגדרות: {e}")
    
    def on_tab_changed(self, index):
        """טיפול בשינוי טאב עם אנימציה"""
        try:
            if self.animation_manager and hasattr(self, '_previous_tab_index'):
                self.animation_manager.animate_tab_transition(
                    self.tab_widget, 
                    self._previous_tab_index, 
                    index
                )
            self._previous_tab_index = index
        except Exception as e:
            print(f"שגיאה באנימציית טאב: {e}")
        
    def setup_shortcuts(self):
        """הגדרת קיצורי מקלדת"""
        # קיצורים לשלבים
        QShortcut(QKeySequence("Alt+1"), self, self.load_manifests)
        QShortcut(QKeySequence("Alt+2"), self, self.download_updates)
        QShortcut(QKeySequence("Alt+3"), self, self.apply_updates)
        
        # קיצורי בקרה
        QShortcut(QKeySequence("Space"), self, self.toggle_pause)
        QShortcut(QKeySequence("Escape"), self, self.cancel_operation)
        
    def toggle_theme(self):
        """החלפת ערכת צבעים (תאימות לאחור)"""
        try:
            if self.theme_manager:
                self.theme_manager.toggle_theme(self)
            else:
                # fallback לשיטה הישנה
                dark_mode = self.settings.value("dark_mode", False, type=bool)
                self.settings.setValue("dark_mode", not dark_mode)
                if hasattr(self, 'dark_mode_checkbox'):
                    self.dark_mode_checkbox.setChecked(not dark_mode)
                self.apply_theme_fallback()
        except Exception as e:
            print(f"שגיאה בהחלפת ערכת נושא: {e}")
        
    def apply_initial_settings(self):
        """החלת הגדרות ראשוניות - ערכת נושא וגופן"""
        try:
            # החלת ערכת נושא
            if self.theme_manager:
                current_theme = self.theme_manager.current_theme
                self.theme_manager.apply_theme(current_theme, self)
            else:
                # fallback לערכת נושא ישנה
                self.apply_theme_fallback()
            
            # החלת גודל גופן
            if self.font_manager:
                self.font_manager.apply_font_to_widget(self)
            
            print("הגדרות ראשוניות הוחלו בהצלחה")
            
            # החלת סגנונות כפתורים אחרי שכל הנושא נטען
            QTimer.singleShot(200, lambda: self._apply_all_button_styles())
            
            # הצגת הודעת גירסה 53 אם לא נבחר "אל תזכיר עוד פעם"
            QTimer.singleShot(500, self.show_version_53_warning)
            
        except Exception as e:
            print(f"שגיאה בהחלת הגדרות ראשוניות: {e}")
            self.apply_theme_fallback()
            # החלת סגנונות כפתורים גם במקרה של שגיאה
            QTimer.singleShot(200, lambda: self._apply_all_button_styles())
            # הצגת הודעה גם במקרה של שגיאה
            QTimer.singleShot(500, self.show_version_53_warning)
    
    def refresh_theme(self):
        """רענון ערכת נושא - לשימוש לאחר תיקונים"""
        try:
            if self.theme_manager:
                current_theme = self.theme_manager.current_theme
                self.theme_manager.apply_theme(current_theme, self)
                print("ערכת הנושא רוענה בהצלחה")
            else:
                self.apply_theme_fallback()
        except Exception as e:
            print(f"שגיאה ברענון ערכת נושא: {e}")
            self.apply_theme_fallback()
    
    def apply_theme_fallback(self):
        """החלת ערכת צבעים ישנה (fallback)"""
        dark_mode = self.settings.value("dark_mode", False, type=bool)
        if dark_mode:
            # ערכת צבעים כהה
            self.setStyleSheet("""
                QMainWindow {
                    background-color: #2b2b2b;
                    color: #ffffff;
                }
                QWidget {
                    background-color: #2b2b2b;
                    color: #ffffff;
                }
                QTabWidget::pane {
                    border: 1px solid #555555;
                    background-color: #3c3c3c;
                }
                QTabBar::tab {
                    background-color: #555555;
                    color: #ffffff;
                    padding: 8px 16px;
                    margin: 2px;
                    border-radius: 4px;
                }
                QTabBar::tab:selected {
                    background-color: #4CAF50;
                }
                QGroupBox {
                    font-weight: bold;
                    border: 2px solid #555555;
                    border-radius: 8px;
                    margin: 10px 0px;
                    padding-top: 10px;
                    background-color: #3c3c3c;
                }
                QGroupBox::title {
                    subcontrol-origin: margin;
                    left: 10px;
                    padding: 0 5px 0 5px;
                }
                QTextEdit {
                    background-color: #1e1e1e;
                    border: 1px solid #555555;
                    border-radius: 5px;
                    color: #ffffff;
                }
                QLabel {
                    color: #ffffff;
                }
                QCheckBox {
                    color: #ffffff;
                }
                QSlider::groove:horizontal {
                    border: 1px solid #555555;
                    height: 8px;
                    background: #3c3c3c;
                    border-radius: 4px;
                }
                QSlider::handle:horizontal {
                    background: #4CAF50;
                    border: 1px solid #555555;
                    width: 18px;
                    margin: -2px 0;
                    border-radius: 9px;
                }
            """)
        else:
            # ערכת צבעים בהירה
            self.setStyleSheet("""
                QMainWindow {
                    background-color: #ffffff;
                    color: #2E4057;
                }
                QWidget {
                    background-color: #ffffff;
                    color: #2E4057;
                }
                QTabWidget::pane {
                    border: 1px solid #E0E0E0;
                    background-color: #ffffff;
                }
                QTabBar::tab {
                    background-color: #F5F5F5;
                    color: #2E4057;
                    padding: 8px 16px;
                    margin: 2px;
                    border-radius: 4px;
                }
                QTabBar::tab:selected {
                    background-color: #4CAF50;
                    color: white;
                }
                QGroupBox {
                    font-weight: bold;
                    border: 2px solid #E0E0E0;
                    border-radius: 8px;
                    margin: 10px 0px;
                    padding-top: 10px;
                    background-color: #FAFAFA;
                }
                QGroupBox::title {
                    subcontrol-origin: margin;
                    left: 10px;
                    padding: 0 5px 0 5px;
                }
                QTextEdit {
                    background-color: #F5F5F5;
                    border: 1px solid #CCCCCC;
                    border-radius: 5px;
                    color: #2E4057;
                }
                QSlider::groove:horizontal {
                    border: 1px solid #CCCCCC;
                    height: 8px;
                    background: #F5F5F5;
                    border-radius: 4px;
                }
                QSlider::handle:horizontal {
                    background: #4CAF50;
                    border: 1px solid #CCCCCC;
                    width: 18px;
                    margin: -2px 0;
                    border-radius: 9px;
                }
            """)
        
        # עדכון אייקונים לערכת הנושא החדשה
        theme = self.theme_manager.current_theme if self.theme_manager else ("dark" if self.settings.value("dark_mode", False, type=bool) else "light")
        if hasattr(self, 'icon_manager'):
            self.icon_manager.update_icons_for_theme(theme)
        
        # עדכון אייקונים בכפתורים הקיימים
        self.update_button_icons()
            
    def update_button_icons(self):
        """עדכון אייקונים בכפתורים לפי ערכת הנושא הנוכחית"""
        try:
            theme = self.theme_manager.current_theme if self.theme_manager else ("dark" if self.settings.value("dark_mode", False, type=bool) else "light")
            
            # עדכון כפתורים ראשיים
            self.btn_load_manifests.setIcon(self.icon_manager.get_icon('folder', size=24, theme=theme))
            self.btn_download_updates.setIcon(self.icon_manager.get_icon('download', size=24, theme=theme))
            self.btn_apply_updates.setIcon(self.icon_manager.get_icon('sync', size=24, theme=theme))
            
            # עדכון כפתורי בקרה
            if self.is_paused:
                self.btn_pause.setIcon(self.icon_manager.get_icon('play', size=16, theme=theme))
            else:
                self.btn_pause.setIcon(self.icon_manager.get_icon('pause', size=16, theme=theme))
            
            self.btn_cancel.setIcon(self.icon_manager.get_icon('stop', size=16, theme=theme))
            self.btn_reset_data.setIcon(self.icon_manager.get_icon('refresh', size=16, theme=theme))
            
        except Exception as e:
            print(f"שגיאה בעדכון אייקוני כפתורים: {e}")
            
    def change_font_size(self, size):
        """שינוי גודל גופן"""
        try:
            if self.font_manager:
                self.font_manager.set_font_size(size, self)
            else:
                # fallback לשיטה הישנה
                self.settings.setValue("font_size", size)
                font = QFont(get_default_font_family(), size)
                self.setFont(font)
                QApplication.instance().setFont(font)
            
            if hasattr(self, 'font_size_label'):
                self.font_size_label.setText(str(size))
        except Exception as e:
            print(f"שגיאה בשינוי גודל גופן: {e}")
        
    def increase_font(self):
        """הגדלת גופן"""
        try:
            if self.font_manager:
                success = self.font_manager.increase_font_size(self)
                if success and hasattr(self, 'font_slider'):
                    self.font_slider.setValue(self.font_manager.current_font_size)
            else:
                # fallback לשיטה הישנה
                current_size = self.settings.value("font_size", 10, type=int)
                if current_size < 20:
                    self.change_font_size(current_size + 1)
                    if hasattr(self, 'font_slider'):
                        self.font_slider.setValue(current_size + 1)
        except Exception as e:
            print(f"שגיאה בהגדלת גופן: {e}")
                
    def decrease_font(self):
        """הקטנת גופן"""
        try:
            if self.font_manager:
                success = self.font_manager.decrease_font_size(self)
                if success and hasattr(self, 'font_slider'):
                    self.font_slider.setValue(self.font_manager.current_font_size)
            else:
                # fallback לשיטה הישנה
                current_size = self.settings.value("font_size", 10, type=int)
                if current_size > 8:
                    self.change_font_size(current_size - 1)
                    if hasattr(self, 'font_slider'):
                        self.font_slider.setValue(current_size - 1)
        except Exception as e:
            print(f"שגיאה בהקטנת גופן: {e}")
                
    def update_stats_display(self):
        """עדכון תצוגת הסטטיסטיקות"""
        if hasattr(self, 'stats_widget'):
            # עדכון סטטיסטיקות
            last_sync = self.settings.value("last_sync", "אף פעם")
            if last_sync != "אף פעם":
                try:
                    from datetime import datetime
                    dt = datetime.fromisoformat(last_sync)
                    last_sync = dt.strftime("%d/%m/%Y %H:%M")
                except:
                    pass
                    
            self.stats_widget.update_stats(
                books=self.total_books,
                size_mb=self.total_size_mb,
                last_sync=last_sync,
                speed=self.current_speed
            )
            
            # עדכון התקדמות כללית
            state = self.load_sync_state()
            current_step = state.get("step", 0)
            overall_progress = (current_step / 3) * 100
            self.overall_progress.setValue(int(overall_progress))
        
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
            # הפעלת כפתור איפוס מצב רק אחרי שהושלם שלב ראשון
            self.btn_reset_data.setEnabled(True)
            # החלת הסגנון הסגול מחדש
            self._apply_reset_button_style()
            self.log("כפתור איפוס המצב הופעל לאחר השלמת שלב 1")
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
        self._apply_reset_button_style()
        """איפוס מצב התקדמות עם דיאלוג אישור"""
        if hebrew_question_dialog(self, "איפוס מצב", 
                                "האם אתה בטוח שברצונך לאפס את מצב ההתקדמות?\n\nפעולה זו תמחק את כל ההתקדמות השמורה ותחזיר אותך לשלב הראשון."):
            success = self.reset_sync_state()
            if success:
                # איפוס משתנים גלובליים
                global LOCAL_PATH, COPIED_DICTA
                LOCAL_PATH = ""
                COPIED_DICTA = False
                
                # עדכון UI למצב התחלתי
                self.load_and_set_state()
                # איפוס סרגל התקדמות
                self.progress_bar.setValue(0)
                self.progress_bar.setVisible(False)
                # איפוס הודעת סטטוס
                self.status_label.setText("מוכן להתחלה")
                # השבתת כפתור איפוס מצב אחרי איפוס
                self.btn_reset_data.setEnabled(False)
                # החלת הסגנון הסגול מחדש גם כשהכפתור לא פעיל
                QTimer.singleShot(100, lambda: self._apply_reset_button_style())
                hebrew_info_dialog(self, "איפוס הושלם", "מצב ההתקדמות אופס בהצלחה!")
            else:
                hebrew_warning_dialog(self, "שגיאה", "שגיאה באיפוס מצב ההתקדמות")

    def reset_data(self):
        """איפוס נתוני המצב השמורים - אותה פונקציה כמו reset_state"""
        # החלת הסגנון הסגול מיד אחרי הלחיצה
        self._apply_reset_button_style()
        self.reset_state()
    
    def offer_cleanup_temp_files(self):
        """הצעה למשתמש למחוק קבצים זמניים לאחר סיום מוצלח"""
        try:
            # בדיקה אם יש קבצים זמניים למחיקה
            temp_files_exist = self._check_temp_files_exist()
            
            if not temp_files_exist:
                return  # אין קבצים זמניים למחיקה
            
            # חישוב גודל הקבצים הזמניים
            temp_size = self._calculate_temp_files_size()
            size_str = self._format_size(temp_size)
            
            # יצירת דיאלוג שאלה עם כפתורים בעברית
            if hebrew_question_dialog(
                self, 
                "מחיקת קבצים זמניים 🗑️",
                f"האם למחוק את הקבצים הזמניים שנוצרו בתיקיית התוכנה של הסנכרון אופליין?\n\n"
                f"גודל הקבצים הזמניים: {size_str}\n\n"
                f"פעולה זו תמחק את כל הקבצים שהורדו, כולל קובץ המניפסט,\n"
                f"כך שהתוכנה תהיה מוכנה להורדה חדשה מההתחלה.\n\n"
                f"הספרים שכבר הועתקו לתיקיית אוצריא לא יימחקו.",
                default_no=True  # ברירת מחדל: לא
            ):
                success = self._cleanup_temp_files()
                if success:
                    hebrew_info_dialog(
                        self, 
                        "מחיקה הושלמה ✅",
                        f"הקבצים הזמניים נמחקו בהצלחה!\n"
                        f"פונה מקום: {size_str}\n\n"
                        f"התוכנה מוכנה להורדה חדשה מההתחלה."
                    )
                    self.log(f"קבצים זמניים נמחקו בהצלחה - פונה מקום: {size_str}")
                else:
                    hebrew_warning_dialog(
                        self, 
                        "שגיאה במחיקה",
                        "אירעה שגיאה במחיקת חלק מהקבצים הזמניים.\n"
                        "ייתכן שחלק מהקבצים נמחקו בהצלחה."
                    )
                    
        except Exception as e:
            self.log(f"שגיאה בהצעת מחיקת קבצים זמניים: {e}")
    
    def _check_temp_files_exist(self):
        """בדיקה אם יש קבצים זמניים למחיקה"""
        try:
            # בדיקת תיקיית BASE_PATH
            if os.path.exists(BASE_PATH) and os.path.isdir(BASE_PATH):
                # בדיקה שיש תוכן בתיקיה
                if any(os.scandir(BASE_PATH)):
                    return True
            
            # בדיקת קבצי מניפסט בתיקיה הנוכחית
            if os.path.exists(MANIFEST_FILE_NAME):
                return True
            if os.path.exists(DICTA_MANIFEST_FILE_NAME):
                return True
            if os.path.exists(STATE_FILE_NAME):
                return True
                
            return False
            
        except Exception as e:
            self.log(f"שגיאה בבדיקת קבצים זמניים: {e}")
            return False
    
    def _calculate_temp_files_size(self):
        """חישוב גודל הקבצים הזמניים בבייטים"""
        total_size = 0
        
        try:
            # חישוב גודל תיקיית BASE_PATH
            if os.path.exists(BASE_PATH) and os.path.isdir(BASE_PATH):
                for dirpath, dirnames, filenames in os.walk(BASE_PATH):
                    for filename in filenames:
                        filepath = os.path.join(dirpath, filename)
                        try:
                            total_size += os.path.getsize(filepath)
                        except (OSError, IOError):
                            pass
            
            # חישוב גודל קבצי מניפסט
            for manifest_file in [MANIFEST_FILE_NAME, DICTA_MANIFEST_FILE_NAME, STATE_FILE_NAME]:
                if os.path.exists(manifest_file):
                    try:
                        total_size += os.path.getsize(manifest_file)
                    except (OSError, IOError):
                        pass
                        
        except Exception as e:
            self.log(f"שגיאה בחישוב גודל קבצים זמניים: {e}")
            
        return total_size
    
    def _format_size(self, size_bytes):
        """המרת גודל בבייטים לפורמט קריא"""
        if size_bytes < 1024:
            return f"{size_bytes} B"
        elif size_bytes < 1024 * 1024:
            return f"{size_bytes / 1024:.1f} KB"
        elif size_bytes < 1024 * 1024 * 1024:
            return f"{size_bytes / (1024 * 1024):.1f} MB"
        else:
            return f"{size_bytes / (1024 * 1024 * 1024):.2f} GB"
    
    def _cleanup_temp_files(self):
        """מחיקת כל הקבצים הזמניים"""
        success = True
        
        try:
            # מחיקת תיקיית BASE_PATH
            if os.path.exists(BASE_PATH) and os.path.isdir(BASE_PATH):
                try:
                    shutil.rmtree(BASE_PATH)
                    self.log(f"תיקיית '{BASE_PATH}' נמחקה בהצלחה")
                except Exception as e:
                    self.log(f"שגיאה במחיקת תיקיית '{BASE_PATH}': {e}")
                    success = False
            
            # מחיקת קבצי מניפסט
            for manifest_file in [MANIFEST_FILE_NAME, DICTA_MANIFEST_FILE_NAME]:
                if os.path.exists(manifest_file):
                    try:
                        os.remove(manifest_file)
                        self.log(f"קובץ '{manifest_file}' נמחק בהצלחה")
                    except Exception as e:
                        self.log(f"שגיאה במחיקת קובץ '{manifest_file}': {e}")
                        success = False
            
            # מחיקת קובץ המצב
            if os.path.exists(STATE_FILE_NAME):
                try:
                    os.remove(STATE_FILE_NAME)
                    self.log(f"קובץ '{STATE_FILE_NAME}' נמחק בהצלחה")
                except Exception as e:
                    self.log(f"שגיאה במחיקת קובץ '{STATE_FILE_NAME}': {e}")
                    success = False
            
            # מחיקת קובץ גיבוי המצב
            backup_state_file = STATE_FILE_NAME + ".backup"
            if os.path.exists(backup_state_file):
                try:
                    os.remove(backup_state_file)
                    self.log(f"קובץ גיבוי '{backup_state_file}' נמחק בהצלחה")
                except Exception as e:
                    self.log(f"שגיאה במחיקת קובץ גיבוי: {e}")
                    # לא נחשב כשגיאה קריטית
            
            # איפוס משתנים גלובליים
            if success:
                global LOCAL_PATH, COPIED_DICTA
                LOCAL_PATH = ""
                COPIED_DICTA = False
                
                # עדכון UI למצב התחלתי
                self.load_and_set_state()
                self.progress_bar.setValue(0)
                self.progress_bar.setVisible(False)
                self.status_label.setText("מוכן להתחלה")
                self.btn_reset_data.setEnabled(False)
                QTimer.singleShot(100, lambda: self._apply_reset_button_style())
                
        except Exception as e:
            self.log(f"שגיאה כללית במחיקת קבצים זמניים: {e}")
            success = False
            
        return success

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
            
    def update_download_progress(self, filename, progress, speed=0, files_done=0, total_files=0):
        """עדכון התקדמות הורדה עם פרטים נוספים"""
        if hasattr(self.progress_bar, 'set_stats'):
            self.progress_bar.set_stats(
                speed=speed,
                files_processed=files_done,
                total_files=total_files
            )
        
        # עדכון מהירות נוכחית לסטטיסטיקות
        self.current_speed = speed
        self.update_stats_display()
        
        # הודעת סטטוס מפורטת
        if total_files > 0:
            self.status_label.setText(f"מוריד: {filename} ({files_done}/{total_files})")
        else:
            self.status_label.setText(f"מוריד: {filename}")
            
    def animate_step_transition(self, new_step):
        """אנימציה למעבר בין שלבים"""
        # אנימציית fade out ו fade in של תווית השלב
        self.step_animation = QPropertyAnimation(self.step_label, b"windowOpacity")
        self.step_animation.setDuration(300)
        self.step_animation.setStartValue(1.0)
        self.step_animation.setEndValue(0.0)
        
        def update_step_text():
            step_names = {
                0: "שלב 1: טעינת קבצי נתונים",
                1: "שלב 2: הורדת עדכונים", 
                2: "שלב 3: החלת עדכונים",
                3: "הושלם! כל השלבים בוצעו"
            }
            self.step_label.setText(f"שלב נוכחי: {step_names.get(new_step, 'לא ידוע')}")
            
            # אנימציית fade in
            fade_in = QPropertyAnimation(self.step_label, b"windowOpacity")
            fade_in.setDuration(300)
            fade_in.setStartValue(0.0)
            fade_in.setEndValue(1.0)
            fade_in.start()
        
        self.step_animation.finished.connect(update_step_text)
        self.step_animation.start()

    def log(self, message):
        timestamp = datetime.now().strftime("%H:%M:%S")
        formatted_message = f"[{timestamp}] {message}"
        self.log_text.append(formatted_message)
        self.log_text.verticalScrollBar().setValue(self.log_text.verticalScrollBar().maximum())
        
        # עדכון status bar
        self.status_bar.showMessage(message)
    
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
        hebrew_info_dialog(self, title, message)
        self.log(f"הצלחה: {message}")

    def show_version_53_warning(self):
        """הצגת הודעת אזהרה לגירסת ספרייה 53 ומטה"""
        try:
            # בדיקה אם המשתמש ביקש לא להציג את ההודעה שוב
            # קודם בודקים בקובץ המקומי, אחר כך ב-QSettings
            dont_show_again = self.get_dont_show_warning_setting()
            if dont_show_again:
                return

            # 1. יצירת דיאלוג גמיש במקום MessageBox
            dialog = QDialog(self)
            dialog.setWindowTitle("⚠️ הודעה חשובה")
            dialog.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
            
            # החזרת כפתור ה-X והגדרת החלון
            dialog.setWindowFlags(Qt.WindowType.Dialog | Qt.WindowType.WindowCloseButtonHint | Qt.WindowType.WindowTitleHint)

            # הגדרת לייאוט ראשי
            main_layout = QVBoxLayout(dialog)
            main_layout.setSpacing(15)

            # טקסט עליון
            top_text = """
            <div style='font-size: 14px; color: #333;'>
                <h3 style='color: #d32f2f; margin: 0 0 10px 0;'>⚠️ הודעה חשובה למשתמשים עם גירסת ספרייה 53 ומטה</h3>
                <p>אם יש לך <strong>גירסת ספרייה 53 או נמוך מזה,</strong><br>
                תוכנת הסנכרון אופליין תצטרך להוריד את כל המאגר כולו מחדש עקב שינויים במבנה הספרייה באתר.<br><br>
                <b>מכיוון שדרך תוכנת הסנכרון אופליין זה לוקח המון זמן,</b>
                מומלץ מאוד להוריד את המאגר כולו מחדש דרך קובץ הזיפ (ZIP) מהקישור הבא:
            </div>
            """
            lbl_top = QLabel(top_text)
            lbl_top.setTextFormat(Qt.TextFormat.RichText)
            lbl_top.setWordWrap(True)
            main_layout.addWidget(lbl_top)

            # --- שורה מיוחדת: קישור + כפתור העתקה צמודים ---
            url_link = "https://github.com/Y-PLONI/otzaria-library/releases/download/latest/otzaria_latest.zip"
            
            link_container = QWidget()
            link_container.setStyleSheet("background-color: #e3f2fd; border-radius: 5px; border: 1px solid #bbdefb;")
            link_layout = QHBoxLayout(link_container)
            link_layout.setContentsMargins(10, 5, 10, 5)
            
            # הקישור עצמו
            lbl_link = QLabel(f"<a href='{url_link}' style='text-decoration: none; color: #1976d2; font-family: monospace; font-weight: bold;'>otzaria_latest.zip</a>")
            lbl_link.setOpenExternalLinks(True)
            
            # כפתור העתקה קטן
            btn_copy = QPushButton("העתק קישור")
            btn_copy.setCursor(Qt.CursorShape.PointingHandCursor)
            btn_copy.setStyleSheet("""
                QPushButton { background-color: white; color: #1976d2; border: 1px solid #1976d2; border-radius: 3px; padding: 2px 8px; font-size: 12px; }
                QPushButton:hover { background-color: #e3f2fd; }
            """)
            
            def copy_link():
                QApplication.clipboard().setText(url_link)
                btn_copy.setText("הועתק!")
                
            btn_copy.clicked.connect(copy_link)

            link_layout.addWidget(lbl_link)
            link_layout.addWidget(btn_copy)
            link_layout.addStretch() # דוחף את התוכן לימין
            
            main_layout.addWidget(link_container)

            # טקסט תחתון
            lbl_bottom = QLabel("ולהשתמש בתוכנה זו רק בשביל הסנכרונים הבאים.")
            lbl_bottom.setStyleSheet("font-size: 14px;")
            main_layout.addWidget(lbl_bottom)

            # --- שורה תחתונה: צ'קבוקס וכפתור סגירה באותה שורה ---
            bottom_layout = QHBoxLayout()
            
            chk_dont_show = QCheckBox("אל תזכיר לי עוד פעם")
            chk_dont_show.setStyleSheet("color: #333; font-weight: bold;")
            
            btn_close = QPushButton("סגור")
            btn_close.setCursor(Qt.CursorShape.PointingHandCursor)
            btn_close.setMinimumWidth(100)
            btn_close.clicked.connect(dialog.accept) # סוגר את החלון

            bottom_layout.addWidget(chk_dont_show)
            bottom_layout.addStretch() # יוצר רווח גמיש באמצע
            bottom_layout.addWidget(btn_close)
            
            main_layout.addLayout(bottom_layout)

            # עיצוב כללי לדיאלוג (רקע ורוד)
            dialog.setStyleSheet("""
                QDialog { background-color: #ffebee; border: 2px solid #ef5350; }
                QPushButton { background-color: #f44336; color: white; border: none; border-radius: 5px; padding: 6px 12px; font-weight: bold; }
                QPushButton:hover { background-color: #d32f2f; }
            """)

            # הצגת החלון
            dialog.exec()

            # שמירת הבחירה
            if chk_dont_show.isChecked():
                self.save_dont_show_warning_setting(True)
                if hasattr(self, 'log'):
                    self.log("המשתמש ביקש לא להציג את הודעת גירסה 53 שוב")

        except Exception as e:
            print(f"שגיאה בהצגת הודעת גירסה 53: {e}")
    
    def get_dont_show_warning_setting(self):
        """קריאת הגדרת 'אל תזכיר עוד פעם' מקובץ מקומי ו-QSettings"""
        try:
            # קודם מנסים לקרוא מהקובץ המקומי
            state = self.state_manager.load_state()
            if "dont_show_version_53_warning" in state:
                return state.get("dont_show_version_53_warning", False)
            
            # אם לא נמצא בקובץ, בודקים ב-QSettings (לתאימות לאחור)
            return self.settings.value("dont_show_version_53_warning", False, type=bool)
            
        except Exception as e:
            print(f"שגיאה בקריאת הגדרת אזהרה: {e}")
            return False
    
    def save_dont_show_warning_setting(self, value):
        """שמירת הגדרת 'אל תזכיר עוד פעם' בקובץ מקומי וב-QSettings"""
        try:
            # שמירה ב-QSettings (לתאימות לאחור)
            self.settings.setValue("dont_show_version_53_warning", value)
            
            # שמירה בקובץ המקומי
            state = self.state_manager.load_state()
            state["dont_show_version_53_warning"] = value
            self.state_manager.save_state(state)
            
            print(f"הגדרת 'אל תזכיר עוד פעם' נשמרה: {value}")
            return True
            
        except Exception as e:
            print(f"שגיאה בשמירת הגדרת אזהרה: {e}")
            return False

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
        self.btn_manual_select.setVisible(False)  # הסתרת כפתור הבחירה הידנית
        self.disable_reset_during_operation()  # השבתת כפתור איפוס מצב במהלך פעולה
        
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
        self.worker.manual_selection.connect(self.show_manual_selection_button)  # חיבור חדש
        # חיבור למידע זיכרון אם קיים
        if hasattr(self.worker, 'memory_info'):
            self.worker.memory_info.connect(self.update_memory_info)
        self.worker.start()
        self.enable_operation_buttons()
        
    def show_manual_selection_button(self):
        """הצגת כפתור הבחירה הידנית"""
        self.btn_manual_select.setVisible(True)
    
    def show_manual_selection(self):
        """הצגת חלון בחירת תיקיה ידנית"""
        folder = QFileDialog.getExistingDirectory(self, "בחר את תיקיית אוצריא")
        if folder:
            global LOCAL_PATH
            LOCAL_PATH = folder
            # עצירת החיפוש הנוכחי מיידית
            if self.worker:
                self.worker.stop_search = True
                self.worker.manual_selected = True  # סימון שנעשתה בחירה ידנית
                # המתנה קצרה לוודא שהחיפוש נעצר
                self.worker.wait(1000)  # המתנה של שנייה אחת
            # הסתרת הכפתור אחרי הבחירה
            self.btn_manual_select.setVisible(False)
            # הודעה למשתמש
            self.log(f"נבחרה תיקיה ידנית: {folder}")
            self.load_manifests()
        else:
            hebrew_warning_dialog(self, "שגיאה", "לא נבחרה תיקיה")

    # שינוי קל בטיפול בשגיאות
    def on_load_manifests_finished(self, success, message):
        self.progress_bar.setVisible(False)
        self.status_label.setText(message)
        
        # השבתת כפתורי השהיה וביטול בסיום הפעולה
        self.disable_operation_buttons()
        self.log(message)
        self.reset_buttons()
        
        if success:
            # סגירה אוטומטית של כפתור בחירה ידנית אם מוצג
            if self.btn_manual_select.isVisible():
                self.btn_manual_select.setVisible(False)
                self.log("כפתור הבחירה הידנית הוסתר אוטומטית לאחר מציאת המניפסטים")
            else:
                self.log("כפתור הבחירה הידנית כבר היה מוסתר")
            
            # אנימציה למעבר לשלב הבא
            self.animate_step_transition(1)
            
            # שמירת מצב עם נתונים נוספים
            state_data = {
                "step": 1,
                "manifests_loaded": True,
                "last_sync_time": datetime.now().isoformat()
            }
            self.save_sync_state(state_data)
            self.settings.setValue("last_sync", datetime.now().isoformat())
            
            self.btn_download_updates.setEnabled(True)
            self.enable_reset_after_operation()  # הפעלת כפתור איפוס מצב אחרי השלב הראשון
            self._apply_reset_button_style()
            self.log("שלב 1 הושלם - קבצי המניפסט נטענו")
            
            # עדכון סטטיסטיקות
            self.update_stats_display()
            
            hebrew_info_dialog(self, "הצלחה", message)
        else:
            self.btn_load_manifests.setEnabled(True)
            self.enable_reset_after_operation()  # הפעלת כפתור איפוס מצב גם במקרה של שגיאה
            self._apply_reset_button_style()
            # שמירת מצב גם במקרה של שגיאה כדי לאפשר המשך
            state_data = {"step": 0, "error": message}
            self.save_sync_state(state_data)
            hebrew_error_dialog(self, "שגיאה", message)
    
    def download_updates(self):
        if self.worker and self.worker.isRunning():
            return
            
        self.progress_bar.setVisible(True)
        self.progress_bar.setValue(0)
        self.btn_download_updates.setEnabled(False)
        self.disable_reset_during_operation()  # השבתת כפתור איפוס מצב במהלך פעולה
        
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
        self.enable_operation_buttons()
        
    def on_download_updates_finished(self, success, message):
        self.progress_bar.setVisible(False)
        
        # השבתת כפתורי השהיה וביטול בסיום הפעולה
        self.disable_operation_buttons()
        
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
                hebrew_info_dialog(self, "מעודכן", message)
            else:
                # אנימציה למעבר לשלב הבא
                self.animate_step_transition(2)
                
                # יש קבצים שהורדו - עובר לשלב הבא
                state_data = {
                    "step": 2,
                    "manifests_loaded": True,
                    "updates_downloaded": True,
                    "last_sync_time": datetime.now().isoformat()
                }
                self.save_sync_state(state_data)
                self.settings.setValue("last_sync", datetime.now().isoformat())
                
                self.btn_apply_updates.setEnabled(True)
                self.enable_reset_after_operation()  # הפעלת כפתור איפוס מצב אחרי השלב השני
                self._apply_reset_button_style()
                self.log("שלב 2 הושלם - עדכונים הורדו")
                
                # עדכון סטטיסטיקות
                self.update_stats_display()
                
                hebrew_info_dialog(self, "הצלחה", message)
        else:
            self.btn_download_updates.setEnabled(True)
            self.enable_reset_after_operation()  # הפעלת כפתור איפוס מצב גם במקרה של שגיאה
            self._apply_reset_button_style()
            # שמירת מצב גם במקרה של שגיאה
            state_data = {
                "step": 1,
                "manifests_loaded": True,
                "updates_downloaded": False,
                "error": message,
                "last_sync_time": datetime.now().isoformat()
            }
            self.save_sync_state(state_data)
            hebrew_error_dialog(self, "שגיאה", message)
    
    def apply_updates(self):
        if self.worker and self.worker.isRunning():
            return
            
        self.progress_bar.setVisible(True)
        self.progress_bar.setValue(0)
        self.btn_apply_updates.setEnabled(False)
        self.disable_reset_during_operation()  # השבתת כפתור איפוס מצב במהלך פעולה
        
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
        self.enable_operation_buttons()
    
    def on_apply_updates_finished(self, success, message):
        self.progress_bar.setVisible(False)
        self.status_label.setText(message)
        
        # השבתת כפתורי השהיה וביטול בסיום הפעולה
        self.disable_operation_buttons()
        self.log(message)
        self.reset_buttons()
        
        if success:
            # אנימציה לסיום כל השלבים
            self.animate_step_transition(3)
            
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
            self.settings.setValue("last_sync", datetime.now().isoformat())
            
            # איפוס הכפתורים לתחילת המחזור
            self.btn_load_manifests.setEnabled(True)
            self.btn_download_updates.setEnabled(False)
            self.btn_apply_updates.setEnabled(False)
            self.enable_reset_after_operation()  # הפעלת כפתור איפוס מצב אחרי השלב השלישי
            self._apply_reset_button_style()
            
            # עדכון סטטיסטיקות סופי
            self.update_stats_display()
            
            self.log("כל השלבים הושלמו בהצלחה!")
            
            pixmap = QPixmap(64, 64)
            pixmap.fill(Qt.GlobalColor.transparent)
            painter = QPainter(pixmap)
            # שימוש בגופן emoji מתאים לפלטפורמה
            platform_info = get_platform_info()
            if platform_info['is_windows']:
                emoji_font = "Segoe UI Emoji"
            elif platform_info['is_macos']:
                emoji_font = "Apple Color Emoji"
            else:
                emoji_font = "Noto Color Emoji"
            painter.setFont(QFont(emoji_font, 48))
            painter.drawText(pixmap.rect(), Qt.AlignmentFlag.AlignCenter, "📖")
            painter.end()

            # הודעת הצלחה עם אפקט חזותי וכפתור אישור בעברית
            success_msg = QMessageBox(self)
            success_msg.setIcon(QMessageBox.Icon.Information)
            success_msg.setWindowTitle("!הצלחה 🎉")
            success_msg.setIconPixmap(pixmap)
            success_msg.setText("הסנכרון הושלם בהצלחה!!\n"
                                "כל הספרים נכנסו לתוך תוכנת אוצריא")
            success_msg.addButton("אישור", QMessageBox.ButtonRole.AcceptRole)
            success_msg.exec()
            
            # הצעה למחיקת קבצים זמניים לאחר סיום מוצלח
            self.offer_cleanup_temp_files()
            
        else:
            self.btn_apply_updates.setEnabled(True)
            self.enable_reset_after_operation()  # הפעלת כפתור איפוס מצב גם במקרה של שגיאה
            self._apply_reset_button_style()
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
            hebrew_error_dialog(self, "שגיאה", message)

    def toggle_pause(self):
        if self.worker and self.worker.isRunning():
            self.is_paused = not self.is_paused
            # העברת מצב ההשהיה ל-worker
            self.worker.is_paused = self.is_paused
            
            if self.is_paused:
                # איפוס דגל הודעת השהיה
                self.worker.pause_message_sent = False
                self.btn_pause.setText("   המשך")
                self.btn_pause.setIcon(self.icon_manager.get_icon('play', size=16))
                self.set_pause_button_style("resume")
                self.status_label.setText("פעולה מושהית")
                self.log("פעולה הושהתה")  # רישום פעם אחת בלבד
            else:
                # איפוס דגל הודעת השהיה כשממשיכים
                self.worker.pause_message_sent = False
                self.btn_pause.setText("השהה")
                # self.btn_pause.setIcon(self.icon_manager.get_icon('pause', size=16))
                self.set_pause_button_style("pause")
                self.status_label.setText("פעולה מתבצעת")
                self.log("פעולה הומשכה")  # רישום פעם אחת בלבד
    
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
            self.enable_reset_after_operation()  # הפעלת כפתור איפוס מצב אחרי ביטול
            # החלת הסגנונות מחדש על כל הכפתורים
            QTimer.singleShot(50, lambda: self._apply_all_button_styles())
            
    def reset_buttons(self):
        """איפוס מצב כל הכפתורים"""
        self.btn_pause.setEnabled(False)
        self.btn_cancel.setEnabled(False)
        self.btn_manual_select.setVisible(False)
        self.btn_pause.setText("השהה")
        self.set_pause_button_style("pause")  # איפוס לסגנון השהיה
        # החלת הסגנונות מחדש
        QTimer.singleShot(20, lambda: self._apply_all_button_styles())
    
    def enable_operation_buttons(self):
        """הפעלת כפתורי השהיה וביטול במהלך פעולה - שיפור UX"""
        self.btn_pause.setEnabled(True)
        self.btn_cancel.setEnabled(True)
    
    def disable_operation_buttons(self):
        """השבתת כפתורי השהיה וביטול בסיום פעולה - שיפור UX"""
        self.btn_pause.setEnabled(False)
        self.btn_cancel.setEnabled(False)
    
    def disable_reset_during_operation(self):
        """השבתת כפתור איפוס מצב במהלך פעולה"""
        self.btn_reset_data.setEnabled(False)
    
    def enable_reset_after_operation(self):
        """הפעלת כפתור איפוס מצב אחרי פעולה"""
        self.btn_reset_data.setEnabled(True)
        # החלת הסגנון הסגול מחדש
        self._apply_reset_button_style()
    
    def _apply_reset_button_style(self):
        """החלת הסגנון הסגול על כפתור איפוס המצב"""
        reset_complete_style = """
            QPushButton {
                background-color: #9C27B0 !important;
                color: white !important;
                border: none !important;
                border-radius: 5px !important;
                font-size: 12px !important;
            }
            QPushButton:hover:enabled {
                background-color: #7B1FA2 !important;
                border-radius: 5px !important;
            }
            QPushButton:pressed {
                background-color: #6A1B9A !important;
                border-radius: 5px !important;
            }
        """
        # החלה מיידית של הסגנון המלא
        self.btn_reset_data.setStyleSheet(reset_complete_style)
    
    def set_pause_button_style(self, style_type="pause"):
        """הגדרת סגנון כפתור ההשהיה"""
        if style_type == "pause":
            # סגנון השהיה (כתום) - סגנון מלא עם כל המצבים
            complete_style = """
                QPushButton {
                    background-color: #FF9800 !important;
                    color: white !important;
                    border: none !important;
                    border-radius: 5px !important;
                    font-size: 12px !important;
                }
                QPushButton:hover:enabled {
                    background-color: #F57C00 !important;
                    border-radius: 5px !important;
                }
                QPushButton:pressed {
                    background-color: #E65100 !important;
                    border-radius: 5px !important;
                }
            """
        else:  # style_type == "resume"
            # סגנון המשך (ירוק) - סגנון מלא עם כל המצבים
            complete_style = """
                QPushButton {
                    background-color: #4CAF50 !important;
                    color: white !important;
                    border: none !important;
                    border-radius: 5px !important;
                    font-size: 12px !important;
                }
                QPushButton:hover:enabled {
                    background-color: #45a049 !important;
                    border-radius: 5px !important;
                }
                QPushButton:pressed {
                    background-color: #2E7D32 !important;
                    border-radius: 5px !important;
                }
            """
        
        self.btn_pause.set_disabled_opacity(0.5)
        # החלה מיידית של הסגנון המלא
        self.btn_pause.setStyleSheet(complete_style)
    
    def _apply_pause_button_style_complete(self, style_type="pause"):
        """החלת הסגנון המלא על כפתור ההשהיה"""
        if style_type == "pause":
            complete_style = """
                QPushButton {
                    background-color: #FF9800 !important;
                    color: white !important;
                    border: none !important;
                    border-radius: 5px !important;
                    font-size: 12px !important;
                }
                QPushButton:hover:enabled {
                    background-color: #F57C00 !important;
                    border-radius: 5px !important;
                }
                QPushButton:pressed {
                    background-color: #E65100 !important;
                    border-radius: 5px !important;
                }
            """
        else:  # resume
            complete_style = """
                QPushButton {
                    background-color: #4CAF50 !important;
                    color: white !important;
                    border: none !important;
                    border-radius: 5px !important;
                    font-size: 12px !important;
                }
                QPushButton:hover:enabled {
                    background-color: #45a049 !important;
                    border-radius: 5px !important;
                }
                QPushButton:pressed {
                    background-color: #2E7D32 !important;
                    border-radius: 5px !important;
                }
            """
        self.btn_pause.setStyleSheet(complete_style)
    
    def _apply_cancel_button_style_complete(self):
        """החלת הסגנון המלא על כפתור הביטול"""
        complete_style = """
            QPushButton {
                background-color: #f44336 !important;
                color: white !important;
                border: none !important;
                border-radius: 5px !important;
                font-size: 12px !important;
            }
            QPushButton:hover:enabled {
                background-color: #da190b !important;
                border-radius: 5px !important;
            }
            QPushButton:pressed {
                background-color: #c62828 !important;
                border-radius: 5px !important;
            }
        """
        self.btn_cancel.setStyleSheet(complete_style)
    
    def _apply_all_button_styles(self):
        """החלת הסגנונות על כל הכפתורים"""
        self._apply_reset_button_style()
        self.set_pause_button_style("pause")  # משתמש בפונקציה המעודכנת
        self._apply_cancel_button_style_complete()
    
    def expand_log_area(self):
        """הגדלת איזור יומן הפעולות"""
        try:
            current_height = self.log_text.height()
            new_height = min(current_height + 50, 300)  # הגדלה של 50 פיקסלים עד למקסימום 300
            if new_height != current_height:
                self.log_text.setMinimumHeight(new_height)
                self.log_text.setMaximumHeight(new_height)
                # הודעה ליומן רק אם באמת השתנה הגודל
                if new_height < 300:
                    self.log(f"איזור יומן הפעולות הוגדל לגובה {new_height} פיקסלים")
                else:
                    self.log("איזור יומן הפעולות הגיע לגודל המקסימלי")
        except Exception as e:
            print(f"שגיאה בהגדלת איזור היומן: {e}")
    
    def shrink_log_area(self):
        """הקטנת איזור יומן הפעולות"""
        try:
            current_height = self.log_text.height()
            new_height = max(current_height - 50, 80)  # הקטנה של 50 פיקסלים עד למינימום 80
            if new_height != current_height:
                self.log_text.setMinimumHeight(new_height)
                self.log_text.setMaximumHeight(new_height)
                # הודעה ליומן רק אם באמת השתנה הגודל
                if new_height > 80:
                    self.log(f"איזור יומן הפעולות הוקטן לגובה {new_height} פיקסלים")
                else:
                    self.log("איזור יומן הפעולות הגיע לגודל המינימלי")
        except Exception as e:
            print(f"שגיאה בהקטנת איזור היומן: {e}")
        # איפוס עיצוב כפתור השהיה למצב הרגיל
        self.set_pause_button_style("pause")
        self.is_paused = False
        self.is_cancelled = False            

    # פונקציות אינטגרציה למנהלים
    def toggle_theme_mode(self):
        """החלפה בין מצב כהה לבהיר"""
        try:
            if self.theme_manager:
                success = self.theme_manager.toggle_theme(self)
                if success:
                    theme_name = "כהה" if self.theme_manager.current_theme == "dark" else "בהיר"
                    self.status_bar.showMessage(f"עבר למצב {theme_name}", 2000)
                    return True
            else:
                # fallback למצב ישן
                current_dark_mode = self.settings.value("dark_mode", False, type=bool)
                new_dark_mode = not current_dark_mode
                self.settings.setValue("dark_mode", new_dark_mode)
                self.apply_theme_fallback()
                theme_name = "כהה" if new_dark_mode else "בהיר"
                self.status_bar.showMessage(f"עבר למצב {theme_name}", 2000)
                return True
        except Exception as e:
            print(f"שגיאה בהחלפת ערכת נושא: {e}")
            return False
    
    def increase_font_size(self):
        """הגדלת גודל גופן"""
        try:
            if self.font_manager:
                success = self.font_manager.increase_font_size(self)
                if success:
                    self.status_bar.showMessage(f"גודל גופן: {self.font_manager.current_font_size}", 2000)
                return success
            return False
        except Exception as e:
            print(f"שגיאה בהגדלת גופן: {e}")
            return False
    
    def decrease_font_size(self):
        """הקטנת גודל גופן"""
        try:
            if self.font_manager:
                success = self.font_manager.decrease_font_size(self)
                if success:
                    self.status_bar.showMessage(f"גודל גופן: {self.font_manager.current_font_size}", 2000)
                return success
            return False
        except Exception as e:
            print(f"שגיאה בהקטנת גופן: {e}")
            return False
    
    def animate_progress_update(self, value):
        """עדכון מד התקדמות עם אנימציה"""
        try:
            if hasattr(self.progress_bar, 'update_progress_animated'):
                self.progress_bar.update_progress_animated(value)
            else:
                self.progress_bar.setValue(value)
        except Exception as e:
            print(f"שגיאה באנימציית התקדמות: {e}")
            self.progress_bar.setValue(value)
    
    def update_detailed_progress(self, **kwargs):
        """עדכון מד התקדמות עם פרטים מלאים"""
        try:
            if hasattr(self.progress_bar, 'set_detailed_stats'):
                self.progress_bar.set_detailed_stats(**kwargs)
            
            # עדכון סטטיסטיקות מתקדמות אם קיימות
            if hasattr(self, 'stats_widget') and hasattr(self.stats_widget, 'update_real_time_stats'):
                self.stats_widget.update_real_time_stats(kwargs)
                
        except Exception as e:
            print(f"שגיאה בעדכון התקדמות מפורטת: {e}")
    
    def create_animated_button(self, text, icon_name=None):
        """יצירת כפתור מונפש עם אייקון"""
        try:
            button = AnimatedButton(text)
            
            if icon_name and self.icon_manager:
                icon = self.icon_manager.get_icon(icon_name, size=24)
                if icon and not icon.isNull():
                    button.setIcon(icon)
                    button.setIconSize(QSize(24, 24))
            
            return button
            
        except Exception as e:
            print(f"שגיאה ביצירת כפתור מונפש: {e}")
            return QPushButton(text)
    
    def show_keyboard_shortcuts_help(self):
        """הצגת עזרה לקיצורי מקלדת"""
        try:
            if self.shortcut_manager:
                self.shortcut_manager.show_help_dialog()
            else:
                # fallback לעזרה בסיסית
                hebrew_info_dialog(
                    self,
                    "קיצורי מקלדת",
                    "קיצורי מקלדת בסיסיים:\n\n"
                    "Ctrl+S - התחלת סנכרון\n"
                    "Ctrl+P - השהיה/המשכה\n"
                    "Ctrl+Q - יציאה\n"
                    "F1 - עזרה זו"
                )
        except Exception as e:
            print(f"שגיאה בהצגת עזרה: {e}")
    
    def get_current_theme_info(self):
        """קבלת מידע על ערכת הנושא הנוכחית"""
        try:
            if self.theme_manager:
                return {
                    "theme": self.theme_manager.current_theme,
                    "colors": self.theme_manager.get_current_theme_colors()
                }
            else:
                return {
                    "theme": "dark" if self.settings.value("dark_mode", False, type=bool) else "light",
                    "colors": {}
                }
        except Exception as e:
            print(f"שגיאה בקבלת מידע ערכת נושא: {e}")
            return {"theme": "light", "colors": {}}
    
    def get_font_info(self):
        """קבלת מידע על הגופן הנוכחי"""
        try:
            if self.font_manager:
                return self.font_manager.get_font_info()
            else:
                return {
                    "current_size": self.settings.value("font_size", 10, type=int),
                    "base_size": 10,
                    "min_size": 8,
                    "max_size": 20
                }
        except Exception as e:
            print(f"שגיאה בקבלת מידע גופן: {e}")
            return {"current_size": 10, "base_size": 10}
    
    def export_current_stats(self):
        """ייצוא סטטיסטיקות נוכחיות"""
        try:
            if hasattr(self, 'stats_widget') and hasattr(self.stats_widget, 'export_stats'):
                filename = self.stats_widget.export_stats()
                if filename:
                    hebrew_info_dialog(
                        self,
                        "ייצוא הושלם",
                        f"הסטטיסטיקות יוצאו בהצלחה לקובץ:\n{filename}"
                    )
                    return filename
            return None
        except Exception as e:
            print(f"שגיאה בייצוא סטטיסטיקות: {e}")
            return None
    
    # פונקציה לטעינת אייקון ממחרוזת Base64
    def load_icon_from_base64(self, base64_string):
        pixmap = QPixmap()
        pixmap.loadFromData(base64.b64decode(base64_string))
        return QIcon(pixmap)
        
    def closeEvent(self, event):
        """טיפול בסגירת האפליקציה"""
        # שמירת הגדרות כל המנהלים
        try:
            if self.theme_manager:
                self.theme_manager.save_theme_preference()
            else:
                # fallback לשמירה ישנה
                dark_mode = self.settings.value("dark_mode", False, type=bool)
                self.settings.setValue("dark_mode", dark_mode)
            
            if self.font_manager:
                self.font_manager.save_font_size()
            else:
                # fallback לשמירה ישנה
                font_size = self.settings.value("font_size", 10, type=int)
                self.settings.setValue("font_size", font_size)
            
            # סנכרון הגדרות
            self.settings.sync()
            
        except Exception as e:
            print(f"שגיאה בשמירת הגדרות: {e}")
        
        # בדיקה אם יש פעולה פעילה
        if self.worker and self.worker.isRunning():
            if hebrew_question_dialog(self, "סגירת האפליקציה",
                                        "יש פעולה פעילה. האם אתה בטוח שברצונך לסגור?"):
                # עצירת הפעולה
                if self.worker:
                    self.worker.stop_search = True
                    self.worker.wait(3000)  # המתנה של 3 שניות
                event.accept()
            else:
                event.ignore()
        else:
            event.accept()

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
    
    # הגדרת כיוון RTL
    app.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
    
    window = OtzariaSync()
    
    # הגדרת גופן עברי בהתאם להגדרות המשתמש
    try:
        if window.font_manager:
            font_size = window.font_manager.current_font_size
        else:
            font_size = window.settings.value("font_size", 10, type=int)
        
        font = QFont(get_default_font_family(), font_size)
        app.setFont(font)
        window.setFont(font)
    except Exception as e:
        print(f"שגיאה בהגדרת גופן: {e}")
        # fallback לגופן ברירת מחדל
        font = QFont(get_default_font_family(), 10)
        app.setFont(font)
        window.setFont(font)
    
    # הודעה על חסרון תלויות
    if not has_all_deps:
        window.log("אזהרה: חסרות ספריות נדרשות - התוכנה תפעל במצב בסיסי")
    
    window.show()
    
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
