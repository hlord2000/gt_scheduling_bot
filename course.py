import requests
import json
from bs4 import BeautifulSoup
import logging
import discord
import shelve
import time


class Course:
    def __init__(self, subject="", course="", term=""):
        self.course = course
        self.subject = subject
        self.section = 0
        self.professor = ""
        self.prof_gpa = 0
        self.avg_gpa = 0
        self.gpa_deviation = 0
        self.subjective_score = 0.0
        self.term = term
        self.rmp_link = ""
        self.rmp_score = 0.0
        self.cios_score = 0

    def summarize(self):
        return [
            self.subject,
            self.course,
            self.section,
            self.professor,
            str(self.subjective_score),
            str(self.prof_gpa),
            str(self.avg_gpa),
            str(self.rmp_score),
        ]

    def get_crit(self):
        link = "https://c4citk6s9k.execute-api.us-east-1.amazonaws.com/test/data/course?courseID="
        req = requests.get(link + self.subject + "%20" + self.course).text
        crit_gpas = json.loads(req)
        self.avg_gpa = crit_gpas["header"][0]["avg_gpa"]

    def get_crit_prof(self):
        professor = self.professor
        prof_reversed = self.reverse_prof(professor)
        link = "https://c4citk6s9k.execute-api.us-east-1.amazonaws.com/test/data/course?courseID="
        req = requests.get(link + self.subject + "%20" + self.course).text
        req = json.loads(req)["raw"]
        section_professor = list(
            filter(lambda prof: prof_reversed in prof["instructor_name"], req)
        )
        if len(section_professor) == 1:
            self.prof_gpa = float(section_professor[0]["GPA"])
            self.rmp_link = section_professor[0]["link"]

    def set_rate_my_professor(self):
        if (
            self.rmp_link == "null"
            or self.rmp_link == ""
            or self.rmp_link is None
            or self.rmp_link == "None"
        ):
            pass
        else:
            req = requests.get(self.rmp_link).text
            soup = BeautifulSoup(req, "html.parser")
            score = soup.select('div[class*="RatingValue__Numerator-"]')[0].text
            if self.isDigit(score):
                self.rmp_score = float(score)
            else:
                self.rmp_score = 0.0

    @staticmethod
    def isDigit(x):
        try:
            float(x)
            return True
        except ValueError:
            return False

    def cios_finder(self):
        try:
            with open("cios.json", "r") as file:
                data = json.load(file)
                data = data[str(self.subject + self.course)]
                filtered = list(
                    filter(lambda temp: temp["professor"] == self.professor, data)
                )
                rating_temp = 0
                if len(filtered) != 0 and filtered is not None:
                    for prof in filtered:
                        if any(i.isdigit() for i in str(prof["rating"])):
                            rating_temp += prof["rating"]
                    self.cios_score = round(rating_temp / len(filtered), 2)
                else:
                    self.cios_score = rating_temp
        except KeyError:
            pass

    def subjective_score_creator(self):
        results = []
        normed_gpa = 0
        if str(self.rmp_score).isdigit():
            self.rmp_score = float(self.rmp_score)
        else:
            self.rmp_score = 0.0
        if self.rmp_score == 0:
            results.append(0)
        else:
            results.append(1)
        if self.cios_score == 0:
            results.append(0)
        else:
            results.append(1)
        if self.prof_gpa == 0:
            results.append(0)
        else:
            normed_gpa = ((self.prof_gpa - self.avg_gpa) * 10) / 4
            results.append(1)

        if results == [0, 0, 0]:
            pass
        if results == [1, 0, 0]:
            self.subjective_score = self.rmp_score
        if results == [0, 1, 0]:
            self.subjective_score = self.cios_score
        if results == [0, 0, 1]:
            self.subjective_score = normed_gpa
        if results == [1, 1, 0]:
            self.subjective_score = (self.rmp_score + self.cios_score) / 2
        if results == [0, 1, 1]:
            self.subjective_score = (normed_gpa + self.cios_score) / 2
        if results == [1, 0, 1]:
            self.subjective_score = (normed_gpa + self.rmp_score) / 2
        if results == [1, 1, 1]:
            self.subjective_score = (
                self.cios_score / 5 + float(self.rmp_score) / 5 + normed_gpa
            ) / 3
        self.subjective_score = round(self.subjective_score, 2)

    @staticmethod
    def reverse_prof(professor):
        last_first = professor.split(" ", 1)
        return last_first[1] + ", " + last_first[0]


