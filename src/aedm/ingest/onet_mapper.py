"""Job title to SOC code mapping using fuzzy matching."""

from __future__ import annotations

from typing import TYPE_CHECKING

import structlog
from thefuzz import fuzz, process

from aedm.config import settings

if TYPE_CHECKING:
    from aedm.models.schemas import Role

logger = structlog.get_logger()

# Common job titles mapped to their SOC codes.
# This is a curated subset — not exhaustive. Fuzzy matching handles variations.
TITLE_TO_SOC: dict[str, str] = {
    # Management (11-0000)
    "Chief Executive Officer": "11-1011",
    "CEO": "11-1011",
    "Chief Operating Officer": "11-1011",
    "COO": "11-1011",
    "Chief Financial Officer": "11-3031",
    "CFO": "11-3031",
    "Chief Technology Officer": "11-9041",
    "CTO": "11-9041",
    "Chief Information Officer": "11-3021",
    "CIO": "11-3021",
    "Chief Marketing Officer": "11-2021",
    "CMO": "11-2021",
    "Chief Human Resources Officer": "11-3111",
    "CHRO": "11-3111",
    "General Manager": "11-1021",
    "Operations Manager": "11-1021",
    "Marketing Manager": "11-2021",
    "Sales Manager": "11-2022",
    "Financial Manager": "11-3031",
    "HR Manager": "11-3111",
    "IT Manager": "11-3021",
    "Engineering Manager": "11-9041",
    "Software Engineering Manager": "11-9041",
    "Director of Engineering": "11-9041",
    "VP of Engineering": "11-9041",
    "Director of Marketing": "11-2021",
    "Director of Sales": "11-2022",
    "Director of Finance": "11-3031",
    "Director of HR": "11-3111",
    "Director of Operations": "11-1021",
    "Product Manager": "11-9041",
    "Project Manager": "11-9199",
    "Program Manager": "11-9199",
    # Business and Financial Operations (13-0000)
    "Accountant": "13-2011",
    "Senior Accountant": "13-2011",
    "Staff Accountant": "13-2011",
    "Financial Analyst": "13-2051",
    "Senior Financial Analyst": "13-2051",
    "Budget Analyst": "13-2031",
    "Management Analyst": "13-1111",
    "Management Consultant": "13-1111",
    "Business Analyst": "13-1111",
    "HR Specialist": "13-1071",
    "HR Coordinator": "13-1071",
    "Human Resources Specialist": "13-1071",
    "Recruiter": "13-1071",
    "Technical Recruiter": "13-1071",
    "Compensation Analyst": "13-1141",
    "Benefits Coordinator": "13-1141",
    "Training Specialist": "13-1151",
    "Compliance Officer": "13-1041",
    "Compliance Analyst": "13-1041",
    "Internal Auditor": "13-2011",
    "Tax Analyst": "13-2082",
    "Accounts Payable Clerk": "43-3031",
    "Accounts Receivable Clerk": "43-3031",
    "Payroll Specialist": "43-3051",
    "Buyer": "13-1021",
    "Purchasing Agent": "13-1023",
    "Supply Chain Analyst": "13-1081",
    "Logistics Coordinator": "13-1081",
    # Computer and Mathematical (15-0000)
    "Software Engineer": "15-1252",
    "Software Engineer I": "15-1252",
    "Software Engineer II": "15-1252",
    "Senior Software Engineer": "15-1252",
    "Staff Software Engineer": "15-1252",
    "Principal Software Engineer": "15-1252",
    "Software Developer": "15-1252",
    "Frontend Developer": "15-1252",
    "Backend Developer": "15-1252",
    "Full Stack Developer": "15-1252",
    "Web Developer": "15-1254",
    "Mobile Developer": "15-1252",
    "DevOps Engineer": "15-1244",
    "Site Reliability Engineer": "15-1244",
    "SRE": "15-1244",
    "Cloud Engineer": "15-1244",
    "Systems Administrator": "15-1244",
    "Database Administrator": "15-1242",
    "DBA": "15-1242",
    "Network Engineer": "15-1241",
    "Network Administrator": "15-1241",
    "Security Engineer": "15-1212",
    "Cybersecurity Analyst": "15-1212",
    "Information Security Analyst": "15-1212",
    "Data Scientist": "15-2051",
    "Senior Data Scientist": "15-2051",
    "Data Analyst": "15-2051",
    "Data Engineer": "15-1252",
    "Machine Learning Engineer": "15-2051",
    "ML Engineer": "15-2051",
    "AI Research Scientist": "15-2051",
    "AI Operations Analyst": "15-2051",
    "Prompt Engineer": "15-1252",
    "AI Integration Developer": "15-1252",
    "QA Engineer": "15-1253",
    "Quality Assurance Analyst": "15-1253",
    "Test Engineer": "15-1253",
    "UX Designer": "15-1255",
    "UI Designer": "15-1255",
    "UX Researcher": "15-1255",
    # Architecture and Engineering (17-0000)
    "Mechanical Engineer": "17-2141",
    "Electrical Engineer": "17-2071",
    "Civil Engineer": "17-2051",
    "Industrial Engineer": "17-2112",
    # Life, Physical, and Social Science (19-0000)
    "Research Scientist": "19-1042",
    "Chemist": "19-2031",
    "Environmental Scientist": "19-2041",
    # Legal (23-0000)
    "Lawyer": "23-1011",
    "Attorney": "23-1011",
    "General Counsel": "23-1011",
    "Corporate Counsel": "23-1011",
    "Legal Counsel": "23-1011",
    "Paralegal": "23-2011",
    "Legal Assistant": "23-2011",
    "Contract Specialist": "23-2011",
    # Arts, Design, Entertainment (27-0000)
    "Graphic Designer": "27-1024",
    "Technical Writer": "27-3042",
    "Copywriter": "27-3043",
    "Content Strategist": "27-3043",
    "Content AI Specialist": "27-3043",
    "Video Producer": "27-4032",
    "Editor": "27-3041",
    # Sales (41-0000)
    "Sales Representative": "41-4012",
    "Account Executive": "41-4012",
    "Sales Engineer": "41-9031",
    "Business Development Representative": "41-4012",
    "BDR": "41-4012",
    "Account Manager": "41-4012",
    "Sales Director": "11-2022",
    "Regional Sales Manager": "11-2022",
    # Office and Administrative Support (43-0000)
    "Administrative Assistant": "43-6014",
    "Executive Assistant": "43-6011",
    "Office Manager": "43-1011",
    "Receptionist": "43-4171",
    "Data Entry Clerk": "43-9021",
    "File Clerk": "43-4071",
    "Mail Clerk": "43-9051",
    "Customer Service Representative": "43-4051",
    "Customer Support Specialist": "43-4051",
    "Document Control Specialist": "43-4071",
    # Building and Grounds (37-0000)
    "Facilities Manager": "37-1012",
    "Janitor": "37-2011",
    "Groundskeeper": "37-3011",
    "Custodian": "37-2011",
    # Protective Service (33-0000)
    "Security Guard": "33-9032",
    "Security Officer": "33-9032",
    # Installation, Maintenance, Repair (49-0000)
    "Maintenance Technician": "49-9071",
    "HVAC Technician": "49-9021",
    "Electrician": "47-2111",
    # Production (51-0000)
    "Manufacturing Technician": "51-9199",
    "Quality Inspector": "51-9061",
    # Transportation and Material Moving (53-0000)
    "Warehouse Worker": "53-7065",
    "Forklift Operator": "53-7051",
    "Truck Driver": "53-3032",
    "Delivery Driver": "53-3031",
    "Shipping Clerk": "43-5071",
    # AI-specific emerging roles (mapped to closest SOC)
    "AI Ethics Coordinator": "13-1041",
    "AI Trainer": "15-2051",
}


