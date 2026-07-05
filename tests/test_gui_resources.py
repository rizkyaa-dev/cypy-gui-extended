from cypy.gui.resources import apply_window_icon, asset_path


class FakeRoot:
    def __init__(self):
        self.calls = []

    def iconphoto(self, default, icon):
        self.calls.append((default, icon))


def test_default_gui_icon_exists():
    assert asset_path("favicon.png").is_file()


def test_apply_window_icon_keeps_image_reference(tmp_path):
    icon_path = tmp_path / "icon.png"
    icon_path.write_bytes(b"fake")
    root = FakeRoot()
    icon = object()

    loaded = apply_window_icon(
        root,
        icon_path=icon_path,
        image_factory=lambda **kwargs: icon,
    )

    assert loaded is True
    assert root.calls == [(True, icon)]
    assert root._cypy_window_icon is icon


def test_missing_window_icon_is_non_fatal(tmp_path):
    root = FakeRoot()

    assert apply_window_icon(root, icon_path=tmp_path / "missing.png") is False
    assert root.calls == []
