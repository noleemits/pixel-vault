from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from app.models import Base, Image, Prompt, Batch, Tag

def test_create_tables():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    table_names = Base.metadata.tables.keys()
    assert "images" in table_names
    assert "prompts" in table_names
    assert "batches" in table_names
    assert "tags" in table_names

def test_create_prompt_and_image():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        prompt = Prompt(
            industry="healthcare",
            name="Modern Dental Clinic — Hero",
            prompt_text="Bright modern dental clinic interior...",
            use_case="Homepage hero, about page banner",
            ratios="16:9,4:3",
            kontext_variations="Change season lighting / swap to female dentist",
        )
        session.add(prompt)
        session.flush()

        batch = Batch(status="completed", prompt_id=prompt.id, image_count=4)
        session.add(batch)
        session.flush()

        image = Image(
            filename="healthcare-hero-01-16x9.jpg",
            filepath="storage/images/healthcare-hero-01-16x9.jpg",
            industry="healthcare",
            style="hero",
            ratio="16:9",
            prompt_id=prompt.id,
            batch_id=batch.id,
            status="approved",
            quality_score=8,
        )
        session.add(image)
        session.commit()

        assert image.id is not None
        assert image.prompt.name == "Modern Dental Clinic — Hero"
        assert batch.images[0].filename == "healthcare-hero-01-16x9.jpg"
