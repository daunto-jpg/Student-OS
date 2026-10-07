import customtkinter as ctk
from student_os.ui import theme
from student_os.ui.theme import font
def clear(frame):
    for child in frame.winfo_children(): child.destroy()
def muted_label(master,text,size=13,**kw):
    return ctk.CTkLabel(master,text=text,font=font(size),text_color=theme.TEXT_MUTED,anchor="w",justify="left",**kw)
def body_label(master,text,size=14,weight="normal",**kw):
    return ctk.CTkLabel(master,text=text,font=font(size,weight),text_color=theme.TEXT,anchor="w",justify="left",**kw)
def page_header(master,title,subtitle=None):
    frame=ctk.CTkFrame(master,fg_color="transparent"); frame.grid_columnconfigure(0,weight=1)
    ctk.CTkLabel(frame,text=title,font=font(26,"bold"),text_color=theme.TEXT,anchor="w").grid(row=0,column=0,sticky="w")
    if subtitle: muted_label(frame,subtitle,size=14).grid(row=1,column=0,sticky="w")
    return frame
class Badge(ctk.CTkLabel):
    def __init__(self,master,text,color=theme.BADGE_GREY):
        super().__init__(master,text=f"  {text}  ",font=font(11,"bold"),text_color="white",fg_color=color,corner_radius=9,height=20)
class Card(ctk.CTkFrame):
    def __init__(self,master,title=None,link_text=None,on_link=None):
        super().__init__(master,fg_color=theme.SURFACE,corner_radius=12,border_width=1,border_color=theme.BORDER)
        self.grid_columnconfigure(0,weight=1); self.grid_rowconfigure(1,weight=1)
        if title:
            header=ctk.CTkFrame(self,fg_color="transparent"); header.grid(row=0,column=0,sticky="ew",padx=16,pady=(14,2)); header.grid_columnconfigure(0,weight=1)
            ctk.CTkLabel(header,text=title,font=font(15,"bold"),text_color=theme.TEXT,anchor="w").grid(row=0,column=0,sticky="w")
            if link_text and on_link: ctk.CTkButton(header,text=link_text,width=70,height=24,font=font(12),fg_color="transparent",text_color=theme.PRIMARY,hover_color=theme.BG,command=on_link).grid(row=0,column=1,sticky="e")
        self.body=ctk.CTkFrame(self,fg_color="transparent"); self.body.grid(row=1,column=0,sticky="nsew",padx=16,pady=(4,14))
class StatTile(ctk.CTkFrame):
    def __init__(self,master,label,value,hint="",value_color=theme.TEXT):
        super().__init__(master,fg_color=theme.SURFACE,corner_radius=12,border_width=1,border_color=theme.BORDER)
        muted_label(self,label,size=12).pack(anchor="w",padx=16,pady=(12,0)); ctk.CTkLabel(self,text=str(value),font=font(28,"bold"),text_color=value_color,anchor="w").pack(anchor="w",padx=16); muted_label(self,hint or " ",size=12).pack(anchor="w",padx=16,pady=(0,12))
def divider(master): return ctk.CTkFrame(master,height=1,fg_color=theme.BORDER)
def primary_button(master,text,command,width=120,**kw):
    return ctk.CTkButton(master,text=text,command=command,width=width,height=34,font=font(13,"bold"),fg_color=theme.PRIMARY,hover_color=theme.PRIMARY_HOVER,text_color="white",**kw)
def outline_button(master,text,command,width=64,danger=False):
    return ctk.CTkButton(master,text=text,command=command,width=width,height=28,font=font(12),fg_color="transparent",border_width=1,border_color=theme.BORDER,text_color=theme.DANGER if danger else theme.TEXT,hover_color=theme.BG)