def map_title_to_soc(title: str, threshold: int | None = None) -> tuple[str, int]:
    """Map a job title to a SOC code using fuzzy matching.

    Args:
        title: The job title to map.
        threshold: Minimum fuzzy match score (0-100). Uses config default if None.

    Returns:
        Tuple of (soc_code, confidence_score). Returns ("", 0) if no match found.
    """
    if threshold is None:
        threshold = settings.fuzzy_match_threshold

    # Try exact match first (case-insensitive)
    title_clean = title.strip()
    for known_title, soc in TITLE_TO_SOC.items():
        if title_clean.lower() == known_title.lower():
            logger.debug("exact_soc_match", title=title_clean, soc=soc)
            return soc, 100

    # Fuzzy match
    result = process.extractOne(
        title_clean,
        TITLE_TO_SOC.keys(),
        scorer=fuzz.token_sort_ratio,
    )

    if result is None:
        logger.warning("no_soc_match", title=title_clean)
        return "", 0

    matched_title, score, *_ = result
    if score >= threshold:
        soc = TITLE_TO_SOC[matched_title]
        logger.debug("fuzzy_soc_match", title=title_clean, matched=matched_title, score=score)
        return soc, score

    logger.warning(
        "low_confidence_soc_match",
        title=title_clean,
        best_match=matched_title,
        score=score,
    )
    return "", score


def map_roles(roles: list[Role]) -> list[Role]:
    """Map SOC codes for all roles that don't already have one.

    Args:
        roles: List of Role objects. Roles with existing soc_code are unchanged.

    Returns:
        List of Role objects with soc_code populated where possible.
    """
    mapped: list[Role] = []
    unmapped_count = 0

    for role in roles:
        if role.soc_code:
            mapped.append(role)
            continue

        soc_code, confidence = map_title_to_soc(role.title)
        if soc_code:
            updated = role.model_copy(update={"soc_code": soc_code})
            mapped.append(updated)
        else:
            unmapped_count += 1
            mapped.append(role)

    if unmapped_count > 0:
        logger.warning("unmapped_roles", count=unmapped_count)

    return mapped
