from datetime import datetime
from student_os import assignments,attendance,courses,notes,profile,timetable
def describe_next_class(slot):
    return f"{slot['day_of_week']} at {slot['start_time']}"
def build_dashboard(now=None,db_path=None):
    now=now or datetime.now(); prof=profile.get_profile(db_path) or {}
    return {"student_name":prof.get("name",""),"greeting":f"Welcome{', '+prof.get('name','').split()[0] if prof.get('name') else ''}","date_text":now.strftime("%A, %d %B %Y"),"course_count":len(courses.list_courses(db_path)),"todays_classes":timetable.get_todays_classes(now=now,db_path=db_path),"next_class":timetable.get_next_class(now=now,db_path=db_path),"assignments":{"items":[],"pending":0,"overdue":0,"due_today":0,"due_soon":0},"attendance":{"overall":attendance.get_overall_attendance(db_path=db_path),"standing":"","below":attendance.get_courses_below_threshold(db_path=db_path)},"recent_notes":notes.get_recent_notes(limit=5,db_path=db_path)}
