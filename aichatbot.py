from datetime import datetime
from typing import List, Optional
import json
import os
OpenAI = None
try:
    from openai import OpenAI
except ImportError:
    OpenAI = None


DATE_FMT = "%Y-%m-%d"
def valid_date(e: str) -> bool:
    try:
        datetime.strptime(e, DATE_FMT)
        return True
    except ValueError:
        return False

def parse_date(s: str) -> datetime:
    return datetime.strptime(s, DATE_FMT)

def check_positive(s:str)->float:
    v = float(s)
    if v<= 0:
        raise ValueError('Budget Value must be positive.')
    return v

class Destination:
    def __init__(self, city: str, country: str, start_date: datetime, end_date: datetime, budget: float, activities: List[str]):
        self.city = city
        self.country = country
        self.start_date = start_date
        self.end_date = end_date
        self.budget = budget
        self.activities = activities

    def update_details(self, **kwargs):
        for k, v in kwargs.items():
            if v is None:
                continue
            if hasattr(self,k):
                setattr(self,k,v)
            else:
                raise AttributeError(f"Attribute {k} not found.")

    def to_dict(self):
        return {
            "city": self.city,
            "country": self.country,
            "start_date": self.start_date.strftime(DATE_FMT),
            "end_date": self.end_date.strftime(DATE_FMT),
            "budget": self.budget,
            "activities": self.activities
        }

    @staticmethod
    def from_dict(d):
        return Destination(d["city"], d["country"], datetime.strptime(d["start_date"], DATE_FMT), datetime.strptime(d["end_date"], DATE_FMT), d["budget"], d["activities"])

    def __str__(self):
        act = ",".join(self.activities)
        return f"{self.city},{self.country} | {self.start_date.date()} -> {self.end_date.date()} | Rs.{self.budget:.2f} {act}"

class ItineraryManager:
    def __init__(self, destinations: Optional[List[Destination]] = None):
        self.destinations = destinations or []

    def add_destination(self, destination: Destination):
        self.destinations.append(destination)
        print("Destination added successfully.")

    def remove_destination(self, city:str):
        dlist = [d for d in self.destinations if d.city.lower() == city.lower()]
        if not dlist:
            print("No destination found with the name ",city,".\n")
            return  False
        for dl in dlist:
            self.destinations.remove(dl)
        print(f" Removed destination '{city}'.")
        return True

    def update_destination(self, city:str, **kwargs):
        found = False
        for d in self.destinations:
            if d.city.lower() == city.lower():
                d.update_details(**kwargs)
                print("Updated destination details \n",d)
                found= True
        if not found:
            print("Destination not found. \n")
        return found

    def search_destination(self, s:str):
        s = s.lower()
        res = [d for d in self.destinations if s in d.city.lower() or s in d.country.lower() or any(s in a.lower() for a in d.activities)]
        return res

    def view_all_destinations(self):
        if not self.destinations:
            print("No destinations saved. \n")
            return
        print("Destination list \n"+"="*100)
        print(f"{'Index':<6}{'City':<20}{'Country':<20}{'Start Date':12}{'End Date':<12}{'Budget (Rs.)':10}{'Activities'}")
        print("="*100)
        for i,d in enumerate(self.destinations):
            start = d.start_date if isinstance(d.start_date, str) else d.start_date.strftime(DATE_FMT)
            end = d.end_date if isinstance(d.end_date, str) else d.end_date.strftime(DATE_FMT)
            print(f"{i:<6}{d.city:<20}{d.country:<20}{start:<12}{end:<12}{d.budget:<10.2f}{', '.join(d.activities)}")
        print("=" * 100)

    def save_to_file(self, filename="itineraries.json"):
        with open(filename, "w", encoding="utf-8") as f:
            json.dump([d.to_dict() for d in self.destinations], f, indent=4)

    def load_from_file(self, filename="itineraries.json"):
        if not os.path.exists(filename):
            self.destinations = []
            return
        try:
            with open(filename, "r", encoding="utf-8") as f:
                data = json.load(f)
            self.destinations = [Destination.from_dict(d) for d in data]
        except (IOError, json.JSONDecodeError) as e:
            print(f"Error loading file: {e}")
            self.destinations = []

class AITravelAssistant:
    def __init__(self):
        if OpenAI is None:
            self.client = None
            print("OpenAI not found. \n")
            return
        key = os.getenv("OPENAI_API_KEY")
        if not key:
            self.client = None
            print("OpenAI API key not found. \n")
        else:
            self.client = OpenAI(api_key= key)


    def generate_itinerary(self, dest:Destination):
        if not self.client:
            return "OpenAI set up failure. Install again.\n"
        prompt = (
            f"Create a detailed day-by-day travel itinerary for {dest.city}, {dest.country} "
            f"from {dest.start_date} to {dest.end_date}. Budget: ${dest.budget:.2f}. "
            f"Activities: {', '.join(dest.activities)}.\n"
            "Provide for each day: morning, afternoon, evening suggestions and an estimated cost breakdown."
        )
        try:
            response = self.client.responses.create(
                model="gpt-4o-mini",
                input=prompt,
            )
            text = getattr(response, "output_text", None)
            if not text:
                try:
                    text = response.output[0].content[0].text
                except Exception:
                    text = str(response)
            return text
        except Exception as e:
            return f"OpenAI API error: {e}"


    def generate_budget_tips(self,dest:Destination):
      if not self.client:
        return "AI not configured."
      prompt = (
        f"Provide practical budget-saving tips for a trip to {dest.city}, {dest.country} "
        f"between {dest.start_date} and {dest.end_date} with total budget ${dest.budget:.2f}."
        " Include transport, food, accommodation tips and which activities to prioritize."
      )
      try:
        response = self.client.responses.create(model="gpt-4o-mini", input=prompt)
        text = getattr(response, "output_text", None) or response.output[0].content[0].text
        return text
      except Exception as e:
        return f"OpenAI API error: {e}"

