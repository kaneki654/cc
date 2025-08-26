from kivy.app import App
from kivy.uix.screenmanager import ScreenManager, Screen, NoTransition
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.gridlayout import GridLayout
from kivy.uix.label import Label
from kivy.uix.textinput import TextInput
from kivy.uix.spinner import Spinner
from kivy.uix.button import Button
from kivy.uix.scrollview import ScrollView
from kivy.uix.popup import Popup
from datetime import datetime
import random
import requests
import threading
from kivy.clock import Clock

# ------------------- CC Validation Functions -------------------

def luhn_check(card_number):
    """Luhn algorithm validation"""
    card_number = ''.join(c for c in card_number if c.isdigit())
    
    digits = [int(d) for d in card_number]
    digits.reverse()
    
    total = 0
    for i, digit in enumerate(digits):
        if i % 2 == 1:
            digit *= 2
            if digit > 9:
                digit -= 9
        total += digit
    
    return total % 10 == 0

def validate_exp_date(month, year):
    """Validate expiration date"""
    try:
        current_date = datetime.now()
        exp_date = datetime(int(year), int(month), 1)
        return exp_date > current_date
    except:
        return False

def validate_cvv(cvv):
    """Validate CVV format"""
    return cvv.isdigit() and len(cvv) in [3, 4]

def get_card_type(card_number):
    """Determine card type from number"""
    card_number = ''.join(c for c in card_number if c.isdigit())
    
    if card_number.startswith('4'):
        return "Visa"
    elif card_number.startswith(('51','52','53','54','55','22','23','24','25','26','27')):
        return "Mastercard"
    elif card_number.startswith(('34','37')):
        return "American Express"
    elif card_number.startswith(('300','301','302','303','304','305','36','38')):
        return "Diners Club"
    elif card_number.startswith(('6011','65','64','622')):
        return "Discover"
    elif card_number.startswith(('35')):
        return "JCB"
    return "Unknown"

def check_bin_info(card_number):
    """Get BIN information from free online databases"""
    try:
        bin_number = card_number[:6]
        url = f"https://lookup.binlist.net/{bin_number}"
        headers = {
            'Accept-Version': '3'
        }
        
        response = requests.get(url, headers=headers, timeout=10)
        if response.status_code == 200:
            data = response.json()
            bank_name = data.get('bank', {}).get('name', 'Unknown Bank')
            country = data.get('country', {}).get('name', 'Unknown Country')
            card_type = data.get('type', 'Unknown Type')
            scheme = data.get('scheme', 'Unknown Scheme')
            
            return f"BIN Info: {bank_name} ({country}) - {card_type} {scheme}"
        else:
            return "BIN Info: Not available"
    except:
        return "BIN Info: Error fetching data"

def generate_check_digit(partial_card):
    """Generate Luhn check digit"""
    partial_card = ''.join(c for c in partial_card if c.isdigit())
    
    digits = [int(d) for d in partial_card]
    digits.reverse()
    
    total = 0
    for i, digit in enumerate(digits):
        if i % 2 == 0:
            digit *= 2
            if digit > 9:
                digit -= 9
        total += digit
    
    return (10 - (total % 10)) % 10

def generate_cc_from_bin(bin_number):
    """Generate valid CC number from BIN"""
    bin_number = ''.join(c for c in bin_number if c.isdigit())
    
    card_type = get_card_type(bin_number)
    if card_type == "American Express":
        card_length = 15
    else:
        card_length = 16
    
    missing_digits = card_length - len(bin_number)
    if missing_digits < 1:
        return "Invalid BIN"
    
    random_digits = ''.join([str(random.randint(0, 9)) for _ in range(missing_digits - 1)])
    partial_card = bin_number + random_digits
    check_digit = generate_check_digit(partial_card)
    return partial_card + str(check_digit)

def generate_exp_date():
    """Generate random expiration date"""
    month = f"{random.randint(1,12):02}"
    year = str(random.randint(datetime.now().year + 1, datetime.now().year + 6))
    return month, year

def generate_cvv():
    """Generate random CVV"""
    return ''.join([str(random.randint(0,9)) for _ in range(3)])

# ------------------- Shared Results Panel -------------------

