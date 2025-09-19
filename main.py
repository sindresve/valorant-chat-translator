import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox, filedialog
import easyocr
import numpy as np
import torch
from googletrans import Translator
import mss
import threading
import time
from collections import defaultdict
import warnings
from PIL import Image, ImageTk, ImageDraw
import io
import keyboard
import json
import sys, os
import tempfile
import webbrowser

def resource_path(relative_path):
    """ Get absolute path to resource (for PyInstaller) """
    if hasattr(sys, '_MEIPASS'):
        return os.path.join(sys._MEIPASS, relative_path)
    return os.path.join(os.path.abspath("."), relative_path)

# Suppress warnings
warnings.filterwarnings('ignore', category=UserWarning)

dark_mode = {
    'bg_primary': '#0d1117',
    'bg_secondary': '#161b22', 
    'bg_tertiary': '#21262d',
    'accent_primary': '#238636',
    'accent_secondary': '#1f6feb',
    'text_primary': '#e6edf3',
    'text_secondary': '#7d8590',
    'border': '#30363d',
    'success': '#3fb950',
    'warning': '#d29922',
    'error': '#f85149'
}

light_mode = {
    'bg_primary': '#f5f5f5',      
    'bg_secondary': '#e5e5e5',     
    'bg_tertiary': '#dcdcdc',      
    'accent_primary': '#2e8b57',   
    'accent_secondary': '#1e90ff',
    'text_primary': '#1a1a1a',     
    'text_secondary': '#555555',   
    'border': '#c0c0c0',           
    'success': '#3fb950',          
    'warning': '#d29922',          
    'error': '#f85149'             
}


