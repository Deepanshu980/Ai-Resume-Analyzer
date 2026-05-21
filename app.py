import streamlit as st
import pandas as pd
import base64
import random
import time
import datetime
import pymysql
import os
import socket
import platform
import geocoder
import secrets
import io
import plotly.express as px
from geopy.geocoders import Nominatim
from pyresparser import ResumeParser
from pdfminer3.layout import LAParams
from pdfminer3.pdfpage import PDFPage
from pdfminer3.pdfinterp import PDFResourceManager, PDFPageInterpreter
from pdfminer3.converter import TextConverter
from streamlit_tags import st_tags
from PIL import Image
from Courses import (
    ds_course, web_course, android_course, ios_course, uiux_course,
    resume_videos, interview_videos,
)
import nltk
 
nltk.download('stopwords', quiet=True)
 
import spacy
from spacy.cli import download as spacy_download
 
 
# ── spaCy model ─────────────────────────────────────────────────────────────
 
def ensure_spacy_model(model_name: str = "en_core_web_sm"):
    try:
        return spacy.load(model_name)
    except OSError:
        spacy_download(model_name)
        return spacy.load(model_name)
 
 
ensure_spacy_model()
 
# ── Env vars ─────────────────────────────────────────────────────────────────
 
from dotenv import load_dotenv
load_dotenv()
 
ADMIN_NAME     = os.getenv("ADMIN_NAME", "Admin")
ADMIN_USER     = os.getenv("ADMIN_USER", "admin")
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "admin@resume-analyzer")
 
# ── Database connection (graceful if unavailable) ────────────────────────────
 
def get_connection():
    """Return a live pymysql connection, or None if DB is unreachable."""
    try:
        conn = pymysql.connect(
            host=os.getenv("DB_HOST", "localhost"),
            user=os.getenv("DB_USER", "root"),
            password=os.getenv("DB_PASSWORD", ""),
            db=os.getenv("DB_NAME", "CV"),
            connect_timeout=5,
        )
        return conn
    except Exception as exc:
        st.warning(
            f"⚠️ Database unavailable — data will not be saved this session. ({exc})"
        )
        return None
 
 
connection = get_connection()
cursor = connection.cursor() if connection else None
 
 
def ping_db():
    """Keep the MySQL connection alive; re-connect if it dropped."""
    global connection, cursor
    if connection is None:
        connection = get_connection()
        cursor = connection.cursor() if connection else None
        return
    try:
        connection.ping(reconnect=True)
        cursor = connection.cursor()
    except Exception:
        connection = get_connection()
        cursor = connection.cursor() if connection else None
 
 
# ── Helpers ──────────────────────────────────────────────────────────────────
 
def get_csv_download_link(df: pd.DataFrame, filename: str, text: str) -> str:
    csv = df.to_csv(index=False)
    b64 = base64.b64encode(csv.encode()).decode()
    return f'<a href="data:file/csv;base64,{b64}" download="{filename}">{text}</a>'
 
 
def pdf_reader(file: str) -> str:
    resource_manager = PDFResourceManager()
    fake_file_handle = io.StringIO()
    converter = TextConverter(resource_manager, fake_file_handle, laparams=LAParams())
    page_interpreter = PDFPageInterpreter(resource_manager, converter)
    with open(file, "rb") as fh:
        for page in PDFPage.get_pages(fh, caching=True, check_extractable=True):
            page_interpreter.process_page(page)
    text = fake_file_handle.getvalue()
    converter.close()
    fake_file_handle.close()
    return text
 
 
def contains_any(text: str, keywords: list) -> bool:
    """Return True if any keyword appears in text (case-insensitive)."""
    if not text:
        return False
    upper = text.upper()
    return any(k.upper() in upper for k in keywords)
 
 
