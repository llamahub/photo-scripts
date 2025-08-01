import os
import re
import subprocess
import json
from pathlib import Path


class ImageData:
    @staticmethod
    def get_exif(filepath):
        try:
            result = subprocess.run(
                [
                    "exiftool",
                    "-j",
                    "-DateTimeOriginal",
                    "-ExifIFD:DateTimeOriginal",
                    "-XMP-photoshop:DateCreated",
                    "-FileModifyDate",
                    "-FileTypeExtension",
                    "-ImageWidth",
                    "-ImageHeight",
                    filepath,
                ],
                capture_output=True,
                text=True,
            )
            if result.returncode == 0:
                data = json.loads(result.stdout)[0]
                return data
        except Exception:
            pass
        return {}

    @staticmethod
    def normalize_date(dt):
        if not dt or dt.startswith("1900"):
            return "1900-01-01 00:00"
        m = re.match(
            r"(\d{4})[-_](\d{2})[-_](\d{2})[ T_]?([0-9]{2})?:?([0-9]{2})?:?([0-9]{2})?",
            dt,
        )
        if m:
            year = m.group(1)
            month = m.group(2)
            day = m.group(3) if m.group(3) else "01"
            hour = m.group(4) if m.group(4) else "00"
            minute = m.group(5) if m.group(5) else "00"
            return f"{year}-{month}-{day} {hour}:{minute}"
        return "1900-01-01 00:00"

    @staticmethod
    def normalize_parent_date(parent):
        if not parent:
            return "1900-01-01 00:00"
        m = re.match(r"^(\d{4})(?:-(\d{2}))?(?:-(\d{2}))?", parent)
        if m:
            year = m.group(1)
            month = m.group(2) if m.group(2) else "01"
            day = m.group(3) if m.group(3) else "01"
            return f"{year}-{month}-{day} 00:00"
        return "1900-01-01 00:00"

    @staticmethod
    def strip_time(dt):
        m = re.match(r"(\d{4}-\d{2}-\d{2})", dt)
        return m.group(1) if m else "1900-01-01"

    @staticmethod
    def get_condition(p, f, i):
        if p == f == i:
            return "P Date = F Date = I Date", "Match"
        if p == f:
            if f < i:
                return "P Date = F Date < I Date", "Partial"
            elif f > i:
                return "P Date = F Date > I Date", "Partial"
        if p == i:
            if i < f:
                return "P Date = I Date < F Date", "Partial"
            elif i > f:
                return "P Date = I Date > F Date", "Partial"
        if f == i:
            if i < p:
                return "F Date = I Date < P Date", "Partial"
            elif i > p:
                return "F Date = I Date > P Date", "Partial"
        return "Else", "Mismatch"

    @staticmethod
    def extract_alt_filename_date(source_path, parent_date):
        parent_year = parent_date[:4]
        base = os.path.basename(source_path)
        patterns = [
            rf"({parent_year})(\d{{2}})(\d{{2}})[_\- ]?(\d{{2}})(\d{{2}})(\d{{2}})",
            rf"({parent_year})-(\d{{2}})-(\d{{2}})[_\- ]?(\d{{2}})(\d{{2}})(\d{{2}})",
            rf"({parent_year})(\d{{2}})(\d{{2}})",
            rf"({parent_year})-(\d{{2}})-(\d{{2}})",
        ]
        for pat in patterns:
            m = re.search(pat, base)
            if m:
                try:
                    year = m.group(1)
                    month = m.group(2)
                    day = m.group(3)
                    if m.lastindex >= 6:
                        hour = m.group(4)
                        minute = m.group(5)
                        # second = m.group(6) if m.lastindex >= 6 else "00"
                        return f"{year}-{month}-{day} {hour}:{minute}"
                    else:
                        return f"{year}-{month}-{day}"
                except Exception:
                    continue
        return ""

    @classmethod
    def getImageDate(cls, filepath):
        meta = cls.get_exif(filepath)
        for key in [
            "DateTimeOriginal",
            "ExifIFD:DateTimeOriginal",
            "XMP-photoshop:DateCreated",
            "FileModifyDate",
        ]:
            if key in meta and meta[key]:
                dt = meta[key]
                dt = re.sub(
                    r"^(\d{4})[:_-](\d{2})[:_-](\d{2})[ T_]?(\d{2})?:?(\d{2})?:?(\d{2})?",
                    r"\1-\2-\3 \4:\5:\6",
                    dt,
                )
                return cls.normalize_date(dt)
        return "1900-01-01 00:00"

    @classmethod
    def getFilenameDate(cls, filename):
        base = os.path.basename(filename)
        patterns = [
            (
                r"^(\d{4})-(\d{2})-(\d{2})",
                lambda m: f"{m.group(1)}-{m.group(2)}-{m.group(3)}",
            ),
            (r"^(\d{4})-(\d{2})", lambda m: f"{m.group(1)}-{m.group(2)}-01"),
            (
                r"^(\d{4})_(\d{2})_(\d{2})",
                lambda m: f"{m.group(1)}-{m.group(2)}-{m.group(3)}",
            ),
            (r"^(\d{4})_(\d{2})", lambda m: f"{m.group(1)}-{m.group(2)}-01"),
        ]
        for pat, func in patterns:
            m = re.match(pat, base)
            if m:
                return cls.normalize_date(func(m))
        return "1900-01-01 00:00"

    @classmethod
    def getTrueExt(cls, filepath):
        meta = cls.get_exif(filepath)
        return meta.get("FileTypeExtension", Path(filepath).suffix.lstrip(".")).lower()

    @classmethod
    def getImageSize(cls, filepath):
        meta = cls.get_exif(filepath)
        width = str(meta.get("ImageWidth", ""))
        height = str(meta.get("ImageHeight", ""))
        return width, height

    @classmethod
    def getParentName(cls, filepath):
        parent = Path(filepath).parent.name
        if (
            re.match(r"^\d{4}$", parent)
            or re.match(r"^\d{4}-\d{2}$", parent)
            or re.match(r"^\d{4}-\d{2}-\d{2}$", parent)
        ):
            return parent
        if re.match(r"^[\d_\- ]+$", parent):
            return ""
        return parent

    @classmethod
    def getTargetFilename(cls, sourceFilePath, targetRoot, label=""):
        parentName = cls.getParentName(sourceFilePath)
        baseName = Path(sourceFilePath).stem
        target_pat = re.compile(
            r"^\d{4}-\d{2}-\d{2}_[0-9]{4}(?:_[^_]+)?_[0-9]+x[0-9]+(?:_[^_]+)?_(.+)$"
        )
        m = target_pat.match(baseName)
        if m:
            baseName = m.group(1)
        trueExt = cls.getTrueExt(sourceFilePath)
        width, height = cls.getImageSize(sourceFilePath)
        imageDate = cls.getImageDate(sourceFilePath)
        if not imageDate:
            imageDate = cls.getFilenameDate(sourceFilePath)
        if not imageDate:
            imageDate = "1900-01-01 00:00"
        year = imageDate[:4]
        month = imageDate[5:7]
        day = imageDate[8:10]
        hour = imageDate[11:13] if len(imageDate) > 10 else "00"
        minute = imageDate[14:16] if len(imageDate) > 13 else "00"
        parentPart = f"_{parentName}" if parentName else ""
        labelPart = f"_{label}" if label else ""
        folderName = parentName if parentName else f"{year}-{month}{labelPart}"
        targetFolderPath = os.path.join(targetRoot, year, folderName)
        filename = f"{year}-{month}-{day}_{hour}{minute}{labelPart}_{width}x{height}{parentPart}_{baseName}.{trueExt}"
        return os.path.join(targetFolderPath, filename)
