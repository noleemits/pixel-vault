# LoRA Training Prompts — PixelVault Style Reference

**Goal:** Generate 24 high-quality reference images using Gemini to train a FLUX LoRA.
**Total:** 24 images — 4 per industry
**After generating:** Run through `tools/watermark_remover.py` before LoRA training.

**Copy each prompt exactly into Gemini image generation.**
**Save each image with the filename shown** — it helps keep training organized.

---

## ⚠️ Watch for These
- If Gemini shows Shutterstock results → you've hit the daily limit. Stop and continue tomorrow.
- Reject any image where hands look distorted or eyes look off — regenerate that one.
- Aim for images that feel **observed**, not posed.

---

## 🏥 Healthcare & Dental (4 images)

### HC-01 — Consultation (tests: eye contact + hands)
**Filename:** `hc-01-consultation.jpg`
```
Female doctor in white coat leaning forward attentively toward a male patient in his 40s seated across a clean modern desk, both making natural eye contact mid-conversation, warm natural window light from the left, shallow depth of field, neutral warm color grading, editorial documentary photography, no surgical masks, hands relaxed and visible on desk
```

### HC-02 — Medical Team (tests: group dynamics + hands)
**Filename:** `hc-02-team.jpg`
```
Three diverse healthcare professionals in scrubs standing together in a bright hospital corridor reviewing a tablet, natural candid moment, genuine conversation, all faces clearly visible, warm neutral tones, soft window light, documentary editorial photography, anatomically natural hand positions, no masks
```

### HC-03 — Clinic Environment (tests: color grading + space)
**Filename:** `hc-03-environment.jpg`
```
Modern dental clinic interior, bright and airy, white and light wood tones, dental chair in center frame, large windows with natural daylight, potted plants, no people, architectural interior photography, neutral color grading, ultra clean, warm white ambient light
```

### HC-04 — Confident Portrait (tests: face rendering + detail)
**Filename:** `hc-04-portrait.jpg`
```
Close-up portrait of a female doctor in her 30s in a white coat, warm confident smile, soft studio lighting, neutral background slightly out of focus, shallow depth of field on face, editorial portrait photography, natural skin tones, no harsh shadows
```

---

## 🏠 Real Estate (4 images)

### RE-01 — Agent with Clients (tests: eye contact + hands)
**Filename:** `re-01-agent-clients.jpg`
```
Professional real estate agent shaking hands with a young couple outside a modern home, sunny afternoon, genuine smiles, all three making natural eye contact, well-dressed casual attire, shallow depth of field on handshake, editorial lifestyle photography, warm golden hour light, anatomically correct hands
```

### RE-02 — Living Room Interior (tests: color grading + environment)
**Filename:** `re-02-interior.jpg`
```
Bright spacious modern living room, floor-to-ceiling windows, late afternoon golden sunlight, Scandinavian minimal furniture in warm neutrals, indoor plants, hardwood floors, no people, architectural interior photography, ultra sharp, wide angle, neutral warm color grading
```

### RE-03 — Home Exterior (tests: outdoor light + architecture)
**Filename:** `re-03-exterior.jpg`
```
Beautiful family home exterior with manicured front lawn, flowers in bloom, bright blue sky, warm afternoon sunlight, freshly painted white facade, welcoming front door, no for sale sign, architectural photography, eye-level perspective, neutral color grading
```

### RE-04 — Property Showing (tests: lifestyle + people in space)
**Filename:** `re-04-showing.jpg`
```
Real estate agent showing a bright modern kitchen to an interested female client, both looking at the space naturally, warm natural light, candid editorial style, agent gesturing toward features with relaxed natural hands, contemporary interior, warm neutral tones
```

---

## 🍽️ Restaurant & Food (4 images)

### FD-01 — Chef Plating (tests: hands in action)
**Filename:** `fd-01-chef.jpg`
```
Confident male chef in white coat carefully plating a gourmet dish in a professional kitchen, close-up on naturally posed hands placing a garnish, warm kitchen ambient lighting, shallow depth of field, documentary food photography, authentic culinary moment, anatomically correct fingers
```

### FD-02 — Restaurant Ambiance (tests: color grading + environment)
**Filename:** `fd-02-ambiance.jpg`
```
Warm inviting restaurant interior at dinner service, soft candlelight and warm pendant lights, beautifully set tables with wine glasses, bokeh background, editorial food lifestyle photography, neutral warm color grading, no harsh shadows, intimate atmosphere
```

### FD-03 — Brunch Flat Lay (tests: composition + color accuracy)
**Filename:** `fd-03-flatlay.jpg`
```
Overhead flat lay of a Sunday brunch table, pancakes with fresh berries, orange juice, coffee in ceramic cup, scattered flowers, warm natural daylight from window, lifestyle editorial photography, clean white marble surface, neutral color grading, no color cast
```

### FD-04 — Group Dining (tests: people + natural interaction)
**Filename:** `fd-04-group.jpg`
```
Three friends laughing and sharing food at a restaurant table, genuine candid moment, warm bokeh lights in background, diverse group, editorial lifestyle photography, natural eye contact between subjects, hands reaching for shared plates naturally, warm ambient tones
```

---

## ⚖️ Professional Services — Law & Finance (4 images)

