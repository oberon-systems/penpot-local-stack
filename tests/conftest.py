import io
import zipfile

import pytest


@pytest.fixture
def archive():
    def build(files: dict[str, bytes]) -> zipfile.ZipFile:
        buffer = io.BytesIO()
        with zipfile.ZipFile(buffer, "w") as zf:
            for name, content in files.items():
                zf.writestr(name, content)
        return zipfile.ZipFile(buffer)

    return build