class DataCollector:
    @staticmethod
    def dept_finder(term_code: str) -> list:
        data = {"cat_term_in": term_code}
        url = "https://oscar.gatech.edu/pls/bprod/bwckctlg.p_disp_cat_term_date"
        try:
            res = requests.post(url, data=data)
        except requests.exceptions:
            res = None
            print("Error in finding departments.")

        soup = BeautifulSoup(res.text, "html.parser")

        selector = soup.find("select", {"name": "sel_subj", "id": "subj_id"})
        departments = []
        for option in selector.findAll("option"):
            departments.append(option["value"])

        return departments

    @staticmethod
    def course_finder(self, term_code, department):
        url = "https://oscar.gatech.edu/pls/bprod/bwskfcls.P_GetCrse"

        data = [
            ("term_in", term_code),
            ("call_proc_in", "bwckctlg.p_disp_dyn_ctlg"),
            ("sel_subj", "dummy"),
            ("sel_subj", department),
            ("sel_levl", "dummy"),
            ("sel_levl", "%"),
            ("sel_schd", "dummy"),
            ("sel_schd", "%"),
            ("sel_coll", "dummy"),
            ("sel_coll", "%"),
            ("sel_divs", "dummy"),
            ("sel_divs", "%"),
            ("sel_dept", "dummy"),
            ("sel_dept", "%"),
            ("sel_attr", "dummy"),
            ("sel_attr", "%"),
            ("sel_crse_strt", ""),
            ("sel_crse_end", ""),
            ("sel_title", ""),
            ("sel_from_cred", ""),
            ("sel_to_cred", ""),
        ]

        response = requests.post(
            "https://oscar.gatech.edu/pls/bprod/bwckctlg.p_display_courses", data=data
        )

        soup = BeautifulSoup(response.text, "html.parser")
        course_names = soup.findAll("td", {"class": "nttitle"})
        courses_found = []
        for course in course_names:
            course_num = course.text[len(department) + 1 : len(department) + 5]
            if course_num.isdigit():
                if int(course_num) >= 1000:
                    courses_found.append(course_num)
        return courses_found

    @staticmethod
    def term_selector(term):
        if type(term) == str:
            term = term.upper()
        else:
            return '202108'

        month = ""
        if "SUMMER" in term:
            month = "05"
        elif "FALL" in term:
            month = "08"
        elif "SPRING" in term:
            month = "02"
        else:
            logging.warning("Month not set, defaulting to most recent term.")
            return "202108"
        return term[-4:] + month


class DataReporting:
    def __init__(self, dept, course, term):
        self.courses = []
        self.summaries = []
        self.output_string = ""
        self.dept = dept
        self.course = course
        self.term = term
        self.array = None
        self.timestamp = None

    def collect_class_data(self):
        shelf = shelve.open("./data/database.shlf")
        term_is = self.term_selector(self.term)
        all_courses = shelf["course_data_" + term_is][
            str(self.dept + self.course)
        ]
        self.courses = all_courses
        self.timestamp = shelf["timestamp"]

    def term_selector(self, term):
        shelf = shelve.open("./data/database.shlf")
        if type(term) == str:
            term = term.upper()
        else:
            self.term = shelf["terms"][0][0]
            return shelf["terms"][0][1]

        month = ""
        if "SUMMER" in term:
            month = "05"
        elif "FALL" in term:
            month = "08"
        elif "SPRING" in term:
            month = "02"
        else:
            logging.warning("Month not set, defaulting to most recent term.")
            self.term = shelf["terms"][0][0]
            return shelf["terms"][0][1]
        return term[-4:] + month

    def format_class_data(self):
        embed = discord.Embed(title=self.dept + self.course + " " + self.term)
        for course in self.courses[0]:
            embed.add_field(name=f'**{course.professor}: {course.section}**',
                        value=f'> Score: {course.subjective_score}\n> GPA: {course.prof_gpa}\n> Avg. GPA: {course.avg_gpa}\n> RMP: {course.rmp_score}',
                        inline=False)
        embed.add_field(name=f'**Last updated:**', value=f"{round((time.time() - self.timestamp)/3600,1)} hours ago")
        return embed