class ResultsPanel(BoxLayout):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.orientation = "vertical"
        self.padding = 5
        self.spacing = 5
        
        # Store raw CC data for validation
        self.raw_cc_data = []
        self.checking = False
        
        # Add button row at the top
        self.button_row = BoxLayout(size_hint_y=None, height=40, spacing=5)
        self.check_btn = Button(text="Check Generated", background_color=(0, 0.7, 0, 1))
        self.clear_btn = Button(text="Clear Results", background_color=(0.8, 0, 0, 1))
        self.button_row.add_widget(self.check_btn)
        self.button_row.add_widget(self.clear_btn)
        self.add_widget(self.button_row)
        
        # Scrollable output area
        self.scroll = ScrollView(size_hint=(1,1))
        self.output = Label(text="", font_size=14, valign="top", halign="left", size_hint_y=None)
        self.output.bind(texture_size=self.update_height)
        self.scroll.add_widget(self.output)
        self.add_widget(self.scroll)

    def update_height(self, instance, size):
        self.output.height = self.output.texture_size[1]
        self.output.text_size = (self.scroll.width, None)

    def append(self, text, is_cc_data=False):
        self.output.text += text + "\n"
        if is_cc_data and "|" in text and not text.startswith("Generated"):
            self.raw_cc_data.append(text)

    def clear(self):
        self.output.text = ""
        self.raw_cc_data = []
        
    def get_cc_entries(self):
        return self.raw_cc_data

# ------------------- Screens -------------------

class BinScreen(Screen):
    def __init__(self, results_panel, **kwargs):
        super().__init__(**kwargs)
        self.results_panel = results_panel

        layout = BoxLayout(orientation='vertical', padding=20, spacing=10)

        grid = GridLayout(cols=2, spacing=10, size_hint_y=None)

        grid.add_widget(Label(text="Credit Card Number:"))
        self.cc_input = TextInput(multiline=False)
        grid.add_widget(self.cc_input)

        grid.add_widget(Label(text="BIN Length:"))
        self.bin_spinner = Spinner(values=['6','8'], text="6")
        grid.add_widget(self.bin_spinner)

        layout.add_widget(grid)

        btn_row = BoxLayout(size_hint_y=None, height=50, spacing=10)
        extract_btn = Button(text="Extract BIN", background_color=(0,0.6,1,1))
        extract_btn.bind(on_press=self.extract_bin)
        
        check_btn = Button(text="Check BIN Info", background_color=(0,0.8,0,1))
        check_btn.bind(on_press=self.check_bin_info)
        
        btn_row.add_widget(extract_btn)
        btn_row.add_widget(check_btn)
        layout.add_widget(btn_row)

        self.add_widget(layout)

    def extract_bin(self, instance):
        cc_number = self.cc_input.text.strip().replace(" ", "")
        bin_length = int(self.bin_spinner.text)

        if not cc_number or len(cc_number) < bin_length:
            self.show_popup("Error", "Please enter a valid CC number")
            return

        bin_value = cc_number[:bin_length]
        card_type = get_card_type(bin_value)
        self.results_panel.append(f"BIN ({bin_length}): {bin_value} → {card_type}")

    def check_bin_info(self, instance):
        cc_number = self.cc_input.text.strip().replace(" ", "")
        
        if not cc_number or len(cc_number) < 6:
            self.show_popup("Error", "Please enter a valid CC number")
            return

        # Show loading message
        self.results_panel.append("Fetching BIN information...")
        
        # Run in thread to avoid blocking UI
        def fetch_bin_info():
            bin_info = check_bin_info(cc_number)
            Clock.schedule_once(lambda dt: self.results_panel.append(bin_info))
        
        threading.Thread(target=fetch_bin_info, daemon=True).start()

    def show_popup(self, title, message):
        popup = Popup(title=title, content=Label(text=message), size_hint=(0.6, 0.4))
        popup.open()

class GeneratorScreen(Screen):
    def __init__(self, results_panel, **kwargs):
        super().__init__(**kwargs)
        self.results_panel = results_panel

        layout = BoxLayout(orientation='vertical', padding=20, spacing=10)

        grid = GridLayout(cols=2, spacing=10, size_hint_y=None)

        grid.add_widget(Label(text="BIN (First 6+ digits):"))
        self.bin_input = TextInput(multiline=False)
        grid.add_widget(self.bin_input)

        grid.add_widget(Label(text="Number of Cards (1-100):"))
        self.count_spinner = Spinner(values=[str(i) for i in range(1, 101)], text="1")
        grid.add_widget(self.count_spinner)

        layout.add_widget(grid)

        btn = Button(text="Generate Cards", size_hint_y=None, height=50, background_color=(0,0.6,1,1))
        btn.bind(on_press=self.generate_cards)
        layout.add_widget(btn)

        self.add_widget(layout)

    def generate_cards(self, instance):
        bin_input = self.bin_input.text.strip().replace(" ", "")
        count = int(self.count_spinner.text)

        if not bin_input or len(bin_input) < 6:
            self.show_popup("Error", "Please enter a valid BIN (at least 6 digits)")
            return

        self.results_panel.append(f"Generated {count} cards with BIN: {bin_input}")
        
        for i in range(count):
            card = generate_cc_from_bin(bin_input)
            exp_m, exp_y = generate_exp_date()
            cvv = generate_cvv()
            
            # Format based on card type
            card_type = get_card_type(card)
            if card_type == "American Express":
                formatted = f"{card[:4]} {card[4:10]} {card[10:]}"
            else:
                formatted = ' '.join([card[i:i+4] for i in range(0, len(card), 4)])
                
            # Display formatted but store raw for validation
            self.results_panel.append(formatted + f"|{exp_m}|{exp_y}|{cvv}", is_cc_data=True)

    def show_popup(self, title, message):
        popup = Popup(title=title, content=Label(text=message), size_hint=(0.6, 0.4))
        popup.open()

