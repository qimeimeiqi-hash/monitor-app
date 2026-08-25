from bs4 import BeautifulSoup


class ExtractionError(Exception):
    pass


def extract_text(html: str, selector: str) -> str:
    soup = BeautifulSoup(html, "html.parser")
    matched_elements = soup.select(selector)

    if not matched_elements:
        raise ExtractionError(f"No element matched selector: {selector}")

    raw_text = " ".join(
        element.get_text(separator=" ", strip=True) for element in matched_elements
    )
    normalized_text = " ".join(raw_text.split())
    return normalized_text
