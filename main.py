"""Start Student OS:   python main.py

Optional: set STUDENT_OS_DB to use a different database file.
"""
from student_os.ui.app import StudentOSApp


def main():
    app = StudentOSApp()
    app.mainloop()


if __name__ == "__main__":
    main()
