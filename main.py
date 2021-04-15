import requests
import json
import schedule
from bs4 import BeautifulSoup
import logging
import discord
from discord.ext import commands
import plotly.graph_objects as go
import numpy as np
from discord_slash import SlashCommand, SlashContext
from discord_slash.utils.manage_commands import create_option

class OSCAR_API:

    @staticmethod
    def get_courses():
        response = requests.get('http://gtcoursecompass.com/api/v1/getCourses', verify=False).text
        return json.loads(response)

    @staticmethod
    def get_course_id(department: str, course: str) -> str:
        for x in OSCAR_API.get_courses():
            if x['subject'] == department and x['number'] == course:
                return x['id']
            else:
                pass
    @staticmethod
    def get_course_info(department, course, section):
        course_response = requests.get("http://gtcoursecompass.com/api/v1/getCourse?id=" + OSCAR_API.get_course_id(department, course)).text
        course_info = json.loads(course_response)
        for x in course_info['sections']:
            if x['section'] == section:
                return x['availability']


class Course:
    def __init__(self, course=0, subject=0, term=0):
        self.course = course
        self.subject = subject
        self.section = 0
        self.start = 0
        self.end = 0
        self.professor = ""
        self.prof_gpa = 0
        self.prof_w = 0
        self.avg_gpa = 0
        self.gpa_deviation = 0
        self.skedge_score = 0
        self.days = 0
        self.location = 0
        self.term = term
        self.rmp_score = 0
        self.cios_score = 0
        self.seats = 0
        self.taken_seats = 0
        self.waitlist_available = 0

    def summarize(self):
        return [self.subject, self.course, self.section, self.professor, str(self.skedge_score), str(self.prof_gpa), str(self.avg_gpa), str(self.rmp_score)]

    def get_crit_avg_gpa(self):
        req = requests.get(
            "https://c4citk6s9k.execute-api.us-east-1.amazonaws.com/test/data/course?courseID={sub}%20{cour}".format(sub=self.subject, cour=self.course))
        dict = json.loads(req.text)
        self.avg_gpa = dict['header'][0]['avg_gpa']

    @staticmethod
    def reverse_prof(professor):
        last_first = professor.split(" ", 1)
        return last_first[1] + ", " + last_first[0]

    def get_crit_prof_gpa(self):
        professor = self.professor
        prof_reversed = self.reverse_prof(professor)
        req = requests.get(
            "https://c4citk6s9k.execute-api.us-east-1.amazonaws.com/test/data/course?courseID={sub}%20{cour}".format(sub=self.subject, cour=self.course))
        dict = json.loads(req.text)['raw']
        section_professor = list(filter(lambda prof: prof_reversed in prof['instructor_name'], dict))
        if len(section_professor) == 1:
            self.prof_gpa = float(section_professor[0]['GPA'])
            self.prof_w = int(section_professor[0]['W'])

    def set_rate_my_professor(self):
        with open("data.json", 'r') as file:
            data = json.load(file)
            try:
                score = data[self.professor]
            except KeyError:
                score = 0
            self.rmp_score = float(score)

    def cios_finder(self):
        with open("cios.json", 'r') as file:
            data = json.load(file)
            data = data[str(self.subject + self.course)]
            filtered = list(filter(lambda temp: temp['professor'] == self.professor, data))
            rating_temp = 0
            if len(filtered) != 0 and filtered is not None:
                for prof in filtered:
                    if any(i.isdigit() for i in str(prof['rating'])):
                        rating_temp += prof['rating']
                self.cios_score = round(rating_temp / len(filtered),2)
            else:
                self.cios_score = rating_temp

    def subjective_score(self):
        results = []
        normed_gpa = (((self.prof_gpa - self.avg_gpa)*10) / 4)
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
            results.append(1)

        if results == [0,0,0]:
            pass
        if results == [1,0,0]:
            self.skedge_score = self.rmp_score
        if results == [0,1,0]:
            self.skedge_score = self.cios_score
        if results == [0,0,1]:
            self.skedge_score = normed_gpa
        if results == [1,1,0]:
            self.skedge_score = (self.rmp_score + self.cios_score)/2
        if results == [0,1,1]:
            self.skedge_score = (normed_gpa + self.cios_score)/2
        if results == [1,0,1]:
            self.skedge_score = (normed_gpa + self.rmp_score)/2
        if results == [1,1,1]:
            self.skedge_score = (self.cios_score/5 + self.rmp_score/5 + normed_gpa)/3
        print(self.cios_score, self.rmp_score, normed_gpa)
        self.skedge_score = round(self.skedge_score,2)

