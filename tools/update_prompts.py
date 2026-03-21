"""
Restructured prompts using prompt-engineering framework.
Rules applied:
- Exact subject count always (one, two, three)
- Explicit gaze direction
- Explicit hand positions
- Shot type specified
- No ambiguous social proximity
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.database import SessionLocal
from app.models import Prompt

UPDATED_PROMPTS = {
    1: (
        "One female dentist in white coat seated on a stool beside a dental chair, "
        "smiling and speaking to one male patient sitting upright in the chair, "
        "dentist looking at patient, patient face turned toward dentist, "
        "dentist hands resting on her knees, patient hands resting in his lap, "
        "wide shot showing full dental operatory with overhead dental lamp visible above, "
        "large window with soft natural daylight on the left, white walls, "
        "potted plant in far background, generous environmental context, "
        "documentary dental photography"
    ),
    2: (
        "Three healthcare professionals in scrubs standing side by side in a bright hospital corridor, "
        "two women and one man, all three looking down at a tablet screen held flat by the center person, "
        "focused engaged expressions, each person standing independently with hands at sides "
        "except the one holding the tablet, no physical contact between subjects, "
        "medium wide shot showing full bodies and corridor depth receding behind them, "
        "natural window light from the right side, documentary healthcare photography"
    ),
    3: (
        "One female doctor in white coat seated across a wooden desk from one elderly male patient, "
        "doctor leaning slightly forward with both hands clasped together resting on the desk surface, "
        "patient sitting upright with both hands resting in his lap, "
        "both subjects looking at each other across the desk, "
        "warm afternoon light from a window on the left casting soft shadows, "
        "clean minimal office with framed diplomas on wall behind doctor, "
        "wide shot showing both seated figures and the full desk between them, "
        "editorial documentary healthcare photography"
    ),
    6: (
        "One female receptionist with a warm smile seated behind a clean modern reception desk, "
        "looking up from a computer monitor toward the camera with a welcoming expression, "
        "both hands resting visibly on the desk surface in front of her, "
        "contemporary medical reception lobby visible behind her with warm wood tones, "
        "white walls, indoor plants, natural light from skylights overhead, "
        "wide establishing shot showing full desk and lobby interior, "
        "architectural interior photography"
    ),
    7: (
        "Close-up portrait of one young woman in her late 20s with a natural bright genuine smile "
        "showing healthy white teeth, looking directly into the camera lens, "
        "soft diffused studio lighting from the left side, clean white background, "
        "shallow depth of field with sharp focus on face, warm natural skin tones, "
        "no heavy makeup, editorial beauty portrait photography"
    ),
    11: (
        "One professional female real estate agent in a smart casual blazer extending her right hand "
        "in a firm handshake toward one young couple standing together on a home front porch, "
        "husband and wife standing side by side, all three subjects smiling genuinely, "
        "agent looking at the couple, couple looking at the agent, "
        "wide shot showing all three full bodies and modern house exterior facade behind them "
        "with a landscaped front garden, shallow depth of field on the handshake, "
        "editorial lifestyle real estate photography"
    ),
    19: (
        "One male chef in white coat and black apron standing alone at a stainless steel kitchen pass, "
        "using both hands to carefully place a microgreens garnish onto a beautifully plated dish, "
        "eyes looking down focused intently on the plate, "
        "dramatic overhead kitchen lighting, professional open kitchen environment in background "
        "with stainless surfaces and shelves in soft focus, "
        "medium shot from the side showing chef from waist up, "
        "documentary culinary photography"
    ),
    21: (
        "Barista forearms and hands visible filling the frame, left hand steadying a ceramic white mug "
        "on a wooden counter, right hand holding a small metal pouring jug tilted to pour a latte art pattern, "
        "steam rising gently from the mug, shallow depth of field with sharp focus on mug and hands, "
        "warm amber coffee shop ambient light creating soft bokeh in background, "
        "overhead angle looking slightly down at the mug, close-up editorial coffee photography"
    ),
    23: (
        "Four friends seated around a restaurant dining table sharing a meal, "
        "two men and two women in their 30s, all engaged in natural conversation with each other, "
        "two people reaching toward shared plates in the center of the table, "
        "two people holding wine glasses, everyone looking at each other not at the camera, "
        "warm pendant lights overhead creating golden bokeh in background, "
        "medium wide shot showing all four people and the full table setting, "
        "editorial lifestyle food photography"
    ),
    26: (
        "One male lawyer in a navy suit seated at a glass boardroom table, "
        "facing one female client in business attire seated across from him, "
        "both leaning slightly forward in engaged conversation, "
        "lawyer looking directly at client, client looking directly at lawyer, "
        "lawyer both hands resting on the table holding a pen, "
        "client both hands on the table with a notepad in front of her, "
        "city skyline visible through floor-to-ceiling windows behind them, "
        "wide shot showing both figures and the full boardroom table between them, "
        "editorial corporate photography"
    ),
    27: (
        "Three business professionals standing confidently in a modern glass office lobby, "
        "one Black woman in a grey blazer, one Asian man in a navy suit, one white woman in a burgundy blazer, "
        "all three standing independently with one arm of space between each person, "
        "all three looking at the camera with composed professional expressions, "
        "arms at sides or one hand in pocket, "
        "wide shot showing all three full figures and glass lobby architecture behind them, "
        "editorial corporate photography"
    ),
    29: (
        "Close-up of two right hands mid-handshake directly over a polished boardroom table, "
        "one person wearing a dark charcoal suit sleeve, the other wearing a light grey suit sleeve, "
        "warm natural light from the left side creating depth and shadow, "
        "signed documents visible slightly blurred at the table edge in lower foreground, "
        "shallow depth of field with sharp focus on the clasped hands, "
        "both persons visible from the chest down as soft background context, "
        "editorial corporate trust photography"
    ),
    31: (
        "One male attorney in his 40s wearing reading glasses seated at a tidy desk, "
        "leaning forward with both hands holding a printed document up to read it, "
        "eyes looking down reading the text on the page, "
        "afternoon warm light from a window on his right side casting soft directional shadows, "
        "bookshelves with legal folders visible in soft focus background, "
        "medium shot from the side showing attorney from waist up at desk, "
        "documentary editorial photography"
    ),
    33: (
        "One athletic man in his 30s in workout clothes performing a barbell deadlift in a modern gym, "
        "bent forward with both hands gripping the barbell, "
        "intense focused expression looking straight down toward the bar, "
        "dramatic natural light streaming from large industrial windows on the right side, "
        "wide shot showing full body from head to feet and gym environment in background, "
        "other equipment visible in soft focus behind him, "
        "documentary fitness photography"
    ),
    34: (
        "One young woman in her late 20s running along an urban park path, "
        "wearing athletic leggings and a fitted top, left foot forward mid-stride, "
        "arms bent and pumping at her sides, determined expression looking forward down the path ahead, "
        "motion blur on legs showing speed, "
        "golden hour sunlight from behind creating a warm rim light around her, "
        "wide shot showing park path and green trees receding into background bokeh, "
        "editorial lifestyle fitness photography"
    ),
    36: (
        "One male personal trainer standing beside one female client who is performing "
        "a dumbbell shoulder press exercise, trainer standing one step to her side, "
        "one hand lightly on her upper arm guiding her form, "
        "trainer looking at her movement with a focused coaching expression, "
        "client looking straight ahead with determined concentration, "
        "both subjects fully visible from head to toe, "
        "bright modern gym environment with natural daylight from windows behind them, "
        "wide shot showing gym background with equipment visible, "
        "documentary fitness photography"
    ),
    38: (
        "Twelve people performing synchronized jumping jacks in a bright fitness studio, "
        "diverse mix of ages and body types, all arms raised overhead at the same moment, "
        "genuine effort and energy on faces, "
        "overhead wide angle shot from above showing the full group in three rows of four, "
        "studio lighting from above, large windows along one wall letting in natural light, "
        "no one looking at the camera, all focused on the exercise, "
        "editorial documentary fitness photography"
    ),
    40: (
        "One confident woman in her 40s wearing athletic leggings and a fitted top, "
        "standing tall facing floor-to-ceiling windows in a modern apartment, "
        "both arms relaxed at her sides, looking out at an urban skyline, "
        "her face visible in partial profile showing a calm hopeful expression, "
        "warm golden morning light flooding in through the windows, "
        "wide shot showing her full figure from head to toe and the large window with city view behind her, "
        "documentary lifestyle photography"
    ),
    42: (
        "One young woman in her mid-20s in a neutral beige linen outfit standing beside a clothing rack "
        "in a minimal boutique store, one hand lightly touching a garment as she browses, "
        "other hand resting at her side, looking at the clothing in front of her with a relaxed expression, "
        "warm natural light from street-facing windows on her left side, "
        "wide shot showing her full figure from head to toe and store interior with clothing racks behind her, "
        "candid editorial lifestyle photography"
    ),
    43: (
        "Two hands carefully gripping the sides of a premium matte black rigid gift box lid "
        "and lifting it open on a clean white marble surface, "
        "fingers spread naturally on the lid edges, "
        "white tissue paper visible inside wrapping the contents, "
        "soft warm studio lighting from the upper left, "
        "overhead shot looking slightly down showing both hands and the open box, "
        "shallow depth of field with sharp focus on the box and hands, "
        "luxury unboxing product photography"
    ),
    45: (
        "One young woman in her late 20s in casual stylish clothes walking on a sunny city sidewalk, "
        "holding a paper shopping bag with both hands in front of her, "
        "looking ahead with a genuine natural smile, not looking at the camera, "
        "urban street with storefronts and trees in soft background bokeh, "
        "wide medium shot showing her full figure from head to toe on the sidewalk, "
        "warm afternoon sunlight from the right side, "
        "editorial lifestyle photography"
    ),
    47: (
        "One artisan maker in their 40s seated at a wooden workshop bench, "
        "both hands actively shaping a small clay ceramic bowl on a hand wheel, "
        "eyes looking down focused on the clay form, "
        "fingers pressed naturally into the wet clay in a forming gesture, "
        "warm directional light from a window on the left casting soft shadows on the clay, "
        "pottery tools and raw clay visible on the bench surface beside the wheel, "
        "medium close-up shot from the side showing hands and clay wheel in sharp focus, "
        "documentary artisan photography"
    ),
}

def run():
    db = SessionLocal()
    updated = 0
    for pid, new_text in UPDATED_PROMPTS.items():
        p = db.get(Prompt, pid)
        if p:
            p.prompt_text = new_text
            print(f"  Updated ID {pid}: {p.name}")
            updated += 1
        else:
            print(f"  WARNING: Prompt ID {pid} not found")
    db.commit()
    db.close()
    print(f"\nDone — {updated} prompts updated.")

if __name__ == "__main__":
    run()