class ModernOCRTranslatorUI:
    def __init__(self, root):
        self.root = root
        self.root.title("VALORANT Chat Translator")
        self.root.geometry("1200x800")
        self.root.configure(bg='#0d1117')
        self.root.minsize(1000, 600)
        
        # Color scheme - Modern GitHub dark theme
        self.colors = dark_mode
        
        # Initialize variables
        self.reader = None
        self.translator = None
        self.using_gpu = False
        self.is_running = False
        self.capture_thread = None
        self.monitor_info = None
        self.box_coordinates = None
        self.current_tab = "home"
        self.capture_key = "F9"
        self.highlight_overlay = None  # Track the highlight overlay
        
        # Settings
        self.load_settings()
        
        # Setup UI
        self.setup_ui()
        
        # Initialize components
        self.initialize_components()
        
    def load_settings(self):
        """Load settings from temp folder"""
        try:
            settings_path = os.path.join(tempfile.gettempdir(), 'valorant_translator_settings.json')
            with open(settings_path, 'r') as f:
                settings = json.load(f)
                self.capture_key = settings.get('capture_key', 'F9')
                self.box_coordinates = settings.get('box_coordinates', None)
        except:
            pass
            
    def save_settings(self):
        """Save settings to temp folder"""
        settings = {
            'capture_key': self.capture_key,
            'box_coordinates': self.box_coordinates,
            'color_mode': self.colors
        }
        try:
            settings_path = os.path.join(tempfile.gettempdir(), 'valorant_translator_settings.json')
            with open(settings_path, 'w') as f:
                json.dump(settings, f, indent=2)
        except:
            pass
        
    def setup_ui(self):
        """Setup the main UI components"""
        # Main container
        main_frame = tk.Frame(self.root, bg=self.colors['bg_primary'])
        main_frame.pack(fill='both', expand=True)
        
        # Sidebar
        self.setup_sidebar(main_frame)
        
        # Content area
        self.setup_content_area(main_frame)
        
        # Footer
        self.setup_footer(main_frame)
        
    def setup_sidebar(self, parent):
        """Setup sidebar with navigation"""
        sidebar_frame = tk.Frame(parent, bg=self.colors['bg_secondary'], width=250)
        sidebar_frame.pack(side='left', fill='y', padx=(0, 1))
        sidebar_frame.pack_propagate(False)
        
        # Logo/Title
        title_frame = tk.Frame(sidebar_frame, bg=self.colors['bg_secondary'])
        title_frame.pack(fill='x', pady=(20, 30))
        
        logo_label = tk.Label(
            title_frame,
            text="🎯 VALORANT",
            font=('Segoe UI', 16, 'bold'),
            fg=self.colors['text_primary'],
            bg=self.colors['bg_secondary']
        )
        logo_label.pack()
        
        subtitle_label = tk.Label(
            title_frame,
            text="Chat Translator",
            font=('Segoe UI', 11),
            fg=self.colors['text_secondary'],
            bg=self.colors['bg_secondary']
        )
        subtitle_label.pack()
        
        # Navigation buttons
        nav_frame = tk.Frame(sidebar_frame, bg=self.colors['bg_secondary'])
        nav_frame.pack(fill='x', padx=10)
        
        self.nav_buttons = {}
        
        # Home tab
        self.nav_buttons['home'] = self.create_nav_button(
            nav_frame, "🏠 Home", "home", True
        )
        
        # Settings tab
        self.nav_buttons['settings'] = self.create_nav_button(
            nav_frame, "⚙️ Settings", "settings", False
        )
        
        # System info
        self.setup_sidebar_status(sidebar_frame)
        
    def create_nav_button(self, parent, text, tab_name, is_active=False):
        """Create navigation button"""
        bg_color = self.colors['accent_secondary'] if is_active else self.colors['bg_secondary']
        fg_color = self.colors['text_primary']
        
        btn = tk.Button(
            parent,
            text=text,
            font=('Segoe UI', 11),
            fg=fg_color,
            bg=bg_color,
            relief='flat',
            anchor='w',
            padx=15,
            pady=12,
            cursor='hand2',
            command=lambda: self.switch_tab(tab_name)
        )
        btn.pack(fill='x', pady=(0, 2))
        
        # Hover effects
        btn.bind("<Enter>", lambda e: self.nav_button_hover(btn, True))
        btn.bind("<Leave>", lambda e: self.nav_button_hover(btn, False))
        
        return btn
        
    def nav_button_hover(self, btn, is_hover):
        """Handle navigation button hover effects"""
        if btn == self.nav_buttons.get(self.current_tab):
            return  # Don't change active button
            
        if is_hover:
            btn.config(bg=self.colors['bg_tertiary'])
        else:
            btn.config(bg=self.colors['bg_secondary'])
            
    def setup_sidebar_status(self, parent):
        """Setup status indicators in sidebar"""
        status_frame = tk.Frame(parent, bg=self.colors['bg_secondary'])
        status_frame.pack(side='bottom', fill='x', padx=10, pady=0)
        
        status_title = tk.Label(
            status_frame,
            text="System Status",
            font=('Segoe UI', 10, 'bold'),
            fg=self.colors['text_primary'],
            bg=self.colors['bg_secondary']
        )
        status_title.pack(anchor='w', pady=(0, 10))
        
        # Status indicators
        self.status_indicators = {}
        
        indicators = [
            ('gpu', 'GPU'),
            ('ocr', 'OCR Engine'), 
            ('translator', 'Translator'),
            ('screen', 'Screen Capture')
        ]
        
        for key, label in indicators:
            frame = tk.Frame(status_frame, bg=self.colors['bg_secondary'])
            frame.pack(fill='x', pady=2)
            
            dot = tk.Label(
                frame,
                text="●",
                font=('Segoe UI', 8),
                fg=self.colors['warning'],
                bg=self.colors['bg_secondary']
            )
            dot.pack(side='left')
            
            text = tk.Label(
                frame,
                text=f"{label}: Initializing...",
                font=('Segoe UI', 9),
                fg=self.colors['text_secondary'],
                bg=self.colors['bg_secondary']
            )
            text.pack(side='left', padx=(5, 0))
            
            self.status_indicators[key] = {'dot': dot, 'text': text}

        footer_frame = tk.Frame(status_frame, bg=self.colors['bg_secondary'], height=40)
        footer_frame.pack(side='bottom', fill='x')
        footer_frame.pack_propagate(False)

        prefix_label = tk.Label(
            footer_frame,
            text="Created with ",
            font=('Segoe UI', 9, 'bold'),
            fg=self.colors['text_primary'],
            bg=self.colors['bg_secondary']
        )
        prefix_label.pack(side="left")

        # Red heart ♥
        heart_label = tk.Label(
            footer_frame,
            text="♥",
            font=('Segoe UI', 9, 'bold'),
            fg="red",
            bg=self.colors['bg_secondary']
        )
        heart_label.pack(side="left")

        # " by " text
        by_label = tk.Label(
            footer_frame,
            text=" by ",
            font=('Segoe UI', 9, 'bold'),
            fg=self.colors['text_primary'],
            bg=self.colors['bg_secondary']
        )
        by_label.pack(side="left")

        velox_label = tk.Label(
            footer_frame,
            text="velox",
            font=('Segoe UI', 9, 'bold'),
            fg=self.colors['accent_secondary'],
            bg=self.colors['bg_secondary'],
            cursor='hand2'
        )
        velox_label.pack(side="left")
        velox_label.bind("<Button-1>", lambda e: webbrowser.open("https://github.com/sindresve"))
        
        # Hover effect for the link
        def on_enter(event):
            velox_label.config(fg=['white'])
        
        def on_leave(event):
            velox_label.config(fg=self.colors['accent_secondary'])
        
        velox_label.bind("<Enter>", on_enter)
        velox_label.bind("<Leave>", on_leave)

            
    def setup_content_area(self, parent):
        """Setup main content area"""
        self.content_frame = tk.Frame(parent, bg=self.colors['bg_primary'])
        self.content_frame.pack(side='right', fill='both', expand=True)
        
        # Setup different tabs
        self.setup_home_tab()
        self.setup_settings_tab()
        
        # Show home tab by default
        self.switch_tab('home')
        
    def setup_home_tab(self):
        """Setup home tab content"""
        self.home_frame = tk.Frame(self.content_frame, bg=self.colors['bg_primary'])
        
        # Header
        header_frame = tk.Frame(self.home_frame, bg=self.colors['bg_primary'])
        header_frame.pack(fill='x', padx=30, pady=(30, 20))
        
        title = tk.Label(
            header_frame,
            text="Home",
            font=('Segoe UI', 24, 'bold'),
            fg=self.colors['text_primary'],
            bg=self.colors['bg_primary']
        )
        title.pack(anchor='w')
        
        subtitle = tk.Label(
            header_frame,
            text="Real-time translation of VALORANT chat messages",
            font=('Segoe UI', 12),
            fg=self.colors['text_secondary'],
            bg=self.colors['bg_primary']
        )
        subtitle.pack(anchor='w', pady=(5, 0))
        
        # Control panel
        self.setup_control_panel()
        
        # Output area
        self.setup_output_area()
        
    def setup_control_panel(self):
        """Setup control panel"""
        control_frame = tk.Frame(self.home_frame, bg=self.colors['bg_secondary'])
        control_frame.pack(fill='x', padx=30, pady=(0, 20))
        
        # Inner frame for padding
        inner_frame = tk.Frame(control_frame, bg=self.colors['bg_secondary'])
        inner_frame.pack(fill='x', padx=25, pady=20)
        
        # Title
        control_title = tk.Label(
            inner_frame,
            text="Controls",
            font=('Segoe UI', 14, 'bold'),
            fg=self.colors['text_primary'],
            bg=self.colors['bg_secondary']
        )
        control_title.pack(anchor='w', pady=(0, 15))
        
        # Buttons row
        buttons_frame = tk.Frame(inner_frame, bg=self.colors['bg_secondary'])
        buttons_frame.pack(fill='x')
        
        # Capture button
        self.capture_btn = self.create_rounded_button(
            buttons_frame,
            text=f"📸 Capture & Translate ({self.capture_key})",
            command=self.manual_capture,
            bg=self.colors['accent_primary'],
            fg='white',
            font=('Segoe UI', 11, 'bold'),
            padx=25,
            pady=12,
            state='disabled'
        )
        self.capture_btn.pack(side='left', padx=(0, 15))
        
        # Clear button
        clear_btn = self.create_rounded_button(
            buttons_frame,
            text="🗑️ Clear",
            command=self.clear_output,
            bg=self.colors['bg_tertiary'],
            fg=self.colors['text_primary'],
            font=('Segoe UI', 10),
            padx=20,
            pady=12
        )
        clear_btn.pack(side='right')
        
    def setup_output_area(self):
        """Setup translation output area"""
        output_frame = tk.Frame(self.home_frame, bg=self.colors['bg_secondary'])
        output_frame.pack(fill='both', expand=True, padx=30, pady=(0, 30))
        
        # Header
        output_header = tk.Frame(output_frame, bg=self.colors['bg_secondary'])
        output_header.pack(fill='x', padx=25, pady=(20, 0))
        
        output_title = tk.Label(
            output_header,
            text="Translation Results",
            font=('Segoe UI', 14, 'bold'),
            fg=self.colors['text_primary'],
            bg=self.colors['bg_secondary']
        )
        output_title.pack(anchor='w')
        
        # Text output with proper scrolling
        text_frame = tk.Frame(output_frame, bg=self.colors['bg_secondary'])
        text_frame.pack(fill='both', expand=True, padx=25, pady=(15, 20))
        
        self.output_text = scrolledtext.ScrolledText(
            text_frame,
            font=('Consolas', 11),
            bg=self.colors['bg_tertiary'],
            fg=self.colors['text_primary'],
            insertbackground=self.colors['text_primary'],
            relief='flat',
            wrap='word',
            padx=15,
            pady=15,
            borderwidth=0
        )
        self.output_text.pack(fill='both', expand=True)
        
        # Configure scrollbar style to match theme
        try:
            # Style the scrollbar to match the theme
            style = ttk.Style()
            style.theme_use('clam')
            style.configure("Vertical.TScrollbar", 
                          background=self.colors['bg_tertiary'],
                          troughcolor=self.colors['bg_secondary'],
                          bordercolor=self.colors['border'],
                          arrowcolor=self.colors['text_secondary'],
                          darkcolor=self.colors['bg_tertiary'],
                          lightcolor=self.colors['bg_tertiary'])
        except:
            pass  # If styling fails, use default
        
        # Configure text tags
        self.configure_text_tags()
        
    def setup_settings_tab(self):
        """Setup settings tab content"""
        self.settings_frame = tk.Frame(self.content_frame, bg=self.colors['bg_primary'])
        
        # Header
        header_frame = tk.Frame(self.settings_frame, bg=self.colors['bg_primary'])
        header_frame.pack(fill='x', padx=30, pady=(30, 20))
        
        title = tk.Label(
            header_frame,
            text="Settings",
            font=('Segoe UI', 24, 'bold'),
            fg=self.colors['text_primary'],
            bg=self.colors['bg_primary']
        )
        title.pack(anchor='w')
        
        subtitle = tk.Label(
            header_frame,
            text="Customize your translation experience",
            font=('Segoe UI', 12),
            fg=self.colors['text_secondary'],
            bg=self.colors['bg_primary']
        )
        subtitle.pack(anchor='w', pady=(5, 0))
        
        # Settings sections
        self.setup_key_binding_settings()
        self.setup_capture_area_settings()
        
    def setup_key_binding_settings(self):
        """Setup key binding settings"""
        section_frame = tk.Frame(self.settings_frame, bg=self.colors['bg_secondary'])
        section_frame.pack(fill='x', padx=30, pady=(0, 20))
        
        inner_frame = tk.Frame(section_frame, bg=self.colors['bg_secondary'])
        inner_frame.pack(fill='x', padx=25, pady=20)
        
        # Title
        section_title = tk.Label(
            inner_frame,
            text="Capture Key Binding",
            font=('Segoe UI', 14, 'bold'),
            fg=self.colors['text_primary'],
            bg=self.colors['bg_secondary']
        )
        section_title.pack(anchor='w', pady=(0, 15))
        
        # Key selection
        key_frame = tk.Frame(inner_frame, bg=self.colors['bg_secondary'])
        key_frame.pack(fill='x')
        
        key_label = tk.Label(
            key_frame,
            text="Capture Key:",
            font=('Segoe UI', 11),
            fg=self.colors['text_primary'],
            bg=self.colors['bg_secondary']
        )
        key_label.pack(side='left', padx=(0, 10))
        
        self.key_var = tk.StringVar(value=self.capture_key)
        key_combo = ttk.Combobox(
            key_frame,
            textvariable=self.key_var,
            values=['F1', 'F2', 'F3', 'F4','F5', 'F6', 'F7', 'F8', 'F9', 'F10', 'F11', 'F12'],
            state='readonly',
            font=('Segoe UI', 11),
            width=15
        )
        key_combo.pack(side='left', padx=(0, 15))
        key_combo.bind('<<ComboboxSelected>>', self.update_capture_key)
        
        # Test button
        test_btn = self.create_rounded_button(
            key_frame,
            text="Test Key",
            command=self.test_capture_key,
            bg=self.colors['accent_secondary'],
            fg='white',
            font=('Segoe UI', 10),
            padx=15,
            pady=8
        )
        test_btn.pack(side='left')
        
    def setup_capture_area_settings(self):
        """Setup capture area settings"""
        section_frame = tk.Frame(self.settings_frame, bg=self.colors['bg_secondary'])
        section_frame.pack(fill='x', padx=30, pady=(0, 20))
        
        inner_frame = tk.Frame(section_frame, bg=self.colors['bg_secondary'])
        inner_frame.pack(fill='x', padx=25, pady=20)
        
        # Title
        section_title = tk.Label(
            inner_frame,
            text="Capture Area",
            font=('Segoe UI', 14, 'bold'),
            fg=self.colors['text_primary'],
            bg=self.colors['bg_secondary']
        )
        section_title.pack(anchor='w', pady=(0, 15))
        
        # Current area info
        self.area_info_label = tk.Label(
            inner_frame,
            text="Using default VALORANT chat area",
            font=('Segoe UI', 10),
            fg=self.colors['text_secondary'],
            bg=self.colors['bg_secondary']
        )
        self.area_info_label.pack(anchor='w', pady=(0, 15))
        
        # Buttons
        buttons_frame = tk.Frame(inner_frame, bg=self.colors['bg_secondary'])
        buttons_frame.pack(fill='x')
        
        select_area_btn = self.create_rounded_button(
            buttons_frame,
            text="📐 Select Custom Area",
            command=self.select_capture_area,
            bg=self.colors['accent_primary'],
            fg='white',
            font=('Segoe UI', 11),
            padx=20,
            pady=12
        )
        select_area_btn.pack(side='left', padx=(0, 15))
        
        # Show capture area button
        self.show_area_btn = self.create_rounded_button(
            buttons_frame,
            text="🔍 Show Current Area",
            command=self.toggle_highlight_capture_area,
            bg=self.colors['accent_secondary'],
            fg='white',
            font=('Segoe UI', 11),
            padx=20,
            pady=12
        )
        self.show_area_btn.pack(side='left', padx=(0, 15))
        
        reset_area_btn = self.create_rounded_button(
            buttons_frame,
            text="↺ Reset to Default",
            command=self.reset_capture_area,
            bg=self.colors['bg_tertiary'],
            fg=self.colors['text_primary'],
            font=('Segoe UI', 11),
            padx=20,
            pady=12
        )
        reset_area_btn.pack(side='left')
        
    def setup_footer(self, parent):
        """Setup footer with credits"""
        footer_frame = tk.Frame(parent, bg=self.colors['bg_secondary'], height=40)
        footer_frame.pack(side='bottom', fill='x')
        footer_frame.pack_propagate(False)
        
        credit_label = tk.Label(
            footer_frame,
            text="Created with ❤️ by velox",
            font=('Segoe UI', 10),
            fg=self.colors['text_secondary'],
            bg=self.colors['bg_secondary']
        )
        credit_label.pack(expand=True)
        
    def create_rounded_button(self, parent, text, command, bg, fg, font=('Segoe UI', 10), padx=15, pady=10, state='normal'):
        """Create a modern rounded button"""
        btn = tk.Button(
            parent,
            text=text,
            command=command,
            font=font,
            bg=bg,
            fg=fg,
            relief='flat',
            padx=padx,
            pady=pady,
            cursor='hand2',
            state=state,
            borderwidth=0
        )
        
        # Add hover effects
        original_bg = bg
        hover_bg = self.adjust_color(bg, 0.1)  # Lighter on hover
        
        def on_enter(e):
            if btn['state'] != 'disabled':
                btn.config(bg=hover_bg)
        
        def on_leave(e):
            if btn['state'] != 'disabled':
                btn.config(bg=original_bg)
        
        btn.bind("<Enter>", on_enter)
        btn.bind("<Leave>", on_leave)
        
        return btn
    
    def adjust_color(self, color, factor):
        """Adjust color brightness"""
        # Simple color adjustment - in a real app you'd want more sophisticated color manipulation
        if color == self.colors['accent_primary']:
            return '#2ea043'  # Lighter green
        elif color == self.colors['accent_secondary']:
            return '#388bfd'  # Lighter blue  
        elif color == self.colors['bg_tertiary']:
            return '#30363d'  # Lighter gray
        return color
    
    def toggle_highlight_capture_area(self):
        """Toggle showing current capture area with red highlight"""
        if self.highlight_overlay:
            # Hide existing overlay
            self.highlight_overlay.destroy()
            self.highlight_overlay = None
            self.show_area_btn.config(text="🔍 Show Current Area")
            return
            
        if not self.box_coordinates:
            messagebox.showwarning("No Capture Area", "Please set up screen capture first.")
            return
            
        # Create overlay window
        self.highlight_overlay = tk.Toplevel()
        self.highlight_overlay.attributes('-fullscreen', True)
        self.highlight_overlay.attributes('-alpha', 0.8)
        self.highlight_overlay.configure(bg='black')
        self.highlight_overlay.attributes('-topmost', True)
        self.highlight_overlay.overrideredirect(True)
        
        # Create canvas for drawing
        canvas = tk.Canvas(self.highlight_overlay, bg='black', highlightthickness=0)
        canvas.pack(fill='both', expand=True)
        
        # Draw red rectangle for capture area
        x = self.box_coordinates['left']
        y = self.box_coordinates['top'] 
        w = self.box_coordinates['width']
        h = self.box_coordinates['height']
        
        canvas.create_rectangle(x, y, x + w, y + h, fill='red', outline='')
        
        # Instructions
        text_y = y + h + 20 if y + h + 60 < self.highlight_overlay.winfo_screenheight() else y - 40
        canvas.create_text(
            x + w//2, text_y,
            text="Current Capture Area (Click anywhere to close)",
            font=('Segoe UI', 14, 'bold'),
            fill='white'
        )
        
        # Update button text
        self.show_area_btn.config(text="🙈 Hide Area")
        
        # Close on click
        def close_overlay(event=None):
            if self.highlight_overlay:
                self.highlight_overlay.destroy()
                self.highlight_overlay = None
                self.show_area_btn.config(text="🔍 Show Current Area")
            
        self.highlight_overlay.bind('<Button-1>', close_overlay)
        self.highlight_overlay.bind('<Escape>', close_overlay)
        self.highlight_overlay.focus_set()
        
        # Auto close after 5 seconds
        self.highlight_overlay.after(5000, close_overlay)
        
    def configure_text_tags(self):
        """Configure text tags for output formatting"""
        self.output_text.tag_configure("header", foreground=self.colors['accent_secondary'], font=('Consolas', 11, 'bold'))
        self.output_text.tag_configure("original", foreground=self.colors['warning'])
        self.output_text.tag_configure("translated", foreground=self.colors['success'])
        self.output_text.tag_configure("error", foreground=self.colors['error'])
        self.output_text.tag_configure("info", foreground=self.colors['text_secondary'])
        
    def switch_tab(self, tab_name):
        """Switch between tabs"""
        # Update button states
        for name, btn in self.nav_buttons.items():
            if name == tab_name:
                btn.config(bg=self.colors['accent_secondary'])
                self.current_tab = name
            else:
                btn.config(bg=self.colors['bg_secondary'])
        
        # Hide all frames
        for widget in self.content_frame.winfo_children():
            widget.pack_forget()
        
        # Show selected frame
        if tab_name == 'home':
            self.home_frame.pack(fill='both', expand=True)
        elif tab_name == 'settings':
            self.settings_frame.pack(fill='both', expand=True)
            
    def update_capture_key(self, event=None):
        """Update capture key setting"""
        self.capture_key = self.key_var.get()
        self.save_settings()
        
        # Update button text
        self.capture_btn.config(text=f"📸 Capture & Translate ({self.capture_key})")
        
    def test_capture_key(self):
        """Test the capture key"""
        messagebox.showinfo("Test Key", f"Capture key is set to: {self.capture_key}")
        
    def select_capture_area(self):
        """Open area selection tool with proper visual feedback"""
        self.root.withdraw()  # Hide main window
        
        # Get screen dimensions
        screen_width = self.root.winfo_screenwidth()
        screen_height = self.root.winfo_screenheight()
        
        # Create overlay window
        overlay = tk.Toplevel()
        overlay.attributes('-fullscreen', True)
        overlay.configure(bg='black')
        overlay.attributes('-topmost', True)
        overlay.overrideredirect(True)
        overlay.attributes('-alpha', 0.3)
        
        # Create canvas for drawing selection
        canvas = tk.Canvas(overlay, bg='black', highlightthickness=0, cursor='crosshair')
        canvas.pack(fill='both', expand=True)
        
        # Instructions
        instruction_text = canvas.create_text(
            screen_width//2, 50,
            text="Click and drag to select capture area. Press ESC to cancel.",
            font=('Segoe UI', 16, 'bold'),
            fill='white'
        )
        
        # Selection variables
        self.selection_start = None
        self.selection_rect = None
        
        def on_click(event):
            self.selection_start = (event.x, event.y)
            if self.selection_rect:
                canvas.delete(self.selection_rect)
            
        def on_drag(event):
            if self.selection_start:
                if self.selection_rect:
                    canvas.delete(self.selection_rect)
                
                x1, y1 = self.selection_start
                x2, y2 = event.x, event.y
                
                # Ensure we have positive width and height
                left = min(x1, x2)
                top = min(y1, y2)
                right = max(x1, x2)
                bottom = max(y1, y2)
                
                # Create selection rectangle with white fill and no outline
                self.selection_rect = canvas.create_rectangle(
                    left, top, right, bottom,
                    fill='white',
                    outline='white',
                    width=2,
                    stipple='gray50'  # Make it semi-transparent
                )
                
                # Show dimensions
                width = right - left
                height = bottom - top
                canvas.delete("dimension_text")
                canvas.create_text(
                    left + width//2, top - 20,
                    text=f"{width} × {height}",
                    font=('Segoe UI', 12, 'bold'),
                    fill='white',
                    tags="dimension_text"
                )
                
        def on_release(event):
            if self.selection_start:
                x1, y1 = self.selection_start
                x2, y2 = event.x, event.y
                
                # Calculate final coordinates
                left = min(x1, x2)
                top = min(y1, y2)
                width = abs(x2 - x1)
                height = abs(y2 - y1)
                
                # Minimum size check
                if width < 50 or height < 50:
                    canvas.create_text(
                        screen_width//2, screen_height//2,
                        text="Selection too small! Minimum 50×50 pixels.",
                        font=('Segoe UI', 14, 'bold'),
                        fill='red'
                    )
                    overlay.after(2000, lambda: self.finish_selection(overlay, None))
                    return
                
                self.box_coordinates = {
                    "left": left,
                    "top": top,
                    "width": width,
                    "height": height
                }
                
                # Show confirmation
                canvas.create_text(
                    screen_width//2, screen_height//2,
                    text=f"✓ Area selected: {width}×{height}\nSaving...",
                    font=('Segoe UI', 16, 'bold'),
                    fill='#3fb950'
                )
                
                overlay.after(1000, lambda: self.finish_selection(overlay, self.box_coordinates))
                
        def on_escape(event):
            self.finish_selection(overlay, None)
            
        def on_motion(event):
            # Change cursor to crosshair when moving
            canvas.configure(cursor='crosshair')
            
        # Bind events
        canvas.bind('<Button-1>', on_click)
        canvas.bind('<B1-Motion>', on_drag)
        canvas.bind('<ButtonRelease-1>', on_release)
        canvas.bind('<Motion>', on_motion)
        overlay.bind('<Escape>', on_escape)
        overlay.focus_set()
        
    def finish_selection(self, overlay, coordinates):
        """Finish area selection and clean up"""
        overlay.destroy()
        self.root.deiconify()
        
        if coordinates:
            self.save_settings()
            self.update_area_info()
        
    def reset_capture_area(self):
        """Reset capture area to default"""
        self.box_coordinates = None
        self.save_settings()
        self.setup_screen_capture()  # Recalculate default area
        self.update_area_info()
        
    def update_area_info(self):
        """Update capture area info display"""
        if self.box_coordinates:
            info = f"Custom area: {self.box_coordinates['width']}×{self.box_coordinates['height']} at ({self.box_coordinates['left']}, {self.box_coordinates['top']})"
        else:
            info = "Using default VALORANT chat area"
        self.area_info_label.config(text=info)
        
    def initialize_components(self):
        """Initialize OCR, translator, and screen capture components"""
        def init_thread():
            try:
                # Check CUDA setup
                self.update_status("gpu", "Checking...", "warning")
                cuda_available = self.check_cuda_setup()
                
                # Initialize OCR
                self.update_status("ocr", "Loading...", "warning")
                self.reader, self.using_gpu = self.initialize_ocr_reader(cuda_available)
                self.update_status("ocr", f"Ready ({'GPU' if self.using_gpu else 'CPU'})", "success")
                
                # Initialize translator
                self.update_status("translator", "Connecting...", "warning")
                self.translator = Translator()
                self.update_status("translator", "Ready", "success")
                
                # Setup screen capture
                self.update_status("screen", "Configuring...", "warning")
                self.setup_screen_capture()
                self.update_status("screen", "Ready", "success")
                
                # Enable capture button and start key monitoring
                self.root.after(0, lambda: self.capture_btn.config(state='normal'))
                self.start_key_monitoring()  # Always monitor for key presses
                
                self.log_message("✅ System initialized successfully!", "info")
                
            except Exception as e:
                error_msg = f"Initialization failed: {str(e)}"
                self.log_message(error_msg, "error")
                self.root.after(0, lambda: messagebox.showerror("Initialization Error", error_msg))
        
        init_thread = threading.Thread(target=init_thread, daemon=True)
        init_thread.start()
        
    def update_status(self, component, message, status):
        """Update status indicators"""
        color_map = {
            "success": self.colors['success'],
            "warning": self.colors['warning'],
            "error": self.colors['error']
        }
        
        def update():
            if component in self.status_indicators:
                self.status_indicators[component]['dot'].config(fg=color_map.get(status, self.colors['text_secondary']))
                self.status_indicators[component]['text'].config(text=f"{component.upper()}: {message}")
        
        self.root.after(0, update)
        
    def check_cuda_setup(self):
        """Check CUDA availability"""
        cuda_available = torch.cuda.is_available()
        if cuda_available:
            gpu_name = torch.cuda.get_device_name(0)[:20] + "..."
            self.update_status("gpu", gpu_name, "success")
        else:
            self.update_status("gpu", "CPU mode", "warning")
        return cuda_available
        
    def initialize_ocr_reader(self, cuda_available):
        """Initialize OCR reader with fallback options"""
        for attempt, use_gpu in enumerate([cuda_available, False], 1):
            try:
                reader = easyocr.Reader(
                    ['en', 'ru'],
                    gpu=use_gpu,
                    model_storage_directory=resource_path('models'),
                    download_enabled=True,
                    verbose=False
                )
                return reader, use_gpu
            except Exception as e:
                if attempt == 1 and use_gpu:
                    continue
                else:
                    raise e
        raise Exception("Could not initialize OCR reader")
        
    def setup_screen_capture(self):
        """Setup screen capture area"""
        if self.box_coordinates:
            return  # Use custom area
            
        with mss.mss() as sct:
            monitor = sct.monitors[1]
            
            screen_width = monitor["width"]
            screen_height = monitor["height"]
            
            # Calculate chatbox dimensions
            chatbox_width = round(screen_width * 0.236)
            chatbox_height = round(screen_height * 0.21)
            chatbox_top = round(screen_height * 0.79)
            
            self.box_coordinates = {
                "left": 0,
                "top": chatbox_top,
                "width": chatbox_width,
                "height": chatbox_height
            }
            
            self.monitor_info = monitor
            
    def log_message(self, message, msg_type="info"):
        """Add message to output text with auto-scroll"""
        def add_message():
            # Store current scroll position
            was_at_bottom = self.output_text.yview()[1] == 1.0
            
            timestamp = time.strftime("%H:%M:%S")
            self.output_text.insert('end', f"[{timestamp}] ", "header")
            self.output_text.insert('end', f"{message}\n", msg_type)
            
            # Auto-scroll to bottom if user was already at bottom, or always for new messages
            if was_at_bottom or msg_type in ["info", "header"]:
                self.output_text.see('end')
            
            # Update the display
            self.output_text.update_idletasks()
        
        self.root.after(0, add_message)
        
    def manual_capture(self):
        """Manually trigger capture and translation"""
        if not self.reader or not self.translator:
            messagebox.showwarning("Not Ready", "System is still initializing. Please wait.")
            return
            
        def capture_thread():
            self.capture_and_translate()
            
        thread = threading.Thread(target=capture_thread, daemon=True)
        thread.start()
        
    def start_key_monitoring(self):
        """Start monitoring for capture key press in background"""
        if self.is_running:
            return
            
        self.is_running = True
        
        def monitor_keys():
            try:
                while self.is_running:
                    if keyboard.is_pressed(self.capture_key.lower()):
                        if self.reader and self.translator:
                            self.capture_and_translate()
                        # Debounce
                        while keyboard.is_pressed(self.capture_key.lower()) and self.is_running:
                            time.sleep(0.05)
                        time.sleep(0.2)
                    time.sleep(0.05)
            except Exception as e:
                self.log_message(f"Key monitoring error: {e}", "error")
        
        self.capture_thread = threading.Thread(target=monitor_keys, daemon=True)
        self.capture_thread.start()
        
    def toggle_auto_capture(self):
        """This method is no longer needed but kept for compatibility"""
        pass
        
    def stop_key_monitoring(self):
        """Stop monitoring for capture key press"""
        self.is_running = False
        
    def capture_and_translate(self):
        """Capture screen area and translate detected text"""
        try:
            self.log_message("📸 Capturing screen...", "info")
            
            with mss.mss() as sct:
                screenshot = sct.grab(self.box_coordinates)
                img = np.array(screenshot)
                
                if img.shape[2] == 4:
                    img = img[:, :, :3]  # Remove alpha channel
                    
                # OCR processing
                ocr_params = {
                    'paragraph': False,
                    'detail': 1,
                    'width_ths': 0.7,
                    'height_ths': 0.7
                }
                
                if self.using_gpu:
                    ocr_params.update({
                        'batch_size': 4,
                        'workers': 0
                    })
                
                results = self.reader.readtext(img, **ocr_params)
                
                if results:
                    messages = self.group_text_by_lines(results)
                    
                    if messages:
                        self.log_message("─" * 60, "header")
                        self.log_message("📝 TRANSLATION RESULTS", "header")
                        self.log_message("─" * 60, "header")
                        
                        for i, message in enumerate(messages, 1):
                            if len(message.strip()) < 2:
                                continue
                            if any(term in message.lower() for term in ["(broadcast)", "(system)"]):
                                continue
                                
                            try:
                                translated = self.translator.translate(message, dest='en').text
                                
                                self.log_message(f"\n💬 Message {i}:", "header")
                                self.log_message(f"   Original: {message}", "original")
                                self.log_message(f"   English:  {translated}", "translated")
                                
                            except Exception as e:
                                self.log_message(f"❌ Translation failed for message {i}: {e}", "error")
                                self.log_message(f"   Original text: {message}", "original")
                        
                        self.log_message("─" * 60, "header")
                    else:
                        self.log_message("🔍 No readable messages found.", "info")
                else:
                    self.log_message("👀 No text detected in capture area.", "info")
                    
        except Exception as e:
            self.log_message(f"❌ Capture failed: {e}", "error")
            
    def group_text_by_lines(self, results):
        """Group detected text by vertical position to separate messages"""
        if not results:
            return []
        
        groups = defaultdict(list)
        MESSAGE_SEPARATION_THRESHOLD = 15
        
        for item in results:
            try:
                if len(item) == 3:
                    bbox, text, prob = item
                else:
                    continue
                    
                if isinstance(bbox, list) and len(bbox) >= 4:
                    y_center = (bbox[0][1] + bbox[2][1]) / 2
                else:
                    continue
                
                found_group = None
                for y_pos in groups:
                    if abs(y_pos - y_center) < MESSAGE_SEPARATION_THRESHOLD:
                        found_group = y_pos
                        break
                
                if found_group is None:
                    found_group = y_center
                
                groups[found_group].append((bbox, text, prob))
                
            except Exception as e:
                continue
        
        # Sort groups by vertical position and combine text
        sorted_groups = sorted(groups.items(), key=lambda x: x[0])
        messages = []
        
        for y_pos, group in sorted_groups:
            try:
                group.sort(key=lambda x: x[0][0][0])
                combined_text = " ".join([item[1] for item in group if item[1].strip()])
                if combined_text.strip():
                    messages.append(combined_text.strip())
            except Exception:
                continue
        
        return messages
        
    def clear_output(self):
        """Clear the output text area"""
        self.output_text.delete(1.0, 'end')
        self.log_message("🗑️ Output cleared.", "info")
        
    def on_closing(self):
        """Handle window closing"""
        self.stop_key_monitoring()
        if self.highlight_overlay:
            self.highlight_overlay.destroy()
        self.save_settings()
        self.root.destroy()

def main():
    root = tk.Tk()
    app = ModernOCRTranslatorUI(root)
    
    # Set window icon (if you have an icon file)
    try:
        root.iconbitmap('icon.ico')
    except:
        pass
    
    # Handle window closing
    root.protocol("WM_DELETE_WINDOW", app.on_closing)
    
    # Center window on screen
    root.update_idletasks()
    x = (root.winfo_screenwidth() // 2) - (root.winfo_width() // 2)
    y = (root.winfo_screenheight() // 2) - (root.winfo_height() // 2)
    root.geometry(f"+{x}+{y}")
    
    # Start the GUI
    root.mainloop()

if __name__ == "__main__":
    main()