import customtkinter as ctk
APP_NAME="Student OS"
BG=("#F3F5F9","#12151C"); SURFACE=("#FFFFFF","#1C202A"); BORDER=("#DDE2EC","#2B3140")
SIDEBAR=("#1B2540","#0D1017"); SIDEBAR_HOVER=("#2A3862","#1A2030"); SIDEBAR_ACTIVE=("#3B6EF5","#3B6EF5")
SIDEBAR_TEXT="#E6EAF5"; SIDEBAR_MUTED="#8E9AB8"; TEXT=("#1B2333","#E8EBF2"); TEXT_MUTED=("#667085","#98A2B8")
PRIMARY=("#2F63F0","#5B8CFF"); PRIMARY_HOVER=("#2450CC","#7AA2FF"); DANGER=("#D92D20","#F97066")
DANGER_HOVER=("#B42318","#FDA29B"); WARNING=("#B54708","#FDB022"); SUCCESS=("#067647","#47CD89")
BADGE_RED="#D92D20"; BADGE_AMBER="#DC6803"; BADGE_GREEN="#039855"; BADGE_BLUE="#2F63F0"; BADGE_GREY="#667085"
ASSIGNMENT_STATE_COLORS={"Overdue":BADGE_RED,"Due Today":BADGE_AMBER,"Due Soon":BADGE_AMBER,"Upcoming":BADGE_BLUE,"Completed":BADGE_GREEN}
CLASS_STATUS_COLORS={"Ongoing":BADGE_GREEN,"Upcoming":BADGE_BLUE,"Finished":BADGE_GREY}
_FONTS={}
def font(size=14,weight="normal"):
    key=(size,weight)
    if key not in _FONTS: _FONTS[key]=ctk.CTkFont(size=size,weight=weight)
    return _FONTS[key]
def apply_global_theme(mode="system"):
    ctk.set_appearance_mode(mode); ctk.set_default_color_theme("blue")
