import customtkinter as ctk
import requests
from datetime import datetime, timedelta, time
import locale
from CTkTable import CTkTable
import json
import sys
JSON_PATTERN = """
{
    "user" = "jira-user",
    "url" = "jira-url",
    "token" = "jira-token",
}
"""

try:
    with open('config.json', 'r') as file:
        data = json.load(file)
except FileNotFoundError as e:
    sys.exit(f"{e}\nPlease create config.json file according to following pattern:\n{JSON_PATTERN}")

JIRA_USER = data["user"]
JIRA_URL = data["url"]
JIRA_API_TOKEN = data["token"]

URL = f"https://{JIRA_URL}/rest/api/2/search"

headers = {
    "Authorization": f"Bearer {JIRA_API_TOKEN}",
    "Accept": "application/json"
}

def process():
    date_str = day_picker.get_selected_date()

    start_of_day = datetime.combine(date_str, time(0,0,0))
    end_of_day = datetime.combine(date_str, time(23,59,59))

    query = {
    'jql': f'worklogDate >= "{date_str}" AND worklogDate <= "{date_str}" AND worklogAuthor = "{JIRA_USER}"',
    'fields': 'key,summary,worklog',
    'maxResults': 1000
    }

    response = requests.get(URL, headers=headers, params=query)

    if response.status_code != 200:
        status_label.configure(text=f"❌ Error during gathering data from JIRA: {response.status_code}")

    issues = response.json()['issues']
    if not issues:
        status_label.configure(text=f"✅ No time logged")


    total_time_spent = 0
    vals = []

    for issue in issues:
        key = issue['key']
        summary = issue['fields']['summary']
        worklogs = issue['fields']['worklog']['worklogs']

        for worklog in worklogs:
            worklog_date = datetime.strptime(worklog['started'], "%Y-%m-%dT%H:%M:%S.%f%z")
            if worklog_date.date() == start_of_day.date() and worklog['author']['name'] == JIRA_USER:
                time_spent_seconds = worklog.get('timeSpentSeconds', 0)
                time_spent_minutes_raw = int(time_spent_seconds / 60)
                time_spent_hours, time_spent_minutes = divmod(time_spent_minutes_raw, 60)

                total_time_spent += time_spent_seconds
                vals.append([key, f"{time_spent_hours}h {time_spent_minutes}m" if time_spent_hours != 0 else f"{time_spent_minutes}m"])

    total_time_hours, total_time_minutes = divmod(int(total_time_spent / 60), 60)
    if not vals:
        status_label.configure(text=f"No time reported on {date_str}")
        issues_list.clear()
    else:
        status_label.configure(text=f"✅ Overal time reported on {date_str} : {total_time_hours}h {total_time_minutes}m")
        vals.insert(0, ["ID", "Time spent"])
        issues_list.add(vals)


def refresh_data_periodically():
    """ Odświeża dane co minutę """
    process()
    root.after(60000, refresh_data_periodically)

def on_date_change(event):
    """ Funkcja uruchamiana po zmianie daty w DateEntry """
    process()

class DayPicker(ctk.CTkFrame):
    def __init__(self, master=None, **kwargs):
        super().__init__(master, **kwargs)

        self.current_date = datetime.now().date()

        self.prev_button = ctk.CTkButton(self, text="prev", command=self.prev_date, width=50)
        self.prev_button.grid(row=0, column=0, padx=10, pady=10)

        self.date_entry = ctk.CTkEntry(self, width=100, justify='center')
        self.date_entry.grid(row=0, column=1, padx=10, pady=10)
        self.date_entry.insert(0, self.current_date.strftime("%Y-%m-%d"))
        self.date_entry.bind("<Return>", self.update_date_from_entry)

        self.next_button = ctk.CTkButton(self, text="next", command=self.next_date, width=50)
        self.next_button.grid(row=0, column=2, padx=10, pady=10)


    def prev_date(self):
        self.current_date -= timedelta(days=1)
        self.refresh_date_entry()

    def next_date(self):
        self.current_date += timedelta(days=1)
        self.refresh_date_entry()

    def update_date_from_entry(self, event):
        try:
            new_date = datetime.strptime(self.date_entry.get(), "%Y-%m-%d").date()
            self.current_date = new_date
            self.refresh_date_entry()
        except ValueError:
            self.date_entry.delete(0, ctk.END)
            self.date_entry.insert(0, self.current_date.strftime("%Y-%m-%d"))

    def refresh_date_entry(self):
        self.date_entry.delete(0, ctk.END)
        self.date_entry.insert(0, self.current_date.strftime("%Y-%m-%d"))
        process()

    def get_selected_date(self):
        return self.current_date

class IssuesList(ctk.CTkScrollableFrame):
    def __init__(self, master):
        super().__init__(master, width=500)
        self.grid_columnconfigure(0, weight=1)

    def clear(self):
        for widget in self.grid_slaves():
            if isinstance(widget, CTkTable):
                widget.grid_forget()

    def add(self, values):
        self.clear()

        table = CTkTable(master=self, values=values)
        table.grid()


locale.setlocale(locale.LC_ALL, 'en_US.UTF-8')
ctk.set_appearance_mode("dark")
root = ctk.CTk()
root.title("JIRA Widget")
root.geometry("400x400")

root.grid_columnconfigure(0, weight=1)

status_label = ctk.CTkLabel(root, text="", font=("Helvetica", 17))
status_label.grid(pady=25)

issues_list = IssuesList(root)
issues_list.grid(pady=20)

day_picker = DayPicker(root)
day_picker.grid(padx=10, pady=15)

root.after(100, refresh_data_periodically)

root.mainloop()
