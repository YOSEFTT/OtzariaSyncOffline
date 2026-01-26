# הוראות בנייה - OtzariaSyncOffline

## דרישות מקדימות

### כל הפלטפורמות
```bash
pip install -r requirements.txt
pip install pyinstaller
```

### macOS נוסף
```bash
# עבור Apple Silicon (M1/M2/M3)
pip install pyinstaller --target arm64

# עבור Intel
pip install pyinstaller --target x86_64
```

### Linux נוסף
```bash
# Ubuntu/Debian
sudo apt-get install python3-dev python3-pip

# Fedora
sudo dnf install python3-devel
```

## בנייה

### בנייה פשוטה (לפלטפורמה הנוכחית)
```bash
python build_all_platforms.py
```

### בנייה ידנית

#### Windows
```bash
pyinstaller --onefile --windowed --name=OtzariaSyncOffline --icon=build/sync_otzaria.ico otzaria_sync_offline.py
```

#### Linux
```bash
pyinstaller --onefile --windowed --name=OtzariaSyncOffline otzaria_sync_offline.py
```

#### macOS Intel
```bash
pyinstaller --onefile --windowed --name=OtzariaSyncOffline --target-arch=x86_64 --osx-bundle-identifier=com.otzaria.syncoffline otzaria_sync_offline.py
```

#### macOS Apple Silicon (M1/M2/M3)
```bash
pyinstaller --onefile --windowed --name=OtzariaSyncOffline --target-arch=arm64 --osx-bundle-identifier=com.otzaria.syncoffline otzaria_sync_offline.py
```

## יצירת אייקון ל-macOS

אם יש לך קובץ ICO ואתה רוצה להמיר אותו ל-ICNS עבור macOS:

```bash
# התקנת כלי המרה
pip install Pillow

# המרה (סקריפט Python)
from PIL import Image
img = Image.open('build/sync_otzaria.ico')
img.save('build/sync_otzaria.icns')
```

## פלט

הקבצים הבנויים יימצאו בתיקייה `dist/`:
- `dist/windows/OtzariaSyncOffline.exe`
- `dist/linux/OtzariaSyncOffline`
- `dist/macos-intel/OtzariaSyncOffline.app`
- `dist/macos-arm/OtzariaSyncOffline.app`

## הערות חשובות

1. **PyInstaller לא תומך ב-cross-compilation** - כדי לבנות לפלטפורמה מסוימת, צריך להריץ את הבנייה על אותה פלטפורמה.

2. **macOS Gatekeeper** - משתמשי macOS עשויים לקבל אזהרה בפתיחה ראשונה. יש ללחוץ ימני → פתח.

3. **Linux permissions** - לאחר הבנייה, יש לתת הרשאות הרצה:
   ```bash
   chmod +x dist/linux/OtzariaSyncOffline
   ```

## GitHub Actions (CI/CD)

לבנייה אוטומטית לכל הפלטפורמות, ראה את קובץ `.github/workflows/build.yml`
