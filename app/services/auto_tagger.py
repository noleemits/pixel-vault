"""
app/services/auto_tagger.py — Predefined tags and auto-tagging logic.

Tags are organized by category. Auto-tagging scans the prompt text
and assigns matching tags on image creation.
"""

from __future__ import annotations
from sqlalchemy.orm import Session
from app.models import Tag, Image

# ---------------------------------------------------------------------------
# Predefined tags by category
# ---------------------------------------------------------------------------

PREDEFINED_TAGS: dict[str, list[str]] = {
    "industry": [
        "healthcare", "real_estate", "food", "legal_finance", "fitness", "ecommerce",
        "pet_care", "beauty", "education", "home_services", "automotive", "technology",
    ],
    "scene": [
        "office", "clinic", "gym", "restaurant", "kitchen", "outdoor",
        "studio", "home", "warehouse", "storefront", "courtroom", "salon",
    ],
    "subject": [
        "people", "team", "consultation", "product", "equipment",
        "abstract", "portrait", "hands", "interior", "exterior",
    ],
    "mood": [
        "warm", "clinical", "energetic", "luxury", "minimal", "bold",
        "calm", "professional", "cozy", "modern",
    ],
    "use_case": [
        "hero", "blog", "testimonial", "about", "service", "team-page",
        "gallery", "product-page", "landing",
    ],
}

# Flattened lookup: tag_name -> category
TAG_CATEGORY: dict[str, str] = {}
for cat, names in PREDEFINED_TAGS.items():
    for name in names:
        TAG_CATEGORY[name] = cat

# Keyword map: words that appear in prompts -> tag names they should trigger
# Extend as needed.
KEYWORD_MAP: dict[str, list[str]] = {
    # Scene keywords
    "office":      ["office"],
    "lobby":       ["office"],
    "desk":        ["office"],
    "workspace":   ["office"],
    "clinic":      ["clinic", "healthcare"],
    "hospital":    ["clinic", "healthcare"],
    "medical":     ["clinic", "healthcare"],
    "dental":      ["clinic", "healthcare"],
    "gym":         ["gym", "fitness"],
    "workout":     ["gym", "fitness", "energetic"],
    "yoga":        ["gym", "fitness", "calm"],
    "pilates":     ["gym", "fitness"],
    "restaurant":  ["restaurant", "food"],
    "dining":      ["restaurant", "food"],
    "cafe":        ["restaurant", "food"],
    "kitchen":     ["kitchen", "food"],
    "cooking":     ["kitchen", "food"],
    "vegetable":   ["food", "kitchen"],
    "rustic":      ["warm", "food"],
    "ingredient":  ["food", "kitchen"],
    "outdoor":     ["outdoor"],
    "garden":      ["outdoor"],
    "park":        ["outdoor"],
    "nature":      ["outdoor"],
    "studio":      ["studio"],
    "home":        ["home"],
    "living room": ["home"],
    "bedroom":     ["home"],
    "bathroom":    ["home"],
    "warehouse":   ["warehouse"],
    "storefront":  ["storefront", "ecommerce"],
    "shop":        ["storefront", "ecommerce"],
    "courtroom":   ["courtroom", "legal_finance"],
    "salon":       ["salon"],
    "spa":         ["salon", "calm", "luxury"],

    # Subject keywords
    "people":      ["people"],
    "person":      ["people"],
    "woman":       ["people"],
    "man":         ["people"],
    "patient":     ["people", "healthcare"],
    "doctor":      ["people", "healthcare", "consultation"],
    "nurse":       ["people", "healthcare"],
    "therapist":   ["people", "consultation"],
    "trainer":     ["people", "fitness"],
    "chef":        ["people", "food"],
    "team":        ["team", "people"],
    "group":       ["team", "people"],
    "staff":       ["team", "people"],
    "consultation":["consultation"],
    "meeting":     ["consultation", "office"],
    "product":     ["product"],
    "equipment":   ["equipment"],
    "tools":       ["equipment"],
    "machine":     ["equipment"],
    "abstract":    ["abstract"],
    "pattern":     ["abstract"],
    "texture":     ["abstract"],
    "portrait":    ["portrait", "people"],
    "headshot":    ["portrait", "people"],
    "hands":       ["hands", "people"],
    "interior":    ["interior"],
    "exterior":    ["exterior"],
    "building":    ["exterior"],
    "facade":      ["exterior"],

    # Mood keywords
    "warm":        ["warm"],
    "cozy":        ["warm", "cozy"],
    "clinical":    ["clinical"],
    "sterile":     ["clinical"],
    "clean":       ["clinical", "minimal"],
    "energetic":   ["energetic"],
    "dynamic":     ["energetic"],
    "action":      ["energetic"],
    "luxury":      ["luxury"],
    "elegant":     ["luxury"],
    "premium":     ["luxury"],
    "upscale":     ["luxury"],
    "minimal":     ["minimal"],
    "minimalist":  ["minimal"],
    "simple":      ["minimal"],
    "bold":        ["bold"],
    "vibrant":     ["bold"],
    "striking":    ["bold"],
    "calm":        ["calm"],
    "serene":      ["calm"],
    "peaceful":    ["calm"],
    "professional":["professional"],
    "corporate":   ["professional", "office"],
    "modern":      ["modern"],
    "contemporary":["modern"],

    # Industry keywords
    "real estate": ["real_estate"],
    "property":    ["real_estate"],
    "house":       ["real_estate", "home", "exterior"],
    "apartment":   ["real_estate", "home", "interior"],
    "legal":       ["legal_finance"],
    "law":         ["legal_finance"],
    "attorney":    ["legal_finance"],
    "lawyer":      ["legal_finance", "people"],
    "finance":     ["legal_finance"],
    "banking":     ["legal_finance"],
    "accounting":  ["legal_finance"],
    "ecommerce":   ["ecommerce"],
    "e-commerce":  ["ecommerce"],
    "online shop": ["ecommerce"],
    "health":      ["healthcare"],
    "wellness":    ["healthcare", "fitness"],
    "fitness":     ["fitness"],
    "exercise":    ["fitness", "energetic"],
    "strength":    ["fitness", "energetic"],
    "flexibility": ["fitness", "calm"],
    "food":        ["food"],
    "meal":        ["food"],
    "dish":        ["food"],
    "recipe":      ["food"],

    # Pet care
    "dog":         ["pet_care", "people"],
    "cat":         ["pet_care"],
    "pet":         ["pet_care"],
    "puppy":       ["pet_care"],
    "kitten":      ["pet_care"],
    "veterinary":  ["pet_care", "healthcare"],
    "vet":         ["pet_care", "healthcare"],
    "grooming":    ["pet_care"],
    "groomer":     ["pet_care", "people"],
    "kennel":      ["pet_care"],

    # Beauty
    "beauty":      ["beauty"],
    "hair":        ["beauty", "salon"],
    "nail":        ["beauty", "salon"],
    "skincare":    ["beauty"],
    "makeup":      ["beauty"],
    "cosmetic":    ["beauty"],
    "facial":      ["beauty", "salon"],
    "barber":      ["beauty", "salon", "people"],
    "stylist":     ["beauty", "salon", "people"],
    "manicure":    ["beauty", "salon"],

    # Education
    "school":      ["education"],
    "university":  ["education"],
    "student":     ["education", "people"],
    "teacher":     ["education", "people"],
    "classroom":   ["education", "interior"],
    "tutor":       ["education", "people"],
    "learning":    ["education"],
    "academy":     ["education"],
    "course":      ["education"],

    # Home services
    "plumber":     ["home_services", "people"],
    "plumbing":    ["home_services"],
    "electrician": ["home_services", "people"],
    "hvac":        ["home_services"],
    "roofing":     ["home_services", "exterior"],
    "contractor":  ["home_services", "people"],
    "handyman":    ["home_services", "people"],
    "landscaping": ["home_services", "outdoor"],
    "cleaning":    ["home_services"],
    "renovation":  ["home_services", "interior"],

    # Automotive
    "car":         ["automotive"],
    "vehicle":     ["automotive"],
    "mechanic":    ["automotive", "people"],
    "dealership":  ["automotive"],
    "garage":      ["automotive"],
    "tire":        ["automotive"],
    "automotive":  ["automotive"],

    # Technology
    "software":    ["technology"],
    "tech":        ["technology"],
    "startup":     ["technology", "modern"],
    "app":         ["technology"],
    "developer":   ["technology", "people"],
    "server":      ["technology"],
    "cloud":       ["technology"],
    "coding":      ["technology"],
}


