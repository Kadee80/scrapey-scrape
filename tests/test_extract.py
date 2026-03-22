from app.extract_heuristic import extract_heuristic


def test_extract_meta_and_jsonld():
    html = """
    <!doctype html>
    <html><head>
    <title>Old Title</title>
    <meta property="og:title" content="Acme Corp" />
    <meta property="og:description" content="We build widgets." />
    <script type="application/ld+json">
    {"@context":"https://schema.org","@type":"Organization","name":"Acme Inc",
     "address":{"addressLocality":"Austin","addressRegion":"TX"}}
    </script>
    </head><body>
    <h1>Welcome</h1>
    <a href="mailto:sales@acme.com">Email</a>
    <a href="https://linkedin.com/company/acme">LI</a>
    </body></html>
    """
    s = extract_heuristic(html, "https://acme.com/")
    assert s.company_name
    assert "Acme" in s.company_name
    assert s.description and "widget" in s.description.lower()
    assert "sales@acme.com" in s.emails
    assert "LinkedIn" in s.social_urls
    assert s.coverage_score > 0.3


def test_extract_respects_company_hint():
    html = "<html><head><title>Generic</title></head><body></body></html>"
    s = extract_heuristic(html, "https://x.com/", company_hint="My Client")
    assert s.company_name == "My Client"