def show_pdf(file_path: str):
    with open(file_path, "rb") as f:
        b64 = base64.b64encode(f.read()).decode("utf-8")
    st.markdown(
        f'<iframe src="data:application/pdf;base64,{b64}" '
        f'width="700" height="1000" type="application/pdf"></iframe>',
        unsafe_allow_html=True,
    )
 
 
def course_recommender(course_list: list) -> list:
    st.subheader("**Courses & Certificates Recommendations 👨‍🎓**")
    rec_course = []
    no_of_reco = st.slider("Choose Number of Course Recommendations:", 1, 10, 5)
    random.shuffle(course_list)
    for idx, (c_name, c_link) in enumerate(course_list, start=1):
        st.markdown(f"({idx}) [{c_name}]({c_link})")
        rec_course.append(c_name)
        if idx == no_of_reco:
            break
    return rec_course
 
 
# ── Database writes ───────────────────────────────────────────────────────────
 
def insert_data(
    sec_token, ip_add, host_name, dev_user, os_name_ver,
    latlong, city, state, country,
    act_name, act_mail, act_mob,
    name, email, res_score, timestamp, no_of_pages,
    reco_field, cand_level, skills, recommended_skills, courses, pdf_name,
):
    if cursor is None:
        return
    ping_db()
    sql = """INSERT INTO user_data VALUES
        (0,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)"""
    values = (
        str(sec_token), str(ip_add), host_name, dev_user, os_name_ver,
        str(latlong), city, state, country,
        act_name, act_mail, act_mob,
        name, email, str(res_score), timestamp, str(no_of_pages),
        reco_field, cand_level, skills, recommended_skills, courses, pdf_name,
    )
    cursor.execute(sql, values)
    connection.commit()
 
 
def insertf_data(feed_name, feed_email, feed_score, comments, timestamp):
    if cursor is None:
        return
    ping_db()
    sql = "INSERT INTO user_feedback VALUES (0,%s,%s,%s,%s,%s)"
    cursor.execute(sql, (feed_name, feed_email, feed_score, comments, timestamp))
    connection.commit()
 
 
# ── Page config (must be first Streamlit call) ────────────────────────────────
 
st.set_page_config(
    page_title="AI Resume Analyzer",
    page_icon="📄",
    layout="wide",
)
 
 
# ── Main app ──────────────────────────────────────────────────────────────────
 
