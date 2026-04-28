"""
Multi-factor risk scoring for vulnerabilities.

Formula:
  risk_score = severity(0.4) + exposure(0.3) + exploitability(0.2) + business_impact(0.1)
"""

SEVERITY_WEIGHTS = {
    'CRITICAL': 1.0,
    'HIGH':     0.75,
    'MEDIUM':   0.5,
    'LOW':      0.25,
}

CONFIDENCE_WEIGHTS = {
    'HIGH':   1.0,
    'MEDIUM': 0.7,
    'LOW':    0.4,
}

# (filename patterns, exposure_score)
_EXPOSURE_RULES = [
    (['views', 'routes', 'controller', 'api', 'endpoint', 'handler', 'urls', 'router', 'rest', 'graphql', 'webhook'], 1.0),
    (['auth', 'login', 'token', 'session', 'password', 'oauth', 'jwt', 'credential', 'secret', 'key'],                 0.9),
    (['model', 'schema', 'serializer', 'form', 'service', 'repository', 'dao', 'orm', 'migration'],                    0.6),
    (['util', 'helper', 'config', 'setting', 'middleware', 'mixin', 'base', 'core'],                                   0.45),
    (['test', 'spec', 'mock', 'fixture', 'stub'],                                                                       0.2),
]


def _estimate_exposure(filename: str) -> float:
    if not filename:
        return 0.5
    lower = filename.lower()
    for patterns, score in _EXPOSURE_RULES:
        if any(p in lower for p in patterns):
            return score
    return 0.5


def compute_risk_score(severity: str, confidence: str, filename: str, llm_score: float) -> float:
    """
    Returns a risk score in [0.0, 1.0].
    A higher score means the vulnerability should be fixed first.
    """
    sev    = SEVERITY_WEIGHTS.get(severity, 0.5)
    conf   = CONFIDENCE_WEIGHTS.get(confidence, 0.7)
    expo   = _estimate_exposure(filename)
    explo  = llm_score if llm_score and llm_score > 0 else sev * 0.8
    impact = sev * conf

    score = sev * 0.4 + expo * 0.3 + explo * 0.2 + impact * 0.1
    return round(min(score, 1.0), 3)
