#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
בדיקות אינטגרציה לשיפורי העיצוב של אוצריא סינק
"""

import unittest
import sys
import os
from unittest.mock import Mock, patch, MagicMock
from PyQt6.QtWidgets import QApplication, QWidget
from PyQt6.QtCore import QSettings
from PyQt6.QtTest import QTest

# הוספת נתיב לקובץ הראשי
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

try:
    import importlib.util
    spec = importlib.util.spec_from_file_location("otzaria_module", "‏‏‏‏otzaria_sync_offline.py")
    otzaria_module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(otzaria_module)
except Exception as e:
    print(f"שגיאה בטעינת המודול: {e}")
    sys.exit(1)

# ייבוא המחלקות
ThemeManager = otzaria_module.ThemeManager
FontManager = otzaria_module.FontManager
ShortcutManager = otzaria_module.ShortcutManager
IconManager = otzaria_module.IconManager
AdvancedStatsWidget = otzaria_module.AdvancedStatsWidget
EnhancedProgressBar = otzaria_module.EnhancedProgressBar

class TestUIEnhancements(unittest.TestCase):
    """בדיקות אינטגרציה לשיפורי העיצוב"""
    
    @classmethod
    def setUpClass(cls):
        """הכנה לכל הבדיקות"""
        if not QApplication.instance():
            cls.app = QApplication([])
        else:
            cls.app = QApplication.instance()
    
    def setUp(self):
        """הכנה לכל בדיקה"""
        self.settings = QSettings("TestOtzariaSync", "TestSettings")
        self.test_widget = QWidget()
        self.test_widget.show()
    
    def tearDown(self):
        """ניקוי אחרי כל בדיקה"""
        self.test_widget.close()
        self.settings.clear()
    
    def test_theme_manager_initialization(self):
        """בדיקת אתחול מנהל ערכות נושא"""
        theme_manager = ThemeManager(self.settings)
        
        self.assertIsNotNone(theme_manager)
        self.assertIn(theme_manager.current_theme, ["light", "dark"])
        self.assertIn("light", theme_manager.themes)
        self.assertIn("dark", theme_manager.themes)
    
    def test_theme_switching(self):
        """בדיקת החלפת ערכות נושא"""
        theme_manager = ThemeManager(self.settings)
        initial_theme = theme_manager.current_theme
        
        # החלפת ערכת נושא
        success = theme_manager.toggle_theme(self.test_widget)
        self.assertTrue(success)
        self.assertNotEqual(theme_manager.current_theme, initial_theme)
        
        # החלפה חזרה
        success = theme_manager.toggle_theme(self.test_widget)
        self.assertTrue(success)
        self.assertEqual(theme_manager.current_theme, initial_theme)
    
    def test_font_manager_initialization(self):
        """בדיקת אתחול מנהל גופנים"""
        font_manager = FontManager(self.settings)
        
        self.assertIsNotNone(font_manager)
        self.assertGreaterEqual(font_manager.current_font_size, font_manager.min_font_size)
        self.assertLessEqual(font_manager.current_font_size, font_manager.max_font_size)
    
    def test_font_size_changes(self):
        """בדיקת שינוי גודל גופן"""
        font_manager = FontManager(self.settings)
        initial_size = font_manager.current_font_size
        
        # הגדלת גופן
        success = font_manager.increase_font_size(self.test_widget)
        if initial_size < font_manager.max_font_size:
            self.assertTrue(success)
            self.assertGreater(font_manager.current_font_size, initial_size)
        
        # הקטנת גופן
        success = font_manager.decrease_font_size(self.test_widget)
        self.assertTrue(success)
        
        # איפוס גופן
        success = font_manager.reset_to_default(self.test_widget)
        self.assertTrue(success)
        self.assertEqual(font_manager.current_font_size, font_manager.base_font_size)
    
    def test_icon_manager_functionality(self):
        """בדיקת פונקציונליות מנהל אייקונים"""
        icon_manager = IconManager()
        
        # בדיקת קבלת אייקון
        icon = icon_manager.get_icon('play')
        self.assertIsNotNone(icon)
        
        # בדיקת אייקון לא קיים
        icon = icon_manager.get_icon('nonexistent_icon')
        self.assertIsNotNone(icon)  # צריך להחזיר fallback
        
        # בדיקת רשימת אייקונים זמינים
        available_icons = icon_manager.get_available_icons()
        self.assertIsInstance(available_icons, list)
        self.assertGreater(len(available_icons), 0)
    
    def test_enhanced_progress_bar(self):
        """בדיקת מד התקדמות משופר"""
        progress_bar = EnhancedProgressBar()
        
        # בדיקת עדכון סטטיסטיקות
        progress_bar.set_detailed_stats(
            current_file="test.txt",
            download_speed=5.5,
            time_remaining=120,
            files_completed=10,
            total_files=50
        )
        
        # בדיקת פורמט זמן
        time_str = progress_bar.format_time_remaining(125)
        self.assertIn(":", time_str)
        
        # בדיקת פורמט גודל קובץ
        size_str = progress_bar.format_file_size(1024 * 1024)
        self.assertIn("MB", size_str)
    
    def test_advanced_stats_widget(self):
        """בדיקת ווידג'ט סטטיסטיקות מתקדם"""
        stats_widget = AdvancedStatsWidget()
        
        # בדיקת עדכון סטטיסטיקות
        test_stats = {
            'books_count': 100,
            'total_size_mb': 500.5,
            'download_speed': 2.3,
            'memory_usage_mb': 128.7,
            'active_threads': 3,
            'errors_count': 2
        }
        
        stats_widget.update_real_time_stats(test_stats)
        
        # בדיקת החלפת מצב תצוגה
        initial_collapsed = stats_widget.is_collapsed
        stats_widget.toggle_visibility()
        self.assertNotEqual(stats_widget.is_collapsed, initial_collapsed)
    
    def test_shortcut_manager_initialization(self):
        """בדיקת אתחול מנהל קיצורי מקלדת"""
        shortcut_manager = ShortcutManager(self.test_widget)
        
        self.assertIsNotNone(shortcut_manager)
        self.assertEqual(len(shortcut_manager.shortcuts), 0)  # לפני setup
        
        # הגדרת קיצורים
        success = shortcut_manager.setup_shortcuts()
        self.assertTrue(success)
        self.assertGreater(len(shortcut_manager.shortcuts), 0)
    
    def test_memory_usage(self):
        """בדיקת שימוש זיכרון בסיסי"""
        # יצירת מספר רכיבים
        components = []
        for i in range(10):
            theme_manager = ThemeManager(self.settings)
            font_manager = FontManager(self.settings)
            icon_manager = IconManager()
            components.extend([theme_manager, font_manager, icon_manager])
        
        # בדיקה שהרכיבים נוצרו
        self.assertEqual(len(components), 30)
        
        # ניקוי
        del components
    
    def test_performance_basic(self):
        """בדיקת ביצועים בסיסית"""
        import time
        
        theme_manager = ThemeManager(self.settings)
        
        # מדידת זמן החלפת ערכת נושא
        start_time = time.time()
        for _ in range(5):
            theme_manager.toggle_theme(self.test_widget)
        end_time = time.time()
        
        # בדיקה שהחלפת ערכת נושא מהירה (פחות מ-2 שניות ל-5 החלפות)
        self.assertLess(end_time - start_time, 2.0)
    
    def test_error_handling(self):
        """בדיקת טיפול בשגיאות"""
        # בדיקת מנהל ערכות נושא עם widget לא תקין
        theme_manager = ThemeManager(self.settings)
        
        # לא צריך לזרוק exception
        try:
            theme_manager.apply_theme("invalid_theme", None)
            theme_manager.toggle_theme(None)
        except Exception as e:
            self.fail(f"טיפול בשגיאות נכשל: {e}")
    
    def test_settings_persistence(self):
        """בדיקת שמירת הגדרות"""
        # בדיקת שמירת ערכת נושא
        theme_manager = ThemeManager(self.settings)
        original_theme = theme_manager.current_theme
        
        theme_manager.toggle_theme(self.test_widget)
        theme_manager.save_theme_preference()
        
        # יצירת מנהל חדש - צריך לטעון את ההגדרה השמורה
        new_theme_manager = ThemeManager(self.settings)
        self.assertNotEqual(new_theme_manager.current_theme, original_theme)
        
        # בדיקת שמירת גודל גופן
        font_manager = FontManager(self.settings)
        original_size = font_manager.current_font_size
        
        font_manager.increase_font_size(self.test_widget)
        font_manager.save_font_size()
        
        # יצירת מנהל חדש
        new_font_manager = FontManager(self.settings)
        self.assertNotEqual(new_font_manager.current_font_size, original_size)

def run_tests():
    """הרצת כל הבדיקות"""
    print("מתחיל בדיקות שיפורי העיצוב...")
    
    # יצירת test suite
    loader = unittest.TestLoader()
    suite = loader.loadTestsFromTestCase(TestUIEnhancements)
    
    # הרצת הבדיקות
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    # סיכום תוצאות
    print(f"\nסיכום בדיקות:")
    print(f"בדיקות שהצליחו: {result.testsRun - len(result.failures) - len(result.errors)}")
    print(f"בדיקות שנכשלו: {len(result.failures)}")
    print(f"שגיאות: {len(result.errors)}")
    
    if result.failures:
        print("\nכשלונות:")
        for test, traceback in result.failures:
            print(f"- {test}: {traceback}")
    
    if result.errors:
        print("\nשגיאות:")
        for test, traceback in result.errors:
            print(f"- {test}: {traceback}")
    
    return result.wasSuccessful()

if __name__ == "__main__":
    success = run_tests()
    sys.exit(0 if success else 1)