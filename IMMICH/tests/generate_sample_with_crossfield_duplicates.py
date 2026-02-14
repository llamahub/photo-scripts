import piexif
from PIL import Image
import io
import subprocess

# Create a simple JPEG image
img = Image.new('RGB', (10, 10), color='white')
output = io.BytesIO()
img.save(output, format='JPEG')
img_bytes = output.getvalue()

# Add EXIF tags: ARCHIVE_DUP in XPKeywords, Keywords, Subject, IPTC:Keywords, but only once per field
exif_dict = {"0th": {}, "Exif": {}, "GPS": {}, "1st": {}, "thumbnail": None}
# XPKeywords (Windows tag, UTF-16LE)
exif_dict["0th"][piexif.ImageIFD.XPKeywords] = "ARCHIVE_DUP".encode('utf-16le')
exif_bytes = piexif.dump(exif_dict)

# Write the image first, then insert EXIF into the file directly
with open("testdata/sample_with_crossfield_duplicates.jpg", "wb") as f:
    f.write(img_bytes)
piexif.insert(exif_bytes, "testdata/sample_with_crossfield_duplicates.jpg")

# Use exiftool to set Keywords, Subject, and IPTC:Keywords to ARCHIVE_DUP (one per field)
subprocess.run([
    "exiftool", "-overwrite_original",
    "-Keywords=ARCHIVE_DUP",
    "-Subject=ARCHIVE_DUP",
    "-IPTC:Keywords=ARCHIVE_DUP",
    "testdata/sample_with_crossfield_duplicates.jpg"
], check=True)