### PF-01 — Client Consultation (tests: eye contact + professional setting)
**Filename:** `pf-01-consultation.jpg`
```
Professional female attorney in a navy suit having a confident focused conversation with a male client across a glass boardroom table, both making natural eye contact, city view through floor-to-ceiling windows behind them, editorial business photography, warm natural window light, relaxed natural hand positions
```

### PF-02 — Modern Office (tests: environment + color)
**Filename:** `pf-02-office.jpg`
```
Sleek contemporary law office interior, floor-to-ceiling windows overlooking a city skyline, dark wood paneling, leather chairs, glass desk with a laptop, warm diffused afternoon light, no people, architectural interior photography, neutral color grading, authoritative and modern
```

### PF-03 — Team (tests: group + professional diversity)
**Filename:** `pf-03-team.jpg`
```
Three business professionals of different backgrounds standing confidently in a modern glass office building lobby, business formal attire, genuine natural expressions, editorial corporate photography, warm neutral tones, shallow depth of field, natural relaxed postures and hands
```

### PF-04 — Document Review (tests: hands detail)
**Filename:** `pf-04-documents.jpg`
```
Close-up of an attorney's hands reviewing printed contract documents on a tidy mahogany desk, afternoon warm window light, selective focus on documents and hands, anatomically correct and natural hand positions, editorial documentary style, books in background slightly blurred
```

---

## 💪 Fitness & Wellness (4 images)

### FT-01 — Personal Training (tests: eye contact + hands on contact)
**Filename:** `ft-01-training.jpg`
```
Personal trainer giving hands-on encouragement to a male client during a dumbbell exercise in a bright modern gym, trainer's hand on client's shoulder naturally, both genuinely focused, documentary fitness photography, warm natural light from industrial windows, no posed stock photo look, anatomically natural hands
```

### FT-02 — Outdoor Running (tests: motion + natural light)
**Filename:** `ft-02-running.jpg`
```
Young woman running along an urban park path at golden hour, motion blur on legs showing speed, determined natural expression, city trees in background bokeh, editorial lifestyle photography, warm morning tones, loose active wear, neutral color grading, no color cast
```

### FT-03 — Yoga (tests: body position + color + light)
**Filename:** `ft-03-yoga.jpg`
```
Woman in warrior yoga pose on a wooden studio floor, large windows with soft morning light streaming in, minimal white and wood interior, calm focused natural expression, editorial wellness photography, neutral warm color grading, clean lines, no clutter
```

### FT-04 — Group Class (tests: group energy + diversity)
**Filename:** `ft-04-group.jpg`
```
Energetic group fitness class doing synchronized exercises in a bright modern studio, diverse participants of varying fitness levels, genuine smiles and effort, wide angle shot showing full group, editorial documentary style, natural light and warm studio lighting mix, neutral color grading
```

---

## 🛒 E-commerce & Retail (4 images)

### EC-01 — Lifestyle Product (tests: product + environment + color)
**Filename:** `ec-01-product.jpg`
```
Modern reusable water bottle on a marble countertop next to a green plant, soft natural side lighting from a window, clean white background, product photography with lifestyle context, minimal styling, sharp focus on product, neutral color grading, editorial and aspirational
```

### EC-02 — Happy Customer (tests: person + expression + hands)
**Filename:** `ec-02-customer.jpg`
```
Genuine happy young woman holding a shopping bag and smiling on a sunny city street, casual stylish outfit, candid editorial lifestyle photography, urban background bokeh, authentic not posed, warm tones, neutral color grading, naturally positioned hands holding bag
```

### EC-03 — Unboxing (tests: hands close-up + detail)
**Filename:** `ec-03-unboxing.jpg`
```
Close-up of hands carefully opening a premium matte black product box revealing tissue-wrapped item, clean marble surface, soft warm studio lighting, anatomically natural and correct hand and finger positions, aspirational unboxing moment, luxury packaging aesthetic, shallow depth of field
```

### EC-04 — Store Interior (tests: environment + color grading)
**Filename:** `ec-04-store.jpg`
```
Bright minimal boutique store interior with neatly organized clothing racks, warm natural light from street-facing windows, no people, wide angle showing store depth, modern organized retail aesthetic, neutral warm color grading, no color cast, clean and aspirational
```

---

## Summary

| Industry | Images | Key Tests |
|---|---|---|
| Healthcare | HC-01 to HC-04 | Eye contact, group hands, environment, portrait |
| Real Estate | RE-01 to RE-04 | Handshake, interior, exterior, lifestyle people |
| Food | FD-01 to FD-04 | Chef hands, ambiance, flat lay, group dining |
| Legal/Finance | PF-01 to PF-04 | Consultation, office, team, document hands |
| Fitness | FT-01 to FT-04 | Trainer hands, running, yoga, group |
| E-commerce | EC-01 to EC-04 | Product, customer, unboxing hands, store |
| **Total** | **24** | |

---

## After Generating

```powershell
# 1. Remove watermarks
python tools/watermark_remover.py lora-inputs/ --out lora-inputs/cleaned/

# 2. Check cleaned folder — reject any with bad hands or gaze
# 3. ZIP the cleaned folder
# 4. Upload ZIP to Google Drive → Share → Anyone with link
# 5. Tell Claude the shareable link — LoRA training pipeline takes it from there
```
