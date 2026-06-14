# 📄 AI Resume Analyzer
 
An intelligent resume analysis tool built with **Streamlit** and **Python** that parses resumes using NLP, identifies the candidate's target field, recommends missing skills and courses, scores the resume, and gives admins a full analytics dashboard.
 
---
 
## ✨ Features
 
| Feature | Description |
|---|---|
| 📤 Resume Upload | Upload a PDF resume and preview it inline |
| 🧠 NLP Parsing | Extracts name, email, phone, degree and skills automatically |
| 🎯 Field Prediction | Detects whether you're targeting Data Science, Web, Android, iOS or UI/UX |
| 💡 Skill Recommendations | Suggests missing skills based on your predicted domain |
| 📚 Course Recommendations | Recommends up to 10 curated courses from Udemy, Coursera, Udacity and more |
| 📊 Resume Score | Scores your resume (0–100) by checking for key sections |
| 🎬 Bonus Videos | Random resume writing & interview prep videos |
| 💬 Feedback | Users can rate and comment on the tool |
| 🔐 Admin Dashboard | Visualises all user data, scores, fields and geo distribution |
 
---
 
## 🖥️ Demo Pages
 
```
Sidebar → User       Upload resume, get analysis & recommendations
Sidebar → Feedback   Rate the tool and leave a comment
Sidebar → About      Description of the project
Sidebar → Admin      Protected dashboard with analytics charts
```
 
---
 
## 🛠️ Tech Stack
 
