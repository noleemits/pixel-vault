# app/seed/master_prompts.py
"""48 master prompts from PixelVault_ImageBankPlan.docx."""

MASTER_PROMPTS = [
    # --- Healthcare & Dental (8) ---
    ("healthcare", "Modern Dental Clinic — Hero",
     "Bright modern dental clinic interior, friendly dentist in white coat speaking with a relaxed patient seated in a dental chair, large windows with soft natural daylight, clean white and teal color palette, potted plant in background, shallow depth of field, professional editorial photography, cinematic lighting, 16:9 web hero image",
     "Homepage hero, about page banner", "16:9,4:3",
     "Change season lighting / swap to female dentist / add child patient"),

    ("healthcare", "Medical Team Collaboration",
     "Three diverse healthcare professionals in scrubs reviewing a digital tablet together in a bright hospital corridor, warm neutral tones, candid documentary style, natural window light, no harsh shadows, soft bokeh background, modern hospital setting, editorial photography",
     "Team section, about us, careers", "16:9,1:1",
     "Change to 2-person / outdoor courtyard / conference room"),

    ("healthcare", "Patient Consultation — Trust",
     "Warm one-on-one consultation between a caring female doctor and an elderly male patient in a clean modern office, doctor leaning slightly forward showing empathy, indirect warm lighting, muted blue and white tones, photorealistic, shallow depth of field, editorial healthcare photography",
     "Services page, testimonials section", "4:3,4:5",
     "Younger patient / pediatric setting / phone consultation"),

    ("healthcare", "Clean Equipment — Abstract",
     "Close-up abstract composition of polished modern dental or medical equipment, soft focus, cool blue-gray tones, studio product photography style, ultra clean background, subtle reflections, professional and reassuring, minimalist aesthetic",
     "Background texture, section divider", "16:9,1:1",
     "Warm tones / surgical instruments / lab setting"),

    ("healthcare", "Wellness & Prevention",
     "Young healthy woman doing yoga meditation at sunrise on a wooden deck surrounded by greenery, golden hour warm light, peaceful expression, soft bokeh, lifestyle editorial photography, wellness and preventive health theme, clean composition",
     "Wellness services, preventive care sections", "16:9,4:5",
     "Male subject / indoor yoga / senior wellness"),

    ("healthcare", "Reception & First Impressions",
     "Welcoming dental or medical reception area with a smiling receptionist at a modern desk, contemporary interior design, warm white and wood tones, plants, natural light from skylights, inviting atmosphere, real estate photography style, sharp focus",
     "Contact page, location section", "16:9,4:3",
     "Evening lighting / busy waiting room / pediatric waiting area"),

    ("healthcare", "Healthy Smile — Outcome",
     "Close-up portrait of a confident young woman with a genuine bright smile, soft studio lighting, clean white background, shallow depth of field on face, warm skin tones, professional beauty editorial style, dental health aspirational theme",
     "Results section, testimonials, social proof", "1:1,4:5",
     "Male subject / older demographic / diverse ethnicities"),

    ("healthcare", "Lab & Research",
     "Medical laboratory technician examining samples under a microscope in a clean modern lab, blue and white color palette, technical precision, shallow depth of field, documentary science photography, professional clinical environment, subtle lens flare",
     "Technology section, credentials, research", "16:9,4:3",
     "Female technician / different equipment / data on screens"),

    # --- Real Estate (8) ---
    ("real_estate", "Modern Living Room — Hero",
     "Bright spacious modern living room with floor-to-ceiling windows, late afternoon golden sunlight streaming in, minimal Scandinavian furniture in warm neutrals, indoor plants, hardwood floors, no people, architectural interior photography, ultra sharp, wide angle",
     "Homepage hero, listing header", "16:9,4:3",
     "Night mood lighting / urban apartment style / coastal aesthetic"),

    ("real_estate", "Luxury Kitchen",
     "High-end open-plan kitchen with white marble countertops, pendant lights, stainless steel appliances, bowl of fresh fruit, natural light from a large window, architectural photography style, no people, ultra clean, warm tones",
     "Property features section", "16:9,4:3",
     "Dark moody tones / rustic wood / breakfast scene with person"),

    ("real_estate", "Agent Meeting — Trust",
     "Professional real estate agent shaking hands with a young couple in front of a modern home exterior, sunny day, genuine smiles, well-dressed casual attire, shallow depth of field on handshake, editorial lifestyle photography, aspirational and trustworthy",
     "About page, agent profile, testimonials", "16:9,4:5",
     "Document signing at table / outdoor coffee meeting / single buyer"),

    ("real_estate", "Aerial — Neighborhood",
     "Aerial drone photography of a clean suburban neighborhood with tree-lined streets, well-maintained homes with varied architecture, green lawns, blue sky with few clouds, golden hour light, wide establishing shot, no text or watermarks",
     "Location section, neighborhood guide", "16:9,21:9",
     "Urban cityscape / coastal suburb / rural acreage"),

    ("real_estate", "Bedroom — Lifestyle",
     "Serene master bedroom with white linen bedding, wood-framed windows with sheer curtains, morning light filtering in, potted plant on nightstand, minimalist decor, real estate photography, no people, aspirational lifestyle feel",
     "Property gallery, blog", "16:9,4:3",
     "Cozy dark palette / kids bedroom / master with en-suite view"),

    ("real_estate", "Outdoor Living Space",
     "Modern outdoor patio with teak furniture, string lights, lush garden backdrop, sunset warm tones, lifestyle editorial photography, relaxed entertaining atmosphere, shallow depth of field on foreground table with drinks, no people",
     "Outdoor features, lifestyle section", "16:9,4:3",
     "Pool area / urban rooftop / winter firepit"),

    ("real_estate", "For Sale — Curb Appeal",
     "Beautiful family home exterior with manicured front lawn, flowers in bloom, blue sky, warm sunlight, freshly painted facade, welcoming front door, no for sale sign, architectural photography, eye-level perspective, symmetrical composition",
     "Listings, featured properties", "4:3,16:9",
     "Night exterior / autumn foliage / contemporary minimalist style"),

    ("real_estate", "Home Office",
     "Bright ergonomic home office with a clean white desk, large monitor, bookshelves, natural daylight from a side window, indoor plants, minimal distractions, editorial lifestyle photography, productivity and work-from-home theme",
     "Property features, remote work appeal", "16:9,4:3",
     "Cozy library style / creative studio / corner nook"),

    # --- Restaurant & Food (8) ---
    ("food", "Hero Dish — Fine Dining",
     "Elegant plated gourmet dish on a dark slate plate, soft dramatic side lighting, shallow depth of field, garnished with microgreens and a sauce reduction, dark moody restaurant background slightly out of focus, professional food photography, ultra detailed textures, appetizing colors",
     "Menu hero, homepage feature", "1:1,4:3",
     "Change dish type / bright editorial style / rustic wooden table"),

    ("food", "Restaurant Ambiance — Dinner",
     "Warm inviting restaurant interior at dinner service, soft candlelight and warm pendant lights, blurred happy diners in background, beautifully set table in foreground with wine glasses and folded napkins, bokeh, shallow depth of field, editorial food lifestyle photography",
     "Homepage hero, about page", "16:9,4:3",
     "Lunch service / outdoor terrace / bar seating"),

    ("food", "Chef in Action",
     "Confident chef in white coat plating a dish in a professional stainless steel kitchen, motion blur on hands showing skill and speed, dramatic overhead lighting, documentary style photography, warm ambient kitchen tones, authentic culinary atmosphere",
     "About us, team, story section", "16:9,4:5",
     "Female chef / pastry section / open kitchen with customer view"),

    ("food", "Casual Brunch — Lifestyle",
     "Overhead flat lay of a Sunday brunch table with pancakes, fresh berries, orange juice, coffee, scattered flowers, warm natural light from a window, lifestyle editorial photography, linen napkins, clean white marble surface, inviting and relaxed",
     "Brunch menu, social, catering", "1:1,4:3",
     "Healthy bowls / cocktails / hands reaching for food"),

    ("food", "Artisan Coffee",
     "Barista's hands pouring latte art into a ceramic mug on a wooden counter, steam rising, warm coffee shop ambiance in background, shallow depth of field on mug, editorial coffee photography, natural morning light, close-up macro style",
     "Coffee section, breakfast menu", "1:1,4:5",
     "Cold brew setup / full cafe scene / to-go cup outdoor"),

    ("food", "Fresh Ingredients",
     "Rustic wooden table with an artful arrangement of fresh colorful vegetables, herbs, and seasonal produce, natural soft daylight, slight shadows, editorial food photography, farm-to-table theme, no processed foods, organic and wholesome aesthetic",
     "Philosophy section, farm-to-table claims", "16:9,1:1",
     "Seafood / meat charcuterie / pastry and baked goods"),

    ("food", "Group Dining — Social",
     "Four friends laughing and sharing food at a restaurant table, natural candid moment, warm bokeh lights in background, genuine emotion, diverse group, editorial lifestyle photography, celebration atmosphere, wine and shared plates on table",
     "Social proof, events, group bookings", "16:9,4:3",
     "Family dinner / romantic date / business lunch"),

    ("food", "Takeaway — Modern Fast Casual",
     "Stylish kraft paper takeaway bag with a logo area, next to a stacked burger and crispy fries on a clean white surface, bright natural light, product photography style, modern fast casual aesthetic, minimal props, sharp focus",
     "Takeaway section, delivery feature", "1:1,4:3",
     "Pizza box / sushi takeout / healthy bowl packaging"),

    # --- Professional Services: Law & Finance (8) ---
    ("legal_finance", "Modern Law Office Interior",
     "Sleek contemporary law office with floor-to-ceiling windows overlooking a city skyline, dark wood paneling, leather chairs, a clean glass desk with a laptop, warm diffused light, no people, architectural interior photography, authoritative and modern",
     "Homepage hero, about us", "16:9,4:3",
     "Evening city lights / traditional library style / meeting room"),

    ("legal_finance", "Client Consultation — Confidence",
     "Professional lawyer or financial advisor in a navy suit having a confident focused conversation with a client across a glass table, executive office setting, city view in background, editorial business photography, warm window light, eye contact and engagement",
     "Services, consultation section", "16:9,4:5",
     "Female attorney / virtual call / signing documents"),

    ("legal_finance", "Team — Diversity & Authority",
     "Three business professionals of different backgrounds standing confidently in a modern glass office building lobby, business formal attire, genuine expressions, editorial corporate photography, warm neutral tones, shallow depth of field",
     "Team page, about us", "16:9,4:3",
     "Outdoor city backdrop / conference room / headshot style"),

    ("legal_finance", "Data & Strategy",
     "Business professional reviewing financial charts and data on a large curved monitor in a dark modern office, dramatic side lighting, data visualizations on screen, focused intense expression, cinematic editorial style, blue and white screen glow",
     "Technology, data analytics service section", "16:9,4:3",
     "Multiple monitors / tablet on boardroom table / team reviewing"),

    ("legal_finance", "Handshake — Partnership",
     "Close-up of two professionals shaking hands across a boardroom table, shallow depth of field on hands, business formal attire, warm natural light from windows, signed documents visible on table edge, editorial corporate photography, trust and partnership theme",
     "About us, partnerships, results", "4:3,1:1",
     "Contract signing / key handover / digital agreement on tablet"),

    ("legal_finance", "City Architecture — Prestige",
     "Modern glass office tower reflecting blue sky and clouds, street level view looking upward, wide angle architectural photography, clean lines and geometric shapes, no text or signs, corporate prestige theme, sharp focus across entire frame",
     "Background image, location, credibility", "4:5,9:16",
     "Interior atrium / courthouse exterior / financial district skyline"),

    ("legal_finance", "Research & Precision",
     "Attorney or analyst in reading glasses carefully reviewing printed documents at a tidy desk, afternoon warm light from window, selective focus on documents, deliberate and meticulous atmosphere, editorial documentary style, books and folders in background",
     "Expertise section, process description", "4:3,4:5",
     "Digital document review / legal library / annotating contract"),

    ("legal_finance", "Growth — Finance Concept",
     "Abstract close-up of a physical wooden desk with a small green plant growing from a handful of coins, selective focus, soft warm studio lighting, financial growth metaphor, minimal conceptual photography, clean white background, hopeful and forward-looking",
     "Investment services, wealth management", "1:1,4:3",
     "Graph on paper / seeds in soil / stairs ascending"),

    # --- Fitness & Wellness (8) ---
    ("fitness", "Gym Training — Hero",
     "Athletic person in workout clothes performing a determined weightlifting exercise in a modern gym, natural daylight from large industrial windows, dramatic side lighting, motion blur on movement, editorial fitness photography, cinematic crop, genuine effort not posed",
     "Homepage hero, services", "16:9,4:5",
     "Female athlete / cardio training / group class"),

    ("fitness", "Outdoor Running — Lifestyle",
     "Young woman running along an urban park path at golden hour, motion blur on legs showing speed, determined expression, city trees in background bokeh, editorial lifestyle photography, aspirational fitness, warm morning tones, loose active wear",
     "Running programs, outdoor fitness", "16:9,4:5",
     "Male runner / trail running / beach running at sunrise"),

    ("fitness", "Yoga & Mindfulness",
     "Woman in warrior yoga pose on a wooden studio floor, large windows with soft morning light, minimal white and wood interior, calm focused expression, editorial wellness photography, clean lines, no clutter, serene and intentional atmosphere",
     "Yoga, mindfulness, mind-body programs", "4:5,1:1",
     "Outdoor rooftop / beach setting / group class / meditation pose"),

    ("fitness", "Personal Training — Connection",
     "Personal trainer giving encouragement to a client mid-exercise in a bright modern gym, trainer showing proper form with a hand on shoulder, both genuinely focused, documentary fitness photography, warm natural light, no cheesy poses",
     "Personal training services, coaching", "16:9,4:3",
     "Female trainer / outdoor training session / senior client"),

    ("fitness", "Healthy Nutrition",
     "Top-down flat lay of a balanced healthy meal prep on a clean white marble surface, colorful vegetables, grilled protein, quinoa, fruit on the side, morning natural light, editorial food and wellness photography, no processed foods, vibrant colors",
     "Nutrition section, meal planning services", "1:1,4:3",
     "Smoothie bowls / supplement setup / grocery haul"),

    ("fitness", "Community — Group Class",
     "Energetic group fitness class doing synchronized exercises in a bright studio, diverse participants of varying fitness levels, genuine smiles and effort, overhead or side angle, editorial documentary style, natural light and studio lighting mix",
     "Group classes, community, memberships", "16:9,4:3",
     "Spin class / bootcamp outdoor / dance fitness"),

    ("fitness", "Recovery & Wellness",
     "Person in a peaceful recovery pose in a spa-like wellness room, warm candle and ambient lighting, white towels and natural materials, serene expression, editorial spa photography, post-workout recovery theme, minimal and calming aesthetic",
     "Recovery services, spa, premium tiers", "4:3,4:5",
     "Ice bath / massage therapy / sauna interior"),

    ("fitness", "Transformation — Before Journey",
     "Confident diverse person standing tall in athletic wear looking out a large window at an urban landscape, contemplative hopeful expression, morning golden light, documentary lifestyle photography, beginning of a fitness journey theme, motivational",
     "Transformation stories, program intro", "4:5,9:16",
     "Celebration finish / looking in mirror / couple starting together"),

    # --- E-commerce & Retail (8) ---
    ("ecommerce", "Lifestyle Product — Hero",
     "Modern reusable water bottle on a marble countertop next to a green plant, soft natural side lighting from a window, clean white background, product photography with lifestyle context, minimal styling, sharp focus on product, editorial and aspirational",
     "Product hero, homepage feature", "1:1,4:5",
     "Change product type / outdoor setting / hands holding product"),

    ("ecommerce", "Fashion Lifestyle",
     "Young stylish woman in a neutral outfit browsing clothing racks in a minimal boutique store, warm natural light from street-facing windows, candid editorial style, blurred clothing in background, authentic shopping experience, no branding visible",
     "Fashion category, shopping experience", "4:5,16:9",
     "Male shopper / online shopping on phone / checkout moment"),

    ("ecommerce", "Unboxing — Premium Feel",
     "Hands carefully opening a premium matte black product box revealing a wrapped item with tissue paper, clean marble surface, soft warm studio lighting, close-up product photography, aspirational unboxing experience, luxury packaging aesthetic",
     "Packaging section, gifting, premium tier", "1:1,4:3",
     "Colorful festive packaging / subscription box / beauty product reveal"),

    ("ecommerce", "Home Products — In Situ",
     "Beautifully styled living room corner with a ceramic vase, coffee table book, and a decorative item on a wooden side table, natural morning light, Scandinavian minimal interior, editorial home decor photography, no people, clean and aspirational",
     "Home decor category, interior lifestyle", "4:3,1:1",
     "Kitchen product placement / bedroom / bathroom shelf"),

    ("ecommerce", "Satisfied Customer",
     "Genuine happy young woman holding a shopping bag and smiling on a sunny city street, casual stylish outfit, candid editorial lifestyle photography, urban background bokeh, authentic not posed, positive retail experience, warm tones",
     "Social proof, testimonials, ad creative", "4:5,1:1",
     "Man with bag / couple shopping / delivery at door"),

    ("ecommerce", "Tech Product — Clean",
     "Minimalist product shot of a sleek wireless earbuds case on a smooth gray surface, dramatic studio side lighting creating shadows and depth, sharp focus, product photography, premium tech aesthetic, no text, advertising quality image",
     "Tech category, product details", "1:1,4:3",
     "Smartwatch / laptop / phone / portable speaker"),

    ("ecommerce", "Small Business — Artisan",
     "Artisan maker's hands crafting a small handmade ceramic item in a cozy workshop, warm workshop lighting, clay and tools visible, shallow depth of field, editorial documentary style, authentic craft and small business theme, earthy warm tones",
     "Artisan brand, about us, process section", "4:3,4:5",
     "Jewelry making / candle pouring / textile weaving"),

    ("ecommerce", "Sale & Urgency",
     "Colorful retail store interior with neatly organized product displays, bright clean lighting, no people, wide angle shot showing store depth, modern organized retail aesthetic, visual merchandising photography, inviting and accessible atmosphere",
     "Sale events, store section, category pages", "16:9,4:3",
     "Seasonal display / food retail / boutique accessories"),
]


def seed_prompts(db_session):
    """Insert all 48 master prompts into the database."""
    from app.models import Prompt
    existing = db_session.query(Prompt).count()
    if existing > 0:
        return existing
    for industry, name, prompt_text, use_case, ratios, kontext in MASTER_PROMPTS:
        db_session.add(Prompt(
            industry=industry,
            name=name,
            prompt_text=prompt_text,
            use_case=use_case,
            ratios=ratios,
            kontext_variations=kontext,
        ))
    db_session.commit()
    return len(MASTER_PROMPTS)
