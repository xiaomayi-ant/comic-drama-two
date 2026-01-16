<div align="center">
<img width="1200" height="475" alt="GHBanner" src="https://github.com/user-attachments/assets/0aa67016-6eaf-458a-adb2-6e31a0763ed6" />
</div>

# Copywriting Fronter (Vite)

本前端不再直连 Gemini（无需 `GEMINI_API_KEY`），而是调用后端 `copywriting-assistant-2` 的接口：
- `POST /api/v1/generate`

## Run Locally

**Prerequisites:**  Node.js


1. Install dependencies:
   `npm install`
2. Start backend (from `copywriting-assistant-2`):
   `python main.py --serve`  (默认 `http://127.0.0.1:8000`)
3. Run the frontend:
   `npm run dev`
