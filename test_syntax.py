#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
בדיקת syntax של הקוד
"""

import sys
import os

def test_syntax():
    """בדיקת syntax של הקובץ הראשי"""
    try:
        # קריאת הקובץ עם encoding נכון
        with open('‏‏‏‏otzaria_sync_offline.py', 'r', encoding='utf-8') as f:
            code = f.read()
        
        # בדיקת syntax
        compile(code, '‏‏‏‏otzaria_sync_offline.py', 'exec')
        print('✅ הקוד עובר בדיקת syntax')
        return True
        
    except SyntaxError as e:
        print(f'❌ שגיאת syntax: {e}')
        print(f'שורה {e.lineno}: {e.text}')
        return False
        
    except Exception as e:
        print(f'⚠️ שגיאה אחרת: {e}')
        return False

if __name__ == "__main__":
    success = test_syntax()
    sys.exit(0 if success else 1)