from student_os import courses,timetable
from student_os.timetable import DAYS
from student_os.ui.dashboard_data import describe_next_class
NO_CLASSES_TEXT="No classes scheduled yet."
def time_range(slot): return f"{slot['start_time']} - {slot['end_time']}"
def slot_title(slot): return f"{slot['course_code']}  {slot['course_name']}"
def course_choices(db_path=None): return [(f"{c['code']} - {c['name']}",c["id"]) for c in courses.list_courses(db_path)]
def editable_venue(slot,course): return "" if course is not None and slot["venue"]==course["venue"] else slot["venue"]
def build_week(now,db_path=None):
    weekly=timetable.get_weekly_timetable(db_path); today=DAYS[now.weekday()]; nxt=timetable.get_next_class(now=now,db_path=db_path); next_text=NO_CLASSES_TEXT
    if nxt:
        nxt={**nxt,"when_text":describe_next_class(nxt)}; next_text=f"Next class: {nxt['when_text']}  -  {nxt['course_code']} {nxt['course_name']}"
    days=[{"day":d,"is_today":d==today,"slots":weekly[d]} for d in DAYS]
    return {"today":today,"total":sum(len(d["slots"]) for d in days),"next_class":nxt,"next_text":next_text,"days":days}