def seed_tags(db: Session) -> int:
    """Ensure all predefined tags exist in the database. Returns count of new tags created."""
    created = 0
    for category, names in PREDEFINED_TAGS.items():
        for name in names:
            existing = db.query(Tag).filter(Tag.name == name).first()
            if existing:
                if existing.category != category:
                    existing.category = category
            else:
                db.add(Tag(name=name, category=category))
                db.flush()
                created += 1
    db.commit()
    return created


def auto_tag_image(db: Session, image: Image, prompt_text: str, industry: str | None = None) -> list[str]:
    """
    Scan prompt text and assign matching tags to an image.
    Returns list of tag names that were assigned.
    """
    prompt_lower = prompt_text.lower()
    matched_tag_names: set[str] = set()

    # 1. Always add the industry tag if it's a known one.
    if industry and industry in TAG_CATEGORY:
        matched_tag_names.add(industry)

    # 2. Scan prompt for keyword matches.
    for keyword, tag_names in KEYWORD_MAP.items():
        if keyword in prompt_lower:
            matched_tag_names.update(tag_names)

    # 3. Direct match against tag names themselves.
    for tag_name in TAG_CATEGORY:
        if tag_name.replace("_", " ") in prompt_lower or tag_name in prompt_lower:
            matched_tag_names.add(tag_name)

    # 4. Assign tags to image.
    assigned = []
    for tag_name in matched_tag_names:
        tag = db.query(Tag).filter(Tag.name == tag_name).first()
        if not tag:
            tag = Tag(name=tag_name, category=TAG_CATEGORY.get(tag_name))
            db.add(tag)
            db.flush()
        if tag not in image.tags:
            image.tags.append(tag)
            assigned.append(tag_name)

    return assigned
