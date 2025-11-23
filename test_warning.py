#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
בדיקה מהירה של הודעת האזהרה
"""

import sys
from PyQt6.QtWidgets import QApplication

# ייבוא התוכנה
from otzaria_sync_offline import OtzariaSync

if __name__ == "__main__":
    app = QApplication(sys.argv)
    
    # יצירת החלון הראשי
    window = OtzariaSync()
    window.show()
    
    print("התוכנה נטענה בהצלחה!")
    print("ההודעה אמורה להופיע אוטומטית אחרי 0.5 שניות")
    
    sys.exit(app.exec())
