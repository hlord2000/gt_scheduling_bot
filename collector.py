import shelve
import requests
import json
from bs4 import BeautifulSoup
import os
from course import Course
from course import DataCollector


class OSCAR_API:
    def __init__(self):
        self.filename = "./data/database.shlf"

    # Gathers course data, formats, and saves it to shelf file in ./data
    def get_courses(self):
        # Request from Course Compass API
        response = requests.get(
            "http://gtcoursecompass.com/api/v1/getCourses", verify=False
        ).text
        # If ./data path does not exist, make it
        if not os.path.isdir("./data"):
            os.mkdir("./data")

        # Loads json file from response into list, creates list of dictionaries
        json_list = []
        for x in json.loads(response):
            json_list.append(x)

        # Load to shelf file.
        _shelf = shelve.open(self.filename)
        _shelf["courses"] = json_list
        _shelf.close()

    # Returns course ID given department (i.e. ECE) and course (i.e. 2040)
    def get_course_id(self, department: str, course: str) -> str:

        # Check if ./data path exists
        if os.path.isdir("./data"):
            # Open stored shelf file.
            _shelf = shelve.open(self.filename)
            course_dict: dict = _shelf["courses"]
            _shelf.close()
            # Search list of dictionaries
            for x in course_dict:
                if x["subject"] == department and x["number"] == course:
                    return x["id"]
        else:
            pass

    def get_terms(self):
        # Look for ./data directory
        if not os.path.isdir("./data"):
            os.mkdir("./data")
        # Hardcoded URL for finding terms.
        url = "https://oscar.gatech.edu/pls/bprod/bwckctlg.p_disp_dyn_ctlg"

        try:
            res = requests.get(url)
            soup = BeautifulSoup(res.text, "html.parser")

            # Create list to return all codes given
            term_list = []
            for x in soup.findAll("option"):
                if (
                    x["value"] != "None"
                    and x.text != "None"
                    and len(x.text) <= len("Summer 2020")
                ):
                    term_list.append([x.text, x["value"]])
                else:
                    pass
            _shelf = shelve.open(self.filename)
            _shelf["terms"] = term_list
            _shelf.close()
        except requests.exceptions.ConnectTimeout:
            pass

    @staticmethod
    def get_oscar(subject, course, term):
        subject = subject.upper()
        data = [
            ("term_in", term),
            ("subj_in", subject),
            ("crse_in", course),
            ("schd_in", "%"),
        ]
        response = requests.post(
            "https://oscar.gatech.edu/pls/bprod/bwckctlg.p_disp_listcrse?", data=data
        )
        soup = BeautifulSoup(response.text, "html.parser")

        # this is terrible, don't do this in real life.
        tables = soup.findAll(
            "table",
            {
                "summary": "This table lists the scheduled meeting times and assigned instructors for this class.."
            },
        )
        headings = soup.findAll("th", {"class": "ddtitle"})

        course_objects = [Course("", "", "") for i in range(0, len(tables))]
        for k, i in enumerate(tables):
            rows = i.findAll("tr")
            for j in rows:
                elements = j.findAll("td")
                if len(elements) != 0:
                    course_objects[k].term = term
                    course_objects[k].course = course
                    course_objects[k].subject = subject
                    index = elements[6].text.find(" (P)")
                    names = elements[6].text[:index].split(" ", 2)
                    names = [name.strip().title() for name in names]
                    course_objects[k].professor = names[0] + " " + names[len(names) - 1]
                    head = headings[k].find("a")
                    classes = head.text
                    classes_split = classes.split(" - ", 4)
                    course_objects[k].section = classes_split[3].strip()

        # Returns list of professors
        return course_objects


def collect_term_data():
    oscar = OSCAR_API()
    oscar.get_terms()


def collect_courses():
    oscar = OSCAR_API()
    oscar.get_courses()


def collect_course_data():
    oscar = OSCAR_API()
    shelf = shelve.open("./data/database.shlf")
    terms = [shelf["terms"][0], shelf["terms"][1]]
    for term in terms:
        objects = {}
        i = len(shelf["courses"])
        for course in shelf["courses"]:
            listing = []
            course_objects = oscar.get_oscar(
                course["subject"], course["number"], term[1]
            )
            for x in course_objects:
                x.get_crit()
                x.get_crit_prof()
                x.set_rate_my_professor()
                x.cios_finder()
                x.subjective_score_creator()
            listing.append(course_objects)
            i -= 1
            objects[course["subject"] + course["number"]] = listing
            print(course, i, term)
        key = "course_data_" + str(term[1])
        shelf[key] = objects
    shelf.close()


def update_timestamp():
    timestamp = os.path.getmtime("./data/database.shlf.dat")
    shelf = shelve.open("./data/database.shlf")
    shelf["timestamp"] = timestamp
    shelf.close()


def update_departments():
    shelf = shelve.open("./data/database.shlf")
    dept_dict = {}
    for x in shelf['terms']:
        terms = DataCollector.dept_finder(x[1])
        dept_dict[x[1]] = terms
    shelf['departments'] = dept_dict
    shelf.close()


def update_database():
    collect_term_data()
    collect_courses()
    collect_course_data()
    update_departments()
    update_timestamp()


if __name__ == "__main__":
    update_database()