# ------------------- Validation Functions -------------------

def validate_cc_entries(entries):
    """Validate a list of CC entries"""
    results = []
    valid_count = 0
    total_count = 0
    
    for entry in entries:
        if not entry.strip():
            continue
            
        total_count += 1
        try:
            # Parse the entry - remove any spaces from the card number part
            parts = entry.split("|")
            if len(parts) < 4:
                results.append(f"[Invalid Format] {entry}")
                continue
                
            # Clean the card number (remove spaces)
            cc_number = ''.join(c for c in parts[0] if c.isdigit())
            month, year, cvv = parts[1], parts[2], parts[3]
            
            luhn_valid = luhn_check(cc_number)
            exp_valid = validate_exp_date(month, year)
            cvv_valid = validate_cvv(cvv)
            card_type = get_card_type(cc_number)
            is_valid = luhn_valid and exp_valid and cvv_valid
            
            if is_valid:
                valid_count += 1

            # Format the card number for display
            if card_type == "American Express":
                formatted_cc = f"{cc_number[:4]} {cc_number[4:10]} {cc_number[10:]}"
            else:
                formatted_cc = ' '.join([cc_number[i:i+4] for i in range(0, len(cc_number), 4)])

            status = "VALID" if is_valid else "INVALID"
            result_text = f"{formatted_cc} ({card_type}) → {status}"
            
            # Add details for invalid cards
            if not is_valid:
                reasons = []
                if not luhn_valid:
                    reasons.append("Luhn check failed")
                if not exp_valid:
                    reasons.append("Expired or invalid date")
                if not cvv_valid:
                    reasons.append("Invalid CVV")
                result_text += f" [{', '.join(reasons)}]"
            
            results.append(result_text)
            
        except Exception as e:
            results.append(f"[Error processing] {entry}: {str(e)}")

    # Add summary
    results.append(f"\nSummary: {valid_count}/{total_count} valid cards")
    
    return results

# ------------------- Main App -------------------

class CreditCardApp(App):
    def build(self):
        root = BoxLayout(orientation='vertical')

        # Create results panel first
        self.results_panel = ResultsPanel(size_hint_y=0.6)

        # Tab buttons at the TOP
        tab_bar = BoxLayout(size_hint_y=None, height=50, spacing=5, padding=5)
        for name in [("BIN Checker", "bin"), ("Generator", "generator")]:
            btn = Button(text=name[0], background_color=(0.2,0.2,0.2,1), color=(1,1,1,1))
            btn.bind(on_press=lambda inst, scr=name[1]: setattr(sm, 'current', scr))
            tab_bar.add_widget(btn)

        # Screens in the MIDDLE
        sm = ScreenManager(transition=NoTransition())
        sm.add_widget(BinScreen(self.results_panel, name="bin"))
        sm.add_widget(GeneratorScreen(self.results_panel, name="generator"))

        # Layout order: Tabs on top, Screens in middle, Results at bottom
        root.add_widget(tab_bar)
        root.add_widget(sm)
        root.add_widget(self.results_panel)
        
        # Bind buttons
        self.results_panel.check_btn.bind(on_press=self.check_generated_cards)
        self.results_panel.clear_btn.bind(on_press=self.clear_results)
        
        return root
    
    def check_generated_cards(self, instance):
        """Check all generated cards in the results panel"""
        entries = self.results_panel.get_cc_entries()
        
        if not entries:
            self.show_popup("Info", "No generated cards found to check")
            return
            
        # Clear and add validation results
        self.results_panel.clear()
        self.results_panel.append("=== VALIDATION RESULTS ===\n")
        
        validation_results = validate_cc_entries(entries)
        for result in validation_results:
            self.results_panel.append(result)
    
    def clear_results(self, instance):
        """Clear the results panel"""
        self.results_panel.clear()
    
    def show_popup(self, title, message):
        popup = Popup(title=title, content=Label(text=message), size_hint=(0.6, 0.4))
        popup.open()

if __name__ == "__main__":
    CreditCardApp().run()