def run():
    # Logo (graceful fallback if file missing)
    try:
        img = Image.open("./Logo/RESUM.png")
        st.image(img)
    except Exception:
        st.markdown("## 📄 AI Resume Analyzer")
 
    st.sidebar.markdown("# Choose Something...")
    activities = ["User", "Feedback", "About", "Admin"]
    choice = st.sidebar.selectbox("Choose among the given options:", activities)
 
    st.sidebar.markdown(
        '<b>Built with 🤍 by <a href="https://dnoobnerd.netlify.app/" '
        'style="text-decoration:none;color:#021659;">Deepak Padhi</a></b>',
        unsafe_allow_html=True,
    )
 
    # ── Create DB / tables ────────────────────────────────────────────────────
    if cursor is not None:
        ping_db()
        cursor.execute("CREATE DATABASE IF NOT EXISTS CV;")
        cursor.execute("USE CV;")
 
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS user_data (
                ID               INT          NOT NULL AUTO_INCREMENT,
                sec_token        VARCHAR(20)  NOT NULL,
                ip_add           VARCHAR(50)  NULL,
                host_name        VARCHAR(50)  NULL,
                dev_user         VARCHAR(50)  NULL,
                os_name_ver      VARCHAR(50)  NULL,
                latlong          VARCHAR(50)  NULL,
                city             VARCHAR(50)  NULL,
                state            VARCHAR(50)  NULL,
                country          VARCHAR(50)  NULL,
                act_name         VARCHAR(50)  NOT NULL,
                act_mail         VARCHAR(50)  NOT NULL,
                act_mob          VARCHAR(20)  NOT NULL,
                Name             VARCHAR(500) NOT NULL,
                Email_ID         VARCHAR(500) NOT NULL,
                resume_score     VARCHAR(8)   NOT NULL,
                Timestamp        VARCHAR(50)  NOT NULL,
                Page_no          VARCHAR(5)   NOT NULL,
                Predicted_Field  BLOB         NOT NULL,
                User_level       BLOB         NOT NULL,
                Actual_skills    BLOB         NOT NULL,
                Recommended_skills BLOB       NOT NULL,
                Recommended_courses BLOB      NOT NULL,
                pdf_name         VARCHAR(100) NOT NULL,
                PRIMARY KEY (ID)
            );
        """)
 
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS user_feedback (
                ID          INT          NOT NULL AUTO_INCREMENT,
                feed_name   VARCHAR(50)  NOT NULL,
                feed_email  VARCHAR(50)  NOT NULL,
                feed_score  VARCHAR(5)   NOT NULL,
                comments    VARCHAR(200) NULL,
                Timestamp   VARCHAR(50)  NOT NULL,
                PRIMARY KEY (ID)
            );
        """)
 
    # ──────────────────────────────────────────────────────────────────────────
    # USER PAGE
    # ──────────────────────────────────────────────────────────────────────────
    if choice == "User":
 
        # ── Collect visitor metadata (all wrapped for server safety) ─────────
        act_name = st.text_input("Name*")
        act_mail = st.text_input("Mail*")
        act_mob  = st.text_input("Mobile Number*")
 
        sec_token   = secrets.token_urlsafe(12)
        host_name   = socket.gethostname()
        ip_add      = socket.gethostbyname(host_name)
 
        # os.getlogin() raises OSError in Docker / headless servers
        try:
            dev_user = os.getlogin()
        except Exception:
            dev_user = os.environ.get("USER", os.environ.get("USERNAME", "Unknown"))
 
        os_name_ver = platform.system() + " " + platform.release()
 
        # Geocoding — fully optional; fails gracefully
        latlong = city = state = country = ""
        try:
            g = geocoder.ip("me")
            if g and g.latlng:
                latlong = g.latlng
                geolocator = Nominatim(user_agent="ai-resume-analyzer")
                location   = geolocator.reverse(latlong, language="en", timeout=5)
                if location and location.raw.get("address"):
                    address = location.raw["address"]
                    city    = address.get("city", address.get("town", ""))
                    state   = address.get("state", "")
                    country = address.get("country", "")
        except Exception:
            pass  # geo info is non-critical; silently skip
 
        # ── Resume upload ─────────────────────────────────────────────────────
        st.markdown(
            "<h5 style='color:#021659;'>Upload Your Resume and Get Smart Recommendations</h5>",
            unsafe_allow_html=True,
        )
        pdf_file = st.file_uploader("Choose your Resume", type=["pdf"])
 
        if pdf_file is not None:
            with st.spinner("Hang On While We Cook Magic For You..."):
                time.sleep(2)
 
            os.makedirs("./Uploaded_Resumes", exist_ok=True)
            save_path = os.path.join("Uploaded_Resumes", pdf_file.name)
            pdf_name  = pdf_file.name
            with open(save_path, "wb") as f:
                f.write(pdf_file.getbuffer())
            show_pdf(save_path)
 
            resume_data = ResumeParser(save_path).get_extracted_data() or {}
            resume_text = pdf_reader(save_path)
            uppercase_text = resume_text.upper() if resume_text else ""
            skills      = [s for s in resume_data.get("skills", []) if s]
            skill_texts = [s.lower() for s in skills]
 
            if resume_data:
                st.header("**Resume Analysis 🤘**")
                st.success("Hello " + str(resume_data.get("name", "Candidate")))
 
                st.subheader("**Your Basic Info 👀**")
                for label, key in [
                    ("Name", "name"), ("Email", "email"),
                    ("Contact", "mobile_number"), ("Degree", "degree"),
                ]:
                    val = resume_data.get(key)
                    if val:
                        st.text(f"{label}: {val}")
                no_of_pages = resume_data.get("no_of_pages") or 0
                try:
                    no_of_pages = int(no_of_pages)
                except (TypeError, ValueError):
                    no_of_pages = 0
                st.text(f"Resume pages: {no_of_pages}")
 
                # Candidate level
                if no_of_pages < 1:
                    cand_level = "NA"
                    st.markdown(
                        "<h4 style='color:#d73b5c;'>You are at Fresher level!</h4>",
                        unsafe_allow_html=True,
                    )
                elif contains_any(uppercase_text, ["INTERNSHIP", "INTERNSHIPS"]):
                    cand_level = "Intermediate"
                    st.markdown(
                        "<h4 style='color:#1ed760;'>You are at Intermediate level!</h4>",
                        unsafe_allow_html=True,
                    )
                elif contains_any(uppercase_text, ["WORK EXPERIENCE", "EXPERIENCE"]):
                    cand_level = "Experienced"
                    st.markdown(
                        "<h4 style='color:#fba171;'>You are at Experience level!</h4>",
                        unsafe_allow_html=True,
                    )
                else:
                    cand_level = "Fresher"
                    st.markdown(
                        "<h4 style='color:#fba171;'>You are at Fresher level!</h4>",
                        unsafe_allow_html=True,
                    )
 
                # ── Skills recommendation ─────────────────────────────────────
                st.subheader("**Skills Recommendation 💡**")
                st_tags(
                    label="### Your Current Skills",
                    text="See our skills recommendation below",
                    value=skills,
                    key="1",
                )
 
                ds_keyword      = ["tensorflow","keras","pytorch","machine learning","deep learning","flask","streamlit"]
                web_keyword     = ["react","django","node js","react js","php","laravel","magento","wordpress","javascript","angular js","c#","asp.net","flask"]
                android_keyword = ["android","android development","flutter","kotlin","xml","kivy"]
                ios_keyword     = ["ios","ios development","swift","cocoa","cocoa touch","xcode"]
                uiux_keyword    = ["ux","adobe xd","figma","zeplin","balsamiq","ui","prototyping","wireframes","storyframes","adobe photoshop","photoshop","editing","adobe illustrator","illustrator","adobe after effects","after effects","adobe premier pro","premier pro","adobe indesign","indesign","wireframe","solid","grasp","user research","user experience"]
                n_any           = ["english","communication","writing","microsoft office","leadership","customer management","social media"]
 
                recommended_skills: list = []
                reco_field  = "General"
                rec_course  = []
 
                for skill in skill_texts:
                    if skill in ds_keyword:
                        reco_field = "Data Science"
                        st.success("**Our analysis says you are looking for Data Science Jobs.**")
                        recommended_skills = ["Data Visualization","Predictive Analysis","Statistical Modeling","Data Mining","Clustering & Classification","Data Analytics","Quantitative Analysis","Web Scraping","ML Algorithms","Keras","Pytorch","Probability","Scikit-learn","Tensorflow","Flask","Streamlit"]
                        st_tags(label="### Recommended skills for you.", text="Recommended skills generated from System", value=recommended_skills, key="2")
                        st.markdown("<h5 style='color:#1ed760;'>Adding these skills will boost 🚀 your chances!</h5>", unsafe_allow_html=True)
                        rec_course = course_recommender(ds_course)
                        break
                    elif skill in web_keyword:
                        reco_field = "Web Development"
                        st.success("**Our analysis says you are looking for Web Development Jobs.**")
                        recommended_skills = ["React","Django","Node JS","React JS","PHP","Laravel","Magento","WordPress","JavaScript","Angular JS","C#","Flask","SDK"]
                        st_tags(label="### Recommended skills for you.", text="Recommended skills generated from System", value=recommended_skills, key="3")
                        st.markdown("<h5 style='color:#1ed760;'>Adding these skills will boost 🚀 your chances!</h5>", unsafe_allow_html=True)
                        rec_course = course_recommender(web_course)
                        break
                    elif skill in android_keyword:
                        reco_field = "Android Development"
                        st.success("**Our analysis says you are looking for Android App Development Jobs.**")
                        recommended_skills = ["Android","Android development","Flutter","Kotlin","XML","Java","Kivy","GIT","SDK","SQLite"]
                        st_tags(label="### Recommended skills for you.", text="Recommended skills generated from System", value=recommended_skills, key="4")
                        st.markdown("<h5 style='color:#1ed760;'>Adding these skills will boost 🚀 your chances!</h5>", unsafe_allow_html=True)
                        rec_course = course_recommender(android_course)
                        break
                    elif skill in ios_keyword:
                        reco_field = "IOS Development"
                        st.success("**Our analysis says you are looking for IOS App Development Jobs.**")
                        recommended_skills = ["IOS","IOS Development","Swift","Cocoa","Cocoa Touch","Xcode","Objective-C","SQLite","Plist","StoreKit","UI-Kit","AV Foundation","Auto-Layout"]
                        st_tags(label="### Recommended skills for you.", text="Recommended skills generated from System", value=recommended_skills, key="5")
                        st.markdown("<h5 style='color:#1ed760;'>Adding these skills will boost 🚀 your chances!</h5>", unsafe_allow_html=True)
                        rec_course = course_recommender(ios_course)
                        break
                    elif skill in uiux_keyword:
                        reco_field = "UI-UX Development"
                        st.success("**Our analysis says you are looking for UI-UX Development Jobs.**")
                        recommended_skills = ["UI","User Experience","Adobe XD","Figma","Zeplin","Balsamiq","Prototyping","Wireframes","Storyframes","Adobe Photoshop","Editing","Illustrator","After Effects","Premier Pro","InDesign","Wireframe","Solid","Grasp","User Research"]
                        st_tags(label="### Recommended skills for you.", text="Recommended skills generated from System", value=recommended_skills, key="6")
                        st.markdown("<h5 style='color:#1ed760;'>Adding these skills will boost 🚀 your chances!</h5>", unsafe_allow_html=True)
                        rec_course = course_recommender(uiux_course)
                        break
                    elif skill in n_any:
                        reco_field = "NA"
                        st.warning("**Currently our tool predicts for: Data Science, Web, Android, IOS and UI/UX Development.**")
                        recommended_skills = ["Communication","Presentation","Problem Solving","Teamwork"]
                        st_tags(label="### Recommended skills for you.", text="General skill recommendations", value=recommended_skills, key="7")
                        st.markdown("<h5 style='color:#092851;'>More fields available in future updates.</h5>", unsafe_allow_html=True)
                        rec_course = ["Sorry! Not Available for this Field"]
                        break
 
                # Fallback if no field matched
                if not recommended_skills:
                    st.info("Could not identify a specific field from your resume keywords. Add more domain-specific skills for better recommendations.")
                    recommended_skills = ["Communication","Problem Solving","Teamwork","Adaptability"]
                    st_tags(label="### Recommended skills for you.", text="General skills to improve your resume", value=recommended_skills, key="8")
 
                # ── Resume score ──────────────────────────────────────────────
                st.subheader("**Resume Tips & Ideas 🥂**")
                resume_score = 0
 
                checks = [
                    (["OBJECTIVE", "SUMMARY"],             6,  "[+] Awesome! You have added Objective/Summary",         "[-] Please add your career objective. It shows your intent to recruiters."),
                    (["EDUCATION", "SCHOOL", "COLLEGE"],   12, "[+] Awesome! You have added Education Details",         "[-] Please add education details. Recruiters need this to assess your qualifications."),
                    (["WORK EXPERIENCE", "EXPERIENCE"],    16, "[+] Awesome! You have added Experience",                "[-] Please add experience. It helps you stand out from the crowd."),
                    (["INTERNSHIP", "INTERNSHIPS"],        6,  "[+] Awesome! You have added Internships",               "[-] Please add internships. It helps you stand out."),
                    (["SKILLS", "SKILL"],                  7,  "[+] Awesome! You have added Skills",                    "[-] Please add skills. It will help you a lot."),
                    (["HOBBIES"],                          4,  "[+] Awesome! You have added your Hobbies",              "[-] Please add hobbies. It shows personality and fit."),
                    (["INTERESTS", "INTEREST"],            5,  "[+] Awesome! You have added your Interests",            "[-] Please add interests. It shows more about your profile."),
                    (["ACHIEVEMENTS", "ACHIEVEMENT"],      13, "[+] Awesome! You have added your Achievements",         "[-] Please add achievements. It shows your capability for the role."),
                    (["CERTIFICATIONS", "CERTIFICATION"],  12, "[+] Awesome! You have added your Certifications",       "[-] Please add certifications. It shows specialization and credibility."),
                    (["PROJECTS", "PROJECT"],              19, "[+] Awesome! You have added your Projects",             "[-] Please add projects. It shows real work related to the position."),
                ]
 
                for keywords_list, pts, good_msg, bad_msg in checks:
                    if contains_any(uppercase_text, keywords_list):
                        resume_score += pts
                        st.markdown(f"<h5 style='color:#1ed760;'>{good_msg}</h5>", unsafe_allow_html=True)
                    else:
                        st.markdown(f"<h5 style='color:#000000;'>{bad_msg}</h5>", unsafe_allow_html=True)
 
                # Cap at 100 — st.progress() raises ValueError above 100
                resume_score = min(resume_score, 100)
 
                st.subheader("**Resume Score 📝**")
                st.markdown(
                    "<style>.stProgress > div > div > div > div {background-color: #d73b5c;}</style>",
                    unsafe_allow_html=True,
                )
                my_bar = st.progress(0)
                for pct in range(resume_score):
                    time.sleep(0.01)          # 0.01 s instead of 0.1 s
                    my_bar.progress(pct + 1)
 
                st.success(f"**Your Resume Writing Score: {resume_score}**")
                st.warning("**Note: This score is calculated based on the content in your Resume.**")
 
                # Timestamp
                ts       = time.time()
                cur_date = datetime.datetime.fromtimestamp(ts).strftime("%Y-%m-%d")
                cur_time = datetime.datetime.fromtimestamp(ts).strftime("%H:%M:%S")
                timestamp = f"{cur_date}_{cur_time}"
 
                # Save to DB
                try:
                    insert_data(
                        str(sec_token), str(ip_add), host_name, dev_user, os_name_ver,
                        latlong, city, state, country,
                        act_name, act_mail, act_mob,
                        resume_data.get("name", ""),
                        resume_data.get("email", ""),
                        str(resume_score), timestamp, str(no_of_pages),
                        reco_field, cand_level,
                        str(skills), str(recommended_skills), str(rec_course),
                        pdf_name,
                    )
                except Exception as e:
                    st.warning(f"Could not save data to database: {e}")
 
                # Bonus videos
                st.header("**Bonus Video for Resume Writing Tips 💡**")
                st.video(random.choice(resume_videos))
 
                st.header("**Bonus Video for Interview Tips 💡**")
                st.video(random.choice(interview_videos))
 
                st.balloons()
 
            else:
                st.error("Something went wrong while parsing the resume.")
 
    # ──────────────────────────────────────────────────────────────────────────
    # FEEDBACK PAGE
    # ──────────────────────────────────────────────────────────────────────────
    elif choice == "Feedback":
 
        ts        = time.time()
        cur_date  = datetime.datetime.fromtimestamp(ts).strftime("%Y-%m-%d")
        cur_time  = datetime.datetime.fromtimestamp(ts).strftime("%H:%M:%S")
        timestamp = f"{cur_date}_{cur_time}"
 
        with st.form("feedback_form"):
            st.write("Feedback Form")
            feed_name  = st.text_input("Name")
            feed_email = st.text_input("Email")
            feed_score = st.slider("Rate Us From 1 - 5", 1, 5)
            comments   = st.text_input("Comments")
            submitted  = st.form_submit_button("Submit")
            if submitted:
                try:
                    insertf_data(feed_name, feed_email, feed_score, comments, timestamp)
                    st.success("Thanks! Your Feedback was recorded.")
                    st.balloons()
                except Exception as e:
                    st.warning(f"Could not save feedback: {e}")
 
        # Past ratings chart (only if DB is up)
        if cursor is not None:
            try:
                ping_db()
                query = "SELECT * FROM user_feedback"
                plotfeed_data = pd.read_sql(query, connection)
                if not plotfeed_data.empty:
                    st.subheader("**Past User Rating's**")
                    labels = plotfeed_data.feed_score.unique()
                    values = plotfeed_data.feed_score.value_counts()
                    fig = px.pie(
                        values=values, names=labels,
                        title="Chart of User Rating Score From 1 - 5",
                        color_discrete_sequence=px.colors.sequential.Aggrnyl,
                    )
                    st.plotly_chart(fig)
 
                    st.subheader("**User Comment's**")
                    ping_db()
                    cursor.execute("SELECT feed_name, comments FROM user_feedback")
                    dff = pd.DataFrame(cursor.fetchall(), columns=["User", "Comment"])
                    st.dataframe(dff, width=1000)
            except Exception as e:
                st.info(f"Could not load feedback data: {e}")
 
    # ──────────────────────────────────────────────────────────────────────────
    # ABOUT PAGE
    # ──────────────────────────────────────────────────────────────────────────
    elif choice == "About":
        st.subheader("**About The Tool — AI Resume Analyzer**")
        st.markdown("""
        <p align='justify'>
            A tool which parses information from a resume using natural language processing,
            finds keywords, clusters them onto sectors, and shows recommendations, predictions
            and analytics to the applicant based on keyword matching.
        </p>
        <p align='justify'>
            <b>How to use it:</b><br/><br/>
            <b>User —</b><br/>
            In the Side Bar choose <i>User</i>, fill the required fields and upload your resume in PDF format.<br/>
            Just sit back — the tool will do the magic on its own.<br/><br/>
            <b>Feedback —</b><br/>
            A place where users can suggest feedback about the tool.<br/><br/>
            <b>Admin —</b><br/>
            Log in with the credentials set in your <code>.env</code> file
            (<code>ADMIN_USER</code> / <code>ADMIN_PASSWORD</code>).<br/>
            It will load all required data and perform analysis.
        </p>
        """, unsafe_allow_html=True)
 
    # ──────────────────────────────────────────────────────────────────────────
    # ADMIN PAGE
    # ──────────────────────────────────────────────────────────────────────────
    else:
        st.success("Welcome to Admin Side")
        ad_user     = st.text_input("Username")
        ad_password = st.text_input("Password", type="password")
 
        if st.button("Login"):
            if ad_user == ADMIN_USER and ad_password == ADMIN_PASSWORD:
 
                if cursor is None:
                    st.error("Database is not connected. Cannot load admin data.")
                    return
 
                ping_db()
 
                # User data
                cursor.execute("""
                    SELECT ID, ip_add, resume_score,
                           CONVERT(Predicted_Field USING utf8),
                           CONVERT(User_level USING utf8),
                           city, state, country
                    FROM user_data
                """)
                datanalys  = cursor.fetchall()
                plot_data  = pd.DataFrame(
                    datanalys,
                    columns=["Idt","IP_add","resume_score","Predicted_Field","User_Level","City","State","Country"],
                )
                total_users = plot_data.Idt.count()
                st.success(f"Welcome {ADMIN_NAME}! Total {total_users} user(s) have used our tool 🙂")
 
                ping_db()
                cursor.execute("""
                    SELECT ID, sec_token, ip_add, act_name, act_mail, act_mob,
                           CONVERT(Predicted_Field USING utf8), Timestamp,
                           Name, Email_ID, resume_score, Page_no, pdf_name,
                           CONVERT(User_level USING utf8),
                           CONVERT(Actual_skills USING utf8),
                           CONVERT(Recommended_skills USING utf8),
                           CONVERT(Recommended_courses USING utf8),
                           city, state, country, latlong, os_name_ver, host_name, dev_user
                    FROM user_data
                """)
                data = cursor.fetchall()
                st.header("**User's Data**")
                df = pd.DataFrame(data, columns=[
                    "ID","Token","IP Address","Name","Mail","Mobile Number",
                    "Predicted Field","Timestamp","Predicted Name","Predicted Mail",
                    "Resume Score","Total Page","File Name","User Level",
                    "Actual Skills","Recommended Skills","Recommended Course",
                    "City","State","Country","Lat Long","Server OS","Server Name","Server User",
                ])
                st.dataframe(df)
                st.markdown(get_csv_download_link(df, "User_Data.csv", "Download Report"), unsafe_allow_html=True)
 
                # Feedback data
                ping_db()
                cursor.execute("SELECT * FROM user_feedback")
                fdata = cursor.fetchall()
                st.header("**User's Feedback Data**")
                fdf = pd.DataFrame(fdata, columns=["ID","Name","Email","Feedback Score","Comments","Timestamp"])
                st.dataframe(fdf)
 
                plotfeed_data = pd.read_sql("SELECT * FROM user_feedback", connection)
 
                def safe_pie(df_src, value_col, title, colors):
                    if df_src.empty or value_col not in df_src.columns:
                        return
                    labels = df_src[value_col].unique()
                    values = df_src[value_col].value_counts()
                    fig = px.pie(values=values, names=labels, title=title,
                                 color_discrete_sequence=colors)
                    st.plotly_chart(fig)
 
                st.subheader("**User Rating's**")
                safe_pie(plotfeed_data, "feed_score",
                         "Chart of User Rating Score From 1 - 5 🤗",
                         px.colors.sequential.Aggrnyl)
 
                st.subheader("**Pie-Chart for Predicted Field Recommendation**")
                safe_pie(plot_data, "Predicted_Field",
                         "Predicted Field according to the Skills 👽",
                         px.colors.sequential.Aggrnyl_r)
 
                st.subheader("**Pie-Chart for User's Experienced Level**")
                safe_pie(plot_data, "User_Level",
                         "Pie-Chart 📈 for User's 👨‍💻 Experienced Level",
                         px.colors.sequential.RdBu)
 
                st.subheader("**Pie-Chart for Resume Score**")
                safe_pie(plot_data, "resume_score",
                         "Resume Score Distribution 💯",
                         px.colors.sequential.Agsunset)
 
                st.subheader("**Pie-Chart for Users App Used Count**")
                safe_pie(plot_data, "IP_add",
                         "Usage Based On IP Address 👥",
                         px.colors.sequential.matter_r)
 
                st.subheader("**Pie-Chart for City**")
                safe_pie(plot_data, "City",
                         "Usage Based On City 🌆",
                         px.colors.sequential.Jet)
 
                st.subheader("**Pie-Chart for State**")
                safe_pie(plot_data, "State",
                         "Usage Based on State 🚉",
                         px.colors.sequential.PuBu_r)
 
                st.subheader("**Pie-Chart for Country**")
                safe_pie(plot_data, "Country",
                         "Usage Based on Country 🌏",
                         px.colors.sequential.Purpor_r)
 
            else:
                st.error("Wrong ID & Password Provided")
 
 
run()