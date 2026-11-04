"""Rule-based report checks shared by the critic node and the eval script."""
import json
import re

NUM = re.compile(r"(?<![\w.])-?\d[\d,]*(?:\.\d+)?")
WINDOWS = {12, 14, 20, 26, 30, 50, 52, 70, 100, 200}  # indicator settings and RSI 30/70 thresholds, not data
TRADE = re.compile(r"\b(you should (buy|sell)|i recommend (buying|selling)|strong buy|strong sell|buy now|sell now|guaranteed|will (rise|fall|double))\b", re.I)
DISCLAIMER = "not financial advice"


def numbers(text: str) -> list[float]:
    out = []
    for m in NUM.findall(text):
        try:
            out.append(float(m.replace(",", "")))
        except ValueError:
            pass
    return out


def ungrounded_numbers(draft: str, findings: list) -> list[float]:
    """Numbers in the draft that do not appear (within rounding) in the tool evidence."""
    evidence = numbers(json.dumps([f.evidence for f in findings], default=str))
    bad = []
    for x in numbers(draft):
        if (x == int(x) and 0 <= abs(x) <= 10) or x in WINDOWS or (x == int(x) and 1990 <= x <= 2100):
            continue
        if not any(abs(abs(x) - abs(y)) <= max(0.011, 0.005 * abs(y)) for y in evidence):
            bad.append(x)
    return list(dict.fromkeys(bad))


def rule_issues(draft: str, findings: list) -> list[str]:
    issues = []
    bad = ungrounded_numbers(draft, findings)
    if bad:
        issues.append("These numbers are not in the evidence, remove or replace them: " + ", ".join(str(b) for b in bad[:6]))
    if TRADE.search(draft):
        issues.append("The report gives a trade instruction or promises an outcome. Describe the data instead.")
    if "risk" not in draft.lower():
        issues.append("Add a Risks section.")
    return issues
