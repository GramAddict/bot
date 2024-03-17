from GramAddict.core.interaction import _load_and_clean_txt_file


def test_load_txt_ok(mocker):
    mocker.patch("os.path.join", return_value="txt/txt_ok.txt")
    message = _load_and_clean_txt_file("test_user", "txt_filename")
    assert message is not None
    assert message == [
        "Hello, test_user! How are you today?",
        "Hello everyone!",
        "Goodbye, test_user! Have a great day!",
    ]


def test_load_txt_empty(mocker):
    mocker.patch("os.path.join", return_value="txt/txt_empty.txt")
    message = _load_and_clean_txt_file("test_user", "txt_filename")
    assert message is None


def test_load_txt_not_exists(mocker):
    mocker.patch("os.path.join", return_value="txt/txt_not_exists.txt")
    message = _load_and_clean_txt_file("test_user", "txt_filename")
    assert message is None
