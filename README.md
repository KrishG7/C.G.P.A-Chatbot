# 🤖 C.G.P.A. (ChitraGupt Personal Assistant)

**An Intelligent, Agentic Campus Assistant for the Faculty of Technology, University of Delhi.**

**C.G.P.A.** is a Hybrid RAG (Retrieval-Augmented Generation) AI application designed to bridge the gap between static campus data (syllabi, timetables, maps) and dynamic administrative actions (attendance marking, student analytics). It empowers students with instant information and gives teachers "Agentic" tools to manage classes via natural language.

-----

## 🚀 Key Features

### 🎓 For Students

  * **Dynamic Syllabus Engine:** Automatically filters and fetches syllabus summaries based on Year (1st, 2nd, 3rd) and Branch (CSE, ECE, EE).
  * **Campus Navigator:** Integrated Leaflet.js map with visual guides to key locations (Kanad Bhawan, Library, Canteen).
  * **Voice Interaction:** Full Speech-to-Text and Text-to-Speech support for hands-free queries.
  * **Contextual Chat:** Remembers conversation history for fluid interaction.

### 👨‍🏫 For Teachers (Agentic AI)

  * **Natural Language Attendance:** Mark attendance by speaking naturally.
      * *"Mark Roll No. 101 and 102 as Present."*
      * *"Mark everyone present whose name starts with 'A'."* (Pattern Matching)
  * **Data Analytics:** Query student performance instantly.
      * *"Show me students with attendance below 75%."*
  * **Smart Roster Upload:** Bulk import student data via CSV/Excel.
  * **Privacy:** Role-based access ensures students cannot access teacher tools.

-----

## 🏗️ Technical Architecture

This project uses a **Hybrid RAG** approach with a "Brain, Muscle, Memory" architecture:

1.  **The Brain (AI & Logic):**

      * **Google Gemini (Flash):** Runs with `Temperature 0.0` for strict adherence to facts. The model name defaults to the `gemini-flash-latest` alias and can be changed with the `GEMINI_MODEL` environment variable, because Google retires specific model names (`gemini-2.0-flash` now returns a 404).
      * **TF-IDF Vector Search (Scikit-Learn):** Handles general queries (Syllabus, Faculty) efficiently without heavy vector databases.
      * **Hard Logic Injection:** For Room/Vacancy queries, the system bypasses vector search and injects raw timetable data for precise calculation.

2.  **The Muscle (Backend - Flask):**

      * **Action Interceptors:** The Python backend intercepts JSON commands from the AI to execute database writes (The AI never touches the DB directly).
      * **Data Processing:** `process_data.py` converts PDFs and Images into a semantic knowledge base.

3.  **The Memory (Database - Supabase):**

      * **PostgreSQL** schema for `students`, `classes`, and `attendance_records`.

4.  **The Face (Frontend):**

      * **Vanilla JavaScript & CSS:** No heavy frameworks. Features Glassmorphism UI and optimized for mobile/desktop.

-----

## 📂 Project Structure

```text
├── backend
│   ├── app.py                 # Main Flask API & Action Handlers
│   ├── process_data.py        # ETL Script: PDF/Image -> Knowledge Base
│   ├── knowledge_base.json    # Processed text chunks (The "Book")
│   ├── vectorizer.pkl         # TF-IDF Model (The "Index")
│   └── tfidf_matrix.pkl       # Matrix Model (The "Map")
├── data
│   ├── knowledge_source       # Raw PDFs, Timetables, Images
│   └── structured_data        # Campus images for the Map
├── frontend
│   ├── index.html             # Main Entry Point
│   ├── script.js              # Frontend Logic (Auth, Voice, API)
│   └── style.css              # Cyberpunk/Glassmorphism Styles
└── requirements.txt           # Python Dependencies
```

-----

## 🛠️ Installation & Setup

### 1\. Clone the Repository

```bash
git clone https://github.com/Mr-BlackAngek/CGPA-Chatbot.git
cd CGPA-Chatbot
```

### 2\. Backend Setup

Create a virtual environment and install dependencies:

```bash
cd backend
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
```

Create a `.env` file in the project root:

```env
GEMINI_API_KEY=your_google_ai_key
SUPABASE_URL=your_supabase_url
SUPABASE_KEY=your_supabase_service_role_key
```

### 3\. Train the Brain

Before running the app, you must process the data files in `/data/knowledge_source`:

```bash
python process_data.py
```

*This generates `knowledge_base.json`, `vectorizer.pkl`, and `tfidf_matrix.pkl`.*

### 4\. Run the Application

```bash
python app.py
```

The server will start at `http://127.0.0.1:5001`.

-----

## 🚀 Deployment

  * **Frontend:** Hosted on **Vercel** (Static site serving `index.html`).
  * **Backend:** Hosted on **Railway** (Python Flask Service).
  * **Database:** Hosted on **Supabase**.

**Note for Production:** Ensure `process_data.py` is run locally and the generated `.pkl` and `.json` files are pushed to the repository so the production server has the latest "Brain".

-----

## 🛡️ Action Protocols (How it works)

When a teacher speaks, the AI outputs a **JSON Command** instead of text. The Backend intercepts this:

**User:** "Mark attendance for roll numbers ending in 77."

**AI Output (Hidden):**

```json
{
  "action": "update_attendance",
  "pattern": { "type": "endswith", "value": "77" },
  "status": "Present"
}
```

**Backend Action:**

1.  Scans class roster.
2.  Finds matching IDs.
3.  Writes to Supabase.
4.  Returns: "✅ Marked Present for 3 students..."

-----

## 📜 License

This project is developed for the Faculty of Technology, University of Delhi.

-----

---

## Database setup (Supabase)

1. Create a Supabase project and open **SQL Editor**.
2. Paste and run [`database/schema.sql`](database/schema.sql). It creates `classes`, `students`, `attendance_records`, `conversations` and `profiles` (roles), with the unique indexes the upserts need. It is safe to re-run on an existing project.
3. **Project Settings > API**: copy the project URL and a key into `.env` as `SUPABASE_URL` and `SUPABASE_KEY`. Keep the key server-side only: this backend never sends it to the browser.
4. Use the **`service_role`** key in `.env` (server only), then run [`database/lock_down.sql`](database/lock_down.sql) to remove any "allow everyone" policies, so the public `anon` key cannot read student data. Run it only after the app works with the new key.

```bash
cp .env.example .env            # then fill in GEMINI_API_KEY, SUPABASE_URL, SUPABASE_KEY
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
python backend/app.py           # http://127.0.0.1:5001
pytest tests/                   # no network needed
```

## Login and roles

| Role | How it is created | What it can do |
|---|---|---|
| Student | Sign up in the app (approved immediately) | Ask questions, campus map, subjects |
| Teacher | Sign up in the app; **an admin must approve** the account | Classes, roster upload, attendance and analytics by chat |
| Admin | **Only** by inserting a row in the Supabase SQL editor (see the end of `database/schema.sql`) | Approve teachers |

- Passwords live in Supabase Auth. The backend verifies the bearer token on every protected call and reads the role from the `profiles` table; the browser's own claims are ignored.
- A teacher can only touch their own classes: the class id is checked against the teacher's email.
- If your Supabase project has **Confirm email** switched on (Authentication > Providers > Email), new users must click the emailed link before logging in. Switch it off for a local demo.
- `GET /` and the guest chat need no login.

## Status and limits

Checked by running the backend with a real Gemini key (October 2026):

- **Retrieval** (TF-IDF, top 8 chunks): on 12 factual questions taken from the data files, the right fact was in the retrieved context for 8 of 12 after rebuilding the index (5 of 12 with the stale index). Misses are mostly faculty-email lookups, where TF-IDF ranks name-heavy chunks poorly.
- **Rebuild the index** with `python backend/process_data.py` whenever anything in `data/knowledge_source/` changes. The shipped index had been built before `administration.txt` and `links.txt` existed, so committee emails were missing.
- **Gemini quota:** a free-tier key allows only a handful of requests, and the SDK retries silently, so a chat request can hang for minutes instead of failing fast.
- **Supabase features** (class creation, roster upload, attendance by chat, analytics, history) were tested end to end against a local PostgREST copy of the schema, through the real UI. Bugs fixed: class creation sent a column that does not exist, deleting a student removed that roll number from every teacher's classes, the analytics reply leaked raw JSON and made up percentages, and the roster sidebar showed a stale 0%.
- **Login:** real sign-in with Supabase Auth; the server takes each user's role from a verified token (see "Login and roles"). Not hardened for production: no rate limiting on login, no password reset screen, and the Gemini key is shared by all users.
- Answers come from a language model and are not verified against the source documents.
