from app import create_app
from app.models import db, CPDActivityType

def seed_activity_types():
    app = create_app()
    with app.app_context():
        cpd_data = [
            ("Attending Doctoral degree course", "100"),
            ("Attending Master's degree course", "50"),
            ("Attending Postgraduate Diploma course", "30"),
            ("Attending Postgraduate Certificate course", "20"),
            ("External meetings, courses and events", "1/hour"),
            ("Distance and online learning", "1/hour"),
            ("Organised specialist centre training", "4"),
            ("Service Review panel participation", "1/hour"),
            ("Service Review panel training", "1/hour"),
            ("Other external learning activity", "1/hour"),
            ("Authorship/editorship of a book", "20"),
            ("Authorship full paper - Author", "20"),
            ("Authorship full paper - Co Author", "3"),
            ("Case report submission", "3"),
            ("Audit template - Author", "3"),
            ("Audit template - Co Author", "1"),
            ("Digital resource content provider", "4"),
            ("Digital resource peer reviewer", "2"),
            ("Reviewing papers/reports", "1"),
            ("Examining national/university exam", "4"),
            ("Active examining", "4"),
            ("Exam Senior/Chair activity", "1/hour"),
            ("Review examination image bank", "1/hour"),
            ("Exam question setting", "1/hour"),
            ("Exam standard setting", "1/hour"),
            ("Educational workshop facilitator", "4"),
            ("Formal educational activities", "1"),
            ("Judging conference competitions", "2"),
            ("Leading an educational webinar", "3"),
            ("Learning/updating computer skills", "1"),
            ("National exam setting meeting", "4"),
            ("Participation in reviews", "4"),
            ("Lecture/Seminar prep & delivery", "3"),
            ("Paper prep - Author", "5"),
            ("Paper prep - Co Author", "1"),
            ("Poster prep - Author", "3"),
            ("Poster prep - Co Author", "1"),
            ("Educational podcast", "2"),
            ("Radiotherapy case lead", "5"),
            ("Radiotherapy case faculty", "3"),
            ("REAL Case publication", "3"),
            ("R-ITI module editor", "8"),
            ("R-ITI module reviewer", "4"),
            ("Self-directed learning", "1/hour"),
            ("Submitting REAL Case for review", "3"),
            ("Writing/editing guidelines", "5"),
            ("Other personal learning", "1/hour"),
        ]

        for name, credits in cpd_data:
            existing = db.session.query(CPDActivityType).filter_by(name=name).first()
            if not existing:
                db.session.add(CPDActivityType(name=name, default_credits=credits))

        db.session.commit()
        print("✅ Seeded CPD activity types successfully.")

if __name__ == "__main__":
    seed_activity_types()
