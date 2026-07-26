# Operations

## Local workspace layout

```text
CutDirective/
  Projects/
    YYYY-MM-DD_Project-Name/
      01_Originals/
      02_Assets/
      03_Analysis/
      04_Edit-Plans/
      05_Previews/
      06_Final-Exports/
      07_Captions/
      08_Thumbnails/
      09_Logs/
      10_Archive/
```

## Backup

- The SQLite database can be copied while the app is offline.
- Project folders are self-contained and can be archived from `10_Archive`.

## Disk cleanup

- Temporary proxies can be removed from `03_Analysis` without affecting originals or final exports.
- Logs are rotated to `09_Logs`.
- Retention rules are configurable in Settings.
