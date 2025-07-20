from exif.image_data import ImageData


def test_normalize_date():
    assert ImageData.normalize_date("2020-01-02 12:34:00") == "2020-01-02 12:34"
    assert ImageData.normalize_date("") == "1900-01-01 00:00"
    assert ImageData.normalize_date("1900") == "1900-01-01 00:00"


def test_normalize_parent_date():
    assert (
        ImageData.normalize_parent_date("2012-06-04 Cousin Camp") == "2012-06-04 00:00"
    )
    assert ImageData.normalize_parent_date("") == "1900-01-01 00:00"
    assert ImageData.normalize_parent_date("2012-06") == "2012-06-01 00:00"


def test_strip_time():
    assert ImageData.strip_time("2020-01-02 12:34:00") == "2020-01-02"
    assert ImageData.strip_time("") == "1900-01-01"


def test_get_condition():
    assert ImageData.get_condition("2020-01-01", "2020-01-01", "2020-01-01") == (
        "P Date = F Date = I Date",
        "Match",
    )
    assert (
        ImageData.get_condition("2020-01-01", "2020-01-01", "2020-01-02")[1]
        == "Partial"
    )
    assert (
        ImageData.get_condition("2020-01-01", "2020-01-02", "2020-01-01")[1]
        == "Partial"
    )
    assert (
        ImageData.get_condition("2020-01-02", "2020-01-01", "2020-01-01")[1]
        == "Partial"
    )
    assert (
        ImageData.get_condition("2020-01-01", "2020-01-02", "2020-01-03")[1]
        == "Mismatch"
    )


def test_extract_alt_filename_date():
    parent_date = "2020-01-01 00:00"
    assert (
        ImageData.extract_alt_filename_date("IMG_20200101_123456.jpg", parent_date)
        == "2020-01-01 12:34"
    )
    assert (
        ImageData.extract_alt_filename_date("IMG_2020-01-01_123456.jpg", parent_date)
        == "2020-01-01 12:34"
    )
    assert (
        ImageData.extract_alt_filename_date("IMG_20200101.jpg", parent_date)
        == "2020-01-01"
    )
    assert (
        ImageData.extract_alt_filename_date("IMG_2020-01-01.jpg", parent_date)
        == "2020-01-01"
    )
    assert ImageData.extract_alt_filename_date("IMG_20190101.jpg", parent_date) == ""


def test_getFilenameDate():
    assert ImageData.getFilenameDate("2020-01-02_test.jpg") == "2020-01-02 00:00"
    assert ImageData.getFilenameDate("2020-01_test.jpg") == "2020-01-01 00:00"
    assert ImageData.getFilenameDate("2020_01_02_test.jpg") == "2020-01-02 00:00"
    assert ImageData.getFilenameDate("2020_01_test.jpg") == "2020-01-01 00:00"
    assert ImageData.getFilenameDate("test.jpg") == "1900-01-01 00:00"


def test_getParentName(tmp_path):
    d = tmp_path / "2020-01-02"
    d.mkdir()
    f = d / "test.jpg"
    f.write_text("")
    assert ImageData.getParentName(str(f)) == "2020-01-02"
    d2 = tmp_path / "1234"
    d2.mkdir()
    f2 = d2 / "test.jpg"
    f2.write_text("")
    assert ImageData.getParentName(str(f2)) == "1234"
    d3 = tmp_path / "foo"
    d3.mkdir()
    f3 = d3 / "test.jpg"
    f3.write_text("")
    assert ImageData.getParentName(str(f3)) == "foo"


def test_getTrueExt(monkeypatch):
    def fake_get_exif(filepath):
        return {"FileTypeExtension": "JPG"}

    monkeypatch.setattr(ImageData, "get_exif", staticmethod(fake_get_exif))
    assert ImageData.getTrueExt("foo.jpg") == "jpg"
    monkeypatch.setattr(ImageData, "get_exif", staticmethod(lambda x: {}))
    assert ImageData.getTrueExt("foo.JPG") == "jpg"


def test_getImageSize(monkeypatch):
    def fake_get_exif(filepath):
        return {"ImageWidth": 100, "ImageHeight": 200}

    monkeypatch.setattr(ImageData, "get_exif", staticmethod(fake_get_exif))
    assert ImageData.getImageSize("foo.jpg") == ("100", "200")
    monkeypatch.setattr(ImageData, "get_exif", staticmethod(lambda x: {}))
    assert ImageData.getImageSize("foo.jpg") == ("", "")


def test_getTargetFilename(monkeypatch, tmp_path):
    def fake_get_exif(filepath):
        return {
            "FileTypeExtension": "jpg",
            "ImageWidth": 100,
            "ImageHeight": 200,
            "DateTimeOriginal": "2020:01:02 12:34:00",
        }

    monkeypatch.setattr(ImageData, "get_exif", staticmethod(fake_get_exif))
    f = tmp_path / "2020-01-02" / "test.jpg"
    f.parent.mkdir()
    f.write_text("")
    target = ImageData.getTargetFilename(str(f), str(tmp_path), label="test")
    assert "2020-01-02_1234_test_100x200_2020-01-02_test.jpg" in target


def test_getImageDate(monkeypatch):
    def fake_get_exif(filepath):
        return {"DateTimeOriginal": "2020:01:02 12:34:00"}

    monkeypatch.setattr(ImageData, "get_exif", staticmethod(fake_get_exif))
    assert ImageData.getImageDate("foo.jpg") == "2020-01-02 12:34"
    monkeypatch.setattr(ImageData, "get_exif", staticmethod(lambda x: {}))
    assert ImageData.getImageDate("foo.jpg") == "1900-01-01 00:00"