class DataCollector:
    def get_oscar(self, term, subject, course):
        subject = subject.upper()
        data = [
            ('term_in', term),
            ('subj_in', subject),
            ('crse_in', course),
            ('schd_in', '%')
        ]
        response = requests.post('https://oscar.gatech.edu/pls/bprod/bwckctlg.p_disp_listcrse?', data=data)
        soup = BeautifulSoup(response.text, 'html.parser')

        # this is terrible, don't do this in real life.
        tables = soup.findAll("table", {
            'summary': 'This table lists the scheduled meeting times and assigned instructors for this class..'})
        headings = soup.findAll("th", {"class": "ddtitle"})

        course_objects = [Course(0, 0, 0) for i in range(0, len(tables))]
        for k, i in enumerate(tables):
            rows = i.findAll("tr")
            for j in rows:
                elements = j.findAll("td")
                if len(elements) != 0:
                    time = elements[1].text.split("-", 1)
                    if "TBA" not in time:
                        course_objects[k].start = time[0].strip()
                        course_objects[k].end = time[1].strip()
                    else:
                        course_objects[k].start = "REMOVE"
                        course_objects[k].end = "REMOVE"
                    course_objects[k].days = elements[2].text
                    course_objects[k].location = elements[3].text
                    course_objects[k].term = term
                    course_objects[k].course = course
                    course_objects[k].subject = subject
                    index = elements[6].text.find(" (P)")
                    names = elements[6].text[:index].split(' ', 2)
                    names = [name.strip().title() for name in names]
                    course_objects[k].professor = names[0] + " " + names[len(names)-1]
                    head = headings[k].find("a")
                    classes = head.text
                    classes_split = classes.split(" - ", 4)
                    course_objects[k].section = classes_split[3].strip()

        # Returns list of professors
        return course_objects

    @staticmethod
    def term_finder() -> list:
        # Hardcoded URL for finding terms.
        url = "https://oscar.gatech.edu/pls/bprod/bwckctlg.p_disp_dyn_ctlg"
        res = None
        try:
            res = requests.get(url)
        except:
            print("Error in finding terms.")
        # Parse with BS4
        soup = BeautifulSoup(res.text, 'html.parser')

        # Create list to return all codes given
        term_list = []
        for x in soup.findAll('option'):
            if x['value'] != 'None' and x.text != 'None' and len(x.text) <= len("Summer 2020"):
                term_list.append([x.text, x['value']])
            else:
                pass
        return term_list

    def dept_finder(self, term_code: str) -> list:
        data = {'cat_term_in': term_code}
        url = 'https://oscar.gatech.edu/pls/bprod/bwckctlg.p_disp_cat_term_date'
        try:
            res = requests.post(url, data=data)
        except requests.exceptions:
            res = None
            print("Error in finding departments.")

        soup = BeautifulSoup(res.text, 'html.parser')

        selector = soup.find('select', {'name': 'sel_subj', 'id': 'subj_id'})
        departments = []
        for option in selector.findAll('option'):
            departments.append(option['value'])

        return departments

    def course_finder(self, term_code, department):
        url = 'https://oscar.gatech.edu/pls/bprod/bwskfcls.P_GetCrse'

        data = [
            ('term_in', term_code),
            ('call_proc_in', 'bwckctlg.p_disp_dyn_ctlg'),
            ('sel_subj', 'dummy'),
            ('sel_subj', department),
            ('sel_levl', 'dummy'),
            ('sel_levl', '%'),
            ('sel_schd', 'dummy'),
            ('sel_schd', '%'),
            ('sel_coll', 'dummy'),
            ('sel_coll', '%'),
            ('sel_divs', 'dummy'),
            ('sel_divs', '%'),
            ('sel_dept', 'dummy'),
            ('sel_dept', '%'),
            ('sel_attr', 'dummy'),
            ('sel_attr', '%'),
            ('sel_crse_strt', ''),
            ('sel_crse_end', ''),
            ('sel_title', ''),
            ('sel_from_cred', ''),
            ('sel_to_cred', ''),
        ]

        response = requests.post('https://oscar.gatech.edu/pls/bprod/bwckctlg.p_display_courses', data=data)

        soup = BeautifulSoup(response.text, 'html.parser')
        course_names = soup.findAll("td", {"class": "nttitle"})
        courses_found = []
        for course in course_names:
            course_num = course.text[len(department) + 1:len(department) + 5]
            if course_num.isdigit():
                if int(course_num) >= 1000:
                    courses_found.append(course_num)
        return courses_found

    @staticmethod
    def term_selector(term):
        if type(term) == str:
            term = term.upper()
        else:
            return DataCollector.term_finder()[0][1]

        month = ""
        if "SUMMER" in term:
            month = "05"
        elif "FALL" in term:
            month = "08"
        elif "SPRING" in term:
            month = "02"
        else:
            logging.warning("Month not set, defaulting to most recent term.")
            return DataCollector.term_finder()[0][1]
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

    def collect_class_data(self):
        data_collector = DataCollector()
        term_code = data_collector.term_selector(self.term)
        all_courses = []

        individuals = data_collector.get_oscar(term_code, self.dept, self.course)
        for individual in individuals:
            individual.get_crit_avg_gpa()
            individual.get_crit_prof_gpa()
            individual.set_rate_my_professor()
            try:
                individual.cios_finder()
            except:
                pass
            individual.subjective_score()
            all_courses.append(individual)

        all_courses.sort(key=lambda individual: individual.skedge_score, reverse=True)

        self.courses = all_courses

    def format_class_data(self):
        for x in self.courses:
            self.summaries.append(x.summarize())
        self.array = np.array(self.summaries).T.tolist()



