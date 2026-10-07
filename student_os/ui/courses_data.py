from student_os import courses
_LINKED_LABELS=(("timetable","class slot","class slots"),("assignments","assignment","assignments"),("attendance","attendance record","attendance records"),("notes","note","notes"))
def credit_text(units): return f"{units} credit unit{'s' if units != 1 else ''}"
def course_summary(course): return "  |  ".join(p for p in [course["lecturer"],course["venue"],credit_text(course["credit_unit"])] if p)
def load_courses(query="",db_path=None): return courses.search_courses(query,db_path)
def count_text(shown,query=""): return f"{shown} match{'es' if shown != 1 else ''}" if query else f"{shown} course{'s' if shown != 1 else ''}"
def empty_text(query=""): return f'No courses match "{query}".' if query else "No courses yet. Click Add course to create your first one."
def delete_warning(course,counts):
    head=f"Delete {course['code']} - {course['name']}?"; lost=[]
    for key,singular,plural in _LINKED_LABELS:
        n=counts.get(key,0)
        if n: lost.append(f"{n} {singular if n==1 else plural}")
    if not lost: return head+"\n\nNothing else is linked to this course."
    return head+"\n\nThis will also permanently delete: "+", ".join(lost)+".\nThis cannot be undone."
