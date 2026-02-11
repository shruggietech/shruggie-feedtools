"""Generate the UTF-8 BOM fixture file with actual BOM bytes."""
from pathlib import Path

xml_content = """\
<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0">
  <channel>
    <title>UTF-8 BOM &amp; Encoding Test \u2014 \u00dcn\u00efc\u00f6d\u00e9 F\u00eb\u00ebd</title>
    <link>https://encoding.example.com</link>
    <description>Testing UTF-8 BOM, HTML entities, and Unicode: \u00e9 \u00e0 \u00fc \u00f1 \u00df \u4e2d\u6587 \u65e5\u672c\u8a9e \ud55c\uad6d\uc5b4 \U0001f680</description>
    <item>
      <title>\u00dcn\u00efc\u00f6d\u00e9 T\u00edtl\u00e9 with \u00c9mojis \U0001f389\U0001f40d</title>
      <link>https://encoding.example.com/unicode-post</link>
      <guid>enc-001</guid>
      <pubDate>Mon, 10 Feb 2026 12:00:00 GMT</pubDate>
      <description>This item has Unicode: caf\u00e9, na\u00efve, r\u00e9sum\u00e9, El Ni\u00f1o, Stra\u00dfe, \u2603 snowman</description>
    </item>
    <item>
      <title>HTML Entities &amp; CDATA</title>
      <link>https://encoding.example.com/entities-post</link>
      <guid>enc-002</guid>
      <pubDate>Sun, 09 Feb 2026 08:00:00 GMT</pubDate>
      <description>Entities: &amp;amp; &amp;lt; &amp;gt; &amp;quot; and special: &lt;b&gt;bold&lt;/b&gt;</description>
    </item>
  </channel>
</rss>
"""

out = Path("tests/fixtures/edge_cases/encoding_utf8_bom.xml")
data = b"\xef\xbb\xbf" + xml_content.encode("utf-8")
out.write_bytes(data)
print(f"Written {len(data)} bytes, BOM present: {data[:3] == b'\\xef\\xbb\\xbf'}")