if __name__ == "__main__":

    description = '''A bot intended to make Georgia Tech's class search
    LESS TERRIBLE'''

    bot = commands.Bot(command_prefix="!", description=description)

    slash = SlashCommand(bot, sync_commands=True)
    guild_ids = [797968601575325707, 575726573852819508, 760550078448140346]

    @bot.event
    async def on_ready():
        print("ready, sama")


    @slash.slash(name="search",
                 description="Input your department, course number, season, and year to search.",
                 options = [
                     create_option(
                         name="department",
                         description="Input department code, e.g. ECE",
                         option_type=3,
                         required=True
                     ),
                     create_option(
                         name="coursenum",
                         description="Input course number, e.g. 2031",
                         option_type=3,
                         required=True
                     ),
                     create_option(
                         name="season",
                         description="Input season, e.g. Fall",
                         option_type=3,
                         required=False
                     ),
                     create_option(
                         name="year",
                         description="Input year, e.g. 1969",
                         option_type=3,
                         required=False
                     ),
                 ],
                 guild_ids=guild_ids)
    async def _search(ctx: SlashContext, department: str, coursenum: str, season=None, year=None):
        await ctx.send(f"Working on {department.upper()} {coursenum}!")


        if type(season) is not str or type(year) is not str:
            report = DataReporting(department, coursenum, 0)
        else:
            report = DataReporting(department, coursenum, str(season+" "+year))
        report.collect_class_data()
        report.format_class_data()
        if len(report.summaries) > 0:
            fig = go.Figure(data=[go.Table(header=dict(
                values=['Dept.', 'Course', 'Section', 'Prof.', 'Score (out of 5)', 'GPA', 'AVG Crse. GPA', "RMP"]),
                cells=dict(values=report.array))
            ])
            fig.write_image("image.png", scale=1.0, height=max(100 * len(report.summaries),300), width=1000)

            with open("image.png", "rb") as f:
                picture = discord.File(f)
            await ctx.send(file=picture)
        else:
            await ctx.send("Course could not be found.")

    bot.run("ODMxMDY2MDY0NTI3MTYzNDEz.YHP0lg.6_668XbbTuXKASU-DNEZLYOXeaI")