- **Frontend** — [Streamlit](https://streamlit.io/)
- **NLP / Parsing** — [pyresparser](https://github.com/OmkarPathak/pyresparser), [spaCy](https://spacy.io/) (`en_core_web_sm`), [NLTK](https://www.nltk.org/)
- **PDF Reading** — [pdfminer3](https://pypi.org/project/pdfminer3/)
- **Database** — MySQL / MariaDB via [PyMySQL](https://pymysql.readthedocs.io/)
- **Charts** — [Plotly Express](https://plotly.com/python/plotly-express/)
- **Geocoding** — [geocoder](https://geocoder.readthedocs.io/) + [geopy](https://geopy.readthedocs.io/)
- **Image** — [Pillow](https://pillow.readthedocs.io/)
---
 
## ⚡ Quick Start
 
### 1 — Clone the repository
 
```bash
git clone https://github.com/your-username/ai-resume-analyzer.git
cd ai-resume-analyzer
```
 
### 2 — Create and activate a virtual environment
 
```bash
python -m venv venv
 
# macOS / Linux
source venv/bin/activate
 
# Windows
venv\Scripts\activate
```
 
### 3 — Install dependencies
 
```bash
pip install -r requirements.txt
```
 
> **Note:** `pyresparser` requires **Python 3.7 – 3.9**. It will not install on Python 3.10+.  
> The `en_core_web_sm` spaCy model is installed automatically from the wheel URL in `requirements.txt`.
 
### 4 — Set up environment variables
 
```bash
cp .env.example .env
```
 
Open `.env` and fill in your values:
 
```env
DB_HOST=localhost
DB_USER=root
DB_PASSWORD=your_password_here
DB_NAME=CV
 
ADMIN_USER=admin
ADMIN_PASSWORD=admin@resume-analyzer
ADMIN_NAME=Admin
```
 
### 5 — Create the MySQL database
 
The app creates the required tables automatically on first run, but the database user needs to exist first:
 
```sql
CREATE DATABASE IF NOT EXISTS CV;
-- Grant your DB_USER access to it if needed:
GRANT ALL PRIVILEGES ON CV.* TO 'root'@'localhost';
FLUSH PRIVILEGES;
```
 
### 6 — (Optional) Add logo images
 
Place your logo files in a `Logo/` folder at the project root:
 
```
Logo/
  RESUM.png        ← banner image shown at the top of the app
  recommend.png    ← browser tab favicon
```
 
The app runs fine without these — it falls back to a text heading.
 
### 7 — Run the app
 
```bash
streamlit run app.py
```
 
The app will open at **http://localhost:8501**.
 
---
 
## 📁 Project Structure
 
```
ai-resume-analyzer/
│
├── app.py                  # Main Streamlit application
├── Courses.py              # Course & video recommendation data
├── requirements.txt        # Python dependencies
├── .env.example            # Environment variable template
├── .env                    # Your local secrets (git-ignored)
│
├── Logo/                   # Optional — logo images
│   ├── RESUM.png
│   └── recommend.png
│
└── Uploaded_Resumes/       # Auto-created — stores uploaded PDFs
```
 
---
 
## 🗄️ Database Schema
 
Two tables are created automatically inside the `CV` database.
 
### `user_data`
| Column | Type | Description |
|---|---|---|
| `ID` | INT AUTO_INCREMENT | Primary key |
| `sec_token` | VARCHAR(20) | Unique session token |
| `ip_add` | VARCHAR(50) | Visitor IP address |
| `host_name` | VARCHAR(50) | Server hostname |
| `dev_user` | VARCHAR(50) | OS user running the server |
| `os_name_ver` | VARCHAR(50) | Server OS and version |
| `latlong` | VARCHAR(50) | Geo coordinates |
| `city / state / country` | VARCHAR(50) | Resolved location |
| `act_name / act_mail / act_mob` | VARCHAR | User-entered contact info |
| `Name / Email_ID` | VARCHAR(500) | Parsed from the resume |
| `resume_score` | VARCHAR(8) | Score 0–100 |
| `Timestamp` | VARCHAR(50) | Submission date-time |
| `Page_no` | VARCHAR(5) | Number of resume pages |
| `Predicted_Field` | BLOB | Detected job domain |
| `User_level` | BLOB | Fresher / Intermediate / Experienced |
| `Actual_skills` | BLOB | Skills extracted from resume |
| `Recommended_skills` | BLOB | Skills recommended by the tool |
| `Recommended_courses` | BLOB | Courses recommended by the tool |
| `pdf_name` | VARCHAR(100) | Uploaded file name |
 
### `user_feedback`
| Column | Type | Description |
|---|---|---|
| `ID` | INT AUTO_INCREMENT | Primary key |
| `feed_name` | VARCHAR(50) | Reviewer name |
| `feed_email` | VARCHAR(50) | Reviewer email |
| `feed_score` | VARCHAR(5) | Rating 1–5 |
| `comments` | VARCHAR(200) | Free-text comment |
| `Timestamp` | VARCHAR(50) | Submission date-time |
 
---
 
## 📊 Resume Scoring
 
The tool checks for these sections in the PDF text and awards points:
 
| Section | Points |
|---|---|
| Objective / Summary | 6 |
| Education | 12 |
| Work Experience | 16 |
| Internships | 6 |
| Skills | 7 |
| Hobbies | 4 |
| Interests | 5 |
| Achievements | 13 |
| Certifications | 12 |
| Projects | 19 |
| **Maximum** | **100** |
 
---
 
## 🎯 Field Detection Keywords
 
| Field | Trigger keywords (any match) |
|---|---|
| Data Science | tensorflow, keras, pytorch, machine learning, deep learning, flask, streamlit |
| Web Development | react, django, node js, php, laravel, wordpress, javascript, angular js, flask |
| Android Development | android, flutter, kotlin, xml, kivy |
| iOS Development | ios, swift, cocoa, cocoa touch, xcode |
| UI/UX Development | ux, figma, adobe xd, zeplin, balsamiq, prototyping, wireframes, user research |
 
---
 
## 🔐 Admin Dashboard
 
1. Select **Admin** from the sidebar.
2. Log in with the credentials in your `.env` file.
3. The dashboard shows:
   - Full user data table (downloadable as CSV)
   - Feedback data table
   - Pie charts for ratings, predicted fields, experience levels, resume scores, and geographic distribution
---
 
## 🔧 Troubleshooting
 
**`OSError: no controlling terminal`**  
Occurs when running inside Docker or a headless server. Fixed in this version — the app falls back to reading `$USER` / `$USERNAME` from the environment.
 
**`pymysql.err.OperationalError` on startup**  
The database is unreachable. Check your `.env` credentials and that the MySQL service is running. The app will still load and show a warning banner — only the save/load features are disabled.
 
**`ValueError: Value must be between 0 and 100`** (Streamlit progress bar)  
Can happen if a resume scores over 100. Fixed — the score is now capped at 100 before the progress bar call.
 
**`pyresparser` fails to install on Python 3.10+**  
Use Python 3.8 or 3.9. Create your venv with:
```bash
python3.9 -m venv venv
```
 
**spaCy model not found**  
The app auto-downloads `en_core_web_sm` on first run. If that fails, install it manually:
```bash
python -m spacy download en_core_web_sm
```
 
---
 
## 🤝 Contributing
 
1. Fork the repository
2. Create a feature branch: `git checkout -b feature/my-feature`
3. Commit your changes: `git commit -m "Add my feature"`
4. Push to the branch: `git push origin feature/my-feature`
5. Open a Pull Request
---
 
## 📄 License
 
This project is open-source and available under the [MIT License](LICENSE).
