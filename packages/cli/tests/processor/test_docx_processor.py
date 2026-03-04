import zipfile

import pytest
from cli.processor.docx_processor import chunk_docx

pytestmark = pytest.mark.medium

_NS_PKG = "http://schemas.openxmlformats.org/package/2006"
_NS_DOC = "http://schemas.openxmlformats.org/officeDocument/2006"
_NS_WML = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"

_CONTENT_TYPES = (
    '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
    f'<Types xmlns="{_NS_PKG}/content-types">'
    '<Default Extension="rels"'
    ' ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
    '<Default Extension="xml" ContentType="application/xml"/>'
    '<Override PartName="/word/document.xml"'
    " ContentType="
    '"application/vnd.openxmlformats-officedocument'
    '.wordprocessingml.document.main+xml"/>'
    '<Override PartName="/word/styles.xml"'
    " ContentType="
    '"application/vnd.openxmlformats-officedocument'
    '.wordprocessingml.styles+xml"/>'
    "</Types>"
)

_RELS = (
    '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
    f'<Relationships xmlns="{_NS_PKG}/relationships">'
    '<Relationship Id="rId1"'
    f' Type="{_NS_DOC}/relationships/officeDocument"'
    ' Target="word/document.xml"/>'
    "</Relationships>"
)

_DOC_RELS = (
    '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
    f'<Relationships xmlns="{_NS_PKG}/relationships">'
    '<Relationship Id="rId1"'
    f' Type="{_NS_DOC}/relationships/styles"'
    ' Target="styles.xml"/>'
    "</Relationships>"
)

_STYLES = (
    '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
    f'<w:styles xmlns:w="{_NS_WML}">'
    '<w:style w:type="paragraph" w:styleId="Heading1">'
    '<w:name w:val="heading 1"/>'
    "</w:style>"
    '<w:style w:type="paragraph" w:styleId="Heading2">'
    '<w:name w:val="heading 2"/>'
    "</w:style>"
    "</w:styles>"
)


def _make_docx(tmp_path, paragraphs: list[tuple[str | None, str]], name="test.docx"):
    """paragraphs: [(style_id, text), ...] style_id=None で Normal 段落"""
    paras_xml = ""
    for style_id, text in paragraphs:
        if style_id:
            paras_xml += (
                f"<w:p>"
                f'<w:pPr><w:pStyle w:val="{style_id}"/></w:pPr>'
                f"<w:r><w:t>{text}</w:t></w:r>"
                f"</w:p>"
            )
        else:
            paras_xml += f"<w:p><w:r><w:t>{text}</w:t></w:r></w:p>"

    document_xml = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        f'<w:document xmlns:w="{_NS_WML}">'
        f"<w:body>{paras_xml}</w:body>"
        "</w:document>"
    )

    docx_path = tmp_path / name
    with zipfile.ZipFile(docx_path, "w") as zf:
        zf.writestr("[Content_Types].xml", _CONTENT_TYPES)
        zf.writestr("_rels/.rels", _RELS)
        zf.writestr("word/_rels/document.xml.rels", _DOC_RELS)
        zf.writestr("word/styles.xml", _STYLES)
        zf.writestr("word/document.xml", document_xml)
    return docx_path


def test_empty_document(tmp_path):
    f = _make_docx(tmp_path, [])
    assert chunk_docx(f) == []


def test_body_only(tmp_path):
    f = _make_docx(tmp_path, [(None, "本文テキストです。")])
    result = chunk_docx(f)
    assert len(result) == 1
    assert "本文テキスト" in result[0]


def test_heading_with_body(tmp_path):
    f = _make_docx(tmp_path, [("Heading1", "見出し1"), (None, "本文テキストです。")])
    result = chunk_docx(f, chunk_size=1000)
    assert len(result) == 1
    assert result[0].startswith("# 見出し1")
    assert "本文テキスト" in result[0]


def test_multiple_sections(tmp_path):
    paragraphs = [
        ("Heading1", "セクション1"),
        (None, "セクション1の本文。"),
        ("Heading2", "セクション2"),
        (None, "セクション2の本文。"),
    ]
    f = _make_docx(tmp_path, paragraphs)
    result = chunk_docx(f, chunk_size=1000)
    assert len(result) == 2
    assert "セクション1の本文" in result[0]
    assert "セクション2の本文" in result[1]


def test_long_body_splits(tmp_path):
    body = "あいうえお。" * 50
    f = _make_docx(tmp_path, [("Heading1", "長い本文"), (None, body)])
    result = chunk_docx(f, chunk_size=100, overlap=0, min_chunk=0)
    assert len(result) >= 2
    for chunk in result:
        assert chunk.startswith("# 長い本文\n")
