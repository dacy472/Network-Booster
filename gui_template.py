import customtkinter as ctk

# 1. Force Dark Mode globally
ctk.set_appearance_mode("Dark")  
ctk.set_default_color_theme("blue")  

class ModernAppTemplate(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("CustomTkinter Modern Template")
        self.geometry("800x500")
        self.minsize(600, 400) # Prevent window from shrinking too small

        # Configure the main 1x2 grid (row 0, column 0=Sidebar, column 1=Main View)
        # Giving weight=1 to column 1 ensures the main content area stretches dynamically
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        # ==========================================
        # SIDEBAR (Settings Area)
        # ==========================================
        # corner_radius=0 keeps the extreme left edges flat against the window border
        self.sidebar_frame = ctk.CTkFrame(self, width=220, corner_radius=0)
        self.sidebar_frame.grid(row=0, column=0, sticky="nsew") # nsew ensures it stretches vertically
        
        # We give row 4 weight=1 so it acts as a flexible spacer, pushing the bottom elements down
        self.sidebar_frame.grid_rowconfigure(4, weight=1)

        self.logo_label = ctk.CTkLabel(self.sidebar_frame, text="Settings", font=ctk.CTkFont(size=20, weight="bold"))
        self.logo_label.grid(row=0, column=0, padx=20, pady=(20, 10))

        # Sidebar Buttons
        self.btn_general = ctk.CTkButton(self.sidebar_frame, text="General Options")
        self.btn_general.grid(row=1, column=0, padx=20, pady=10)

        self.btn_network = ctk.CTkButton(self.sidebar_frame, text="Network Settings")
        self.btn_network.grid(row=2, column=0, padx=20, pady=10)

        self.btn_advanced = ctk.CTkButton(self.sidebar_frame, text="Advanced")
        self.btn_advanced.grid(row=3, column=0, padx=20, pady=10)

        # Theme Toggle at the bottom
        self.appearance_label = ctk.CTkLabel(self.sidebar_frame, text="Theme:", anchor="w")
        self.appearance_label.grid(row=5, column=0, padx=20, pady=(10, 0))
        
        self.appearance_menu = ctk.CTkOptionMenu(self.sidebar_frame, values=["Dark", "Light", "System"], command=self.change_theme)
        self.appearance_menu.grid(row=6, column=0, padx=20, pady=(10, 20))
        self.appearance_menu.set("Dark")

        # ==========================================
        # MAIN CONTENT AREA
        # ==========================================
        # fg_color="transparent" lets the dark mode background bleed through
        self.main_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.main_frame.grid(row=0, column=1, sticky="nsew", padx=30, pady=30)
        
        # Give column 0 weight=1 so everything inside main_frame stretches properly
        self.main_frame.grid_columnconfigure(0, weight=1)

        # Title
        self.content_label = ctk.CTkLabel(self.main_frame, text="Dashboard", font=ctk.CTkFont(size=32, weight="bold"))
        self.content_label.grid(row=0, column=0, sticky="w", pady=(0, 30))

        # Responsive Input Field
        # sticky="ew" (East-West) forces the entry widget to stretch to fill the horizontal space
        self.url_entry = ctk.CTkEntry(self.main_frame, placeholder_text="Enter a URL or Command...", height=40)
        self.url_entry.grid(row=1, column=0, sticky="ew", pady=(0, 20)) 

        # Action Button
        # We explicitly round the corners of the button (corner_radius)
        self.action_button = ctk.CTkButton(self.main_frame, text="Launch Operation", height=40, corner_radius=8)
        self.action_button.grid(row=2, column=0, sticky="w", pady=(0, 50))

        # ==========================================
        # NEON-BLUE PROGRESS BAR
        # ==========================================
        self.progress_label = ctk.CTkLabel(self.main_frame, text="Operation Progress:", font=ctk.CTkFont(weight="bold"))
        self.progress_label.grid(row=3, column=0, sticky="w", pady=(0, 5))

        # We override the default blue with a bright custom Hex code for the "neon" effect
        # sticky="ew" ensures it stretches flawlessly when the user resizes the window
        self.progress_bar = ctk.CTkProgressBar(self.main_frame, progress_color="#00e5ff", height=18, corner_radius=10)
        self.progress_bar.grid(row=4, column=0, sticky="ew")
        
        # Set dummy progress for template viewing
        self.progress_bar.set(0.65) 

    def change_theme(self, new_appearance_mode: str):
        ctk.set_appearance_mode(new_appearance_mode)

if __name__ == "__main__":
    app = ModernAppTemplate()
    app.mainloop()
