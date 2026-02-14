import piexif
from PIL import Image
import io

# Create a simple JPEG image
img = Image.new('RGB', (10, 10), color='white')
output = io.BytesIO()
img.save(output, format='JPEG')
img_bytes = output.getvalue()

# Add duplicate EXIF tags using piexif
exif_dict = {"0th": {}, "Exif": {}, "GPS": {}, "1st": {}, "thumbnail": None}
# Add duplicate XPKeywords (Windows tag, as a stand-in for IPTC/Subject)
dup_tag = "ARCHIVE_DUP;ARCHIVE_DUP;ARCHIVE_DUP".encode('utf-16le')
exif_dict["0th"][piexif.ImageIFD.XPKeywords] = dup_tag
exif_bytes = piexif.dump(exif_dict)

# Write the image first, then insert EXIF into the file directly
with open("testdata/sample_with_duplicate_tags.jpg", "wb") as f:
    f.write(img_bytes)
piexif.insert(exif_bytes, "testdata/sample_with_duplicate_tags.jpg")