def input_activities():
    s = input("Enter activities (comma separated): ").strip()
    acts = [a.strip() for a in s.split(",") if a.strip()]
    return acts

def add_flow(manager: ItineraryManager):
    city = input("City: ").strip()
    country = input("Country: ").strip()
    start = input("Start date (YYYY-MM-DD): ").strip()
    if not valid_date(start):
        print("Invalid start date format.")
        return
    end = input("End date (YYYY-MM-DD): ").strip()
    if not valid_date(end):
        print("Invalid end date format.")
        return
    try:
        budget = check_positive(input("Budget in Rs: ").strip())
    except Exception as e:
        print("Invalid budget:", e)
        return
    activities = input_activities()
    if not activities:
        print("Please provide at least one activity.")
        return
    # date order check
    if parse_date(start) > parse_date(end):
        print("Start date must be before or equal to end date.")
        return
    d = Destination(city, country, parse_date(start), parse_date(end), budget, activities)
    manager.add_destination(d)

def update_flow(manager: ItineraryManager):
    city = input("Which city do you want to update? ").strip()
    # ask for new values (leave blank to skip)
    new_country = input("New country (blank to keep): ").strip() or None
    new_start = input("New start date YYYY-MM-DD (blank to keep): ").strip() or None
    if new_start and not valid_date(new_start):
        print("Invalid date.")
        return
    new_end = input("New end date YYYY-MM-DD (blank to keep): ").strip() or None
    if new_end and not valid_date(new_end):
        print("Invalid date.")
        return
    new_budget = input("New budget (blank to keep): ").strip() or None
    if new_budget:
        try:
            new_budget = check_positive(new_budget)
        except Exception as e:
            print("Invalid budget:", e)
            return
    new_acts = input("New activities (comma separated, blank to keep): ").strip() or None
    if new_acts:
        new_acts = [a.strip() for a in new_acts.split(",") if a.strip()]
        if not new_acts:
            print("Activities cannot be empty.")
            return
    if new_start:
        new_start = parse_date(new_start)
    if new_end:
        new_end = parse_date(new_end)
    manager.update_destination(city, country=new_country or None, start_date=new_start, end_date=new_end, budget=new_budget, activities=new_acts)

def main():
    manager = ItineraryManager()
    manager.load_from_file()
    ai = AITravelAssistant()

    while True:
        print("\nMenu:")
        print("1. Add Destination")
        print("2. Remove Destination")
        print("3. Update Destination")
        print("4. View All Destinations")
        print("5. Search Destination")
        print("6. AI Travel Assistance")
        print("7. Save Itinerary")
        print("8. Load Itinerary")
        print("9. Exit")
        choice = input("Choose: ").strip()
        if choice == "1":
            add_flow(manager)
        elif choice == "2":
            city = input("City to remove: ").strip()
            manager.remove_destination(city)
        elif choice == "3":
            update_flow(manager)
        elif choice == "4":
            manager.view_all_destinations()
        elif choice == "5":
            term = input("Search term (city/country/activity): ").strip()
            results = manager.search_destination(term)
            if results:
                for r in results:
                    print(r)
            else:
                print("No matches.")
        elif choice == "6":
            manager.view_all_destinations()
            idx = input("Choose destination index for AI help (or 'c' to cancel): ").strip()
            if idx.lower() == 'c':
                continue
            try:
                i = int(idx)
                if i < 0 or i >= len(manager.destinations):
                    print("Invalid index.")
                    continue
                dest = manager.destinations[i]
                print("1) Generate full itinerary")
                print("2) Generate budget tips")
                sub = input("Choose: ").strip()
                if sub == "1":
                    print("Generating itinerary (this calls OpenAI)...")
                    text = ai.generate_itinerary(dest)
                    print("\n--- AI Itinerary ---\n")
                    print(text)
                elif sub == "2":
                    print("Generating budget tips...")
                    text = ai.generate_budget_tips(dest)
                    print("\n--- Budget Tips ---\n")
                    print(text)
                else:
                    print("Canceled.")
            except ValueError:
                print("Invalid input.")
        elif choice == "7":
            manager.save_to_file()
        elif choice == "8":
            manager.load_from_file()
        elif choice == "9":
            manager.save_to_file()
            print("Goodbye — saved and exiting.")
            break
        else:
            print("Invalid choice. Try 1-9.")

if __name__ == "__main__":
    main()


