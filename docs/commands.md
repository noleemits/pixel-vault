# PixelVault — Command Reference

---

## 🚀 Daily Startup

Run these every time you start working on the project.

```powershell
# 1. Navigate to the project
cd C:\Users\PC\Documents\noleemits-pixel-vault

# 2. Start the server
python -m app.cli serve
```

Then open in your browser:
- **Dashboard** → http://localhost:8000/static/index.html
- **API docs** → http://localhost:8000/docs

---

## 🖼️ Watermark Removal (Gemini LoRA Training Images)

**Step 1 — Drop your Gemini images into:**
```
C:\Users\PC\Documents\noleemits-pixel-vault\lora-inputs\
```

**Step 2 — Run the watermark remover:**
```powershell
cd C:\Users\PC\Documents\noleemits-pixel-vault
python tools/watermark_remover.py lora-inputs/ --out lora-inputs/cleaned/
```

**Step 3 — Review cleaned images:**
```
C:\Users\PC\Documents\noleemits-pixel-vault\lora-inputs\cleaned\
```
Reject any where hands or gaze still look off. Delete those from the cleaned folder.

**Step 4 — ZIP the cleaned folder:**
```powershell
cd C:\Users\PC\Documents\noleemits-pixel-vault\lora-inputs
Compress-Archive -Path cleaned\* -DestinationPath pixelvault-lora-training.zip
```

**Step 5 — Upload ZIP to Google Drive, share with "Anyone with link", send link to Claude.**

---

## 🧪 Testing the API Manually

```powershell
# Check server is running
curl http://localhost:8000/api/v1/stats

# List all prompts
curl http://localhost:8000/api/v1/prompts

# Generate a test batch (replace 1 with your prompt ID)
curl -X POST http://localhost:8000/api/v1/generate `
  -H "Content-Type: application/json" `
  -d '{"prompt_id": 1, "count": 3, "ratio": "16:9"}'

# Check batch status (replace 1 with batch ID)
curl http://localhost:8000/api/v1/batches/1
```

---

## 🗄️ Database

```powershell
# Seed the database with all 48 master prompts
python -m app.cli seed

# Open the database directly (optional)
# Use DB Browser for SQLite → open pixelvault.db
```

---

## 🔧 Troubleshooting

**Server won't start:**
```powershell
# Make sure you're in the right folder
cd C:\Users\PC\Documents\noleemits-pixel-vault
python -m app.cli serve
```

**Generation fails with 403:**
- fal.ai balance is empty → top up at https://fal.ai/dashboard/billing

**Generation fails with 400:**
- Check your FAL_API_KEY in .env is correct

**Obsidian not logging:**
- Make sure Obsidian is open with the Local REST API plugin active
- Check OBSIDIAN_API_KEY in .env matches your plugin key

**Port already in use:**
```powershell
# Find what's using port 8000
netstat -ano | findstr :8000
# Kill it (replace PID with the number found above)
taskkill /PID <PID> /F
```
