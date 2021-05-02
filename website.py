from course import DataReporting
from flask import Flask, render_template, request
import shelve
import os

app = Flask(__name__, template_folder=os.path.abspath('templates'))


@app.route('/')
def form():
    shelf = shelve.open("./data/database.shlf")
    departments = shelf["departments"]['202108']
    return render_template('form.html', departments=departments)


@app.route('/data/', methods=['POST', 'GET'])
def data():
    if request.method == 'GET':
        return f"The URL /data is accessed directly. Try going to '/form' to submit form"
    if request.method == 'POST':
        form_data = request.form
        course = form_data['course']
        dept = form_data['department_in']
        report = DataReporting(dept, course, 0)
        report.collect_class_data()
        courses = report.courses
        return render_template('data.html', courses=courses)


app.run(host='localhost', port=5000)


"""async def _search(ctx: SlashContext, department: str, coursenum: str, season=None, year=None):
    msg = await ctx.send(f"Working on {department.upper()} {coursenum}!")

    try:
        if type(season) is not str or type(year) is not str:
            report = DataReporting(department, coursenum, 0)
        else:
            report = DataReporting(department, coursenum, str(season + " " + year))
        report.collect_class_data()

        if len(report.courses) > 0:
            await msg.edit(embed=report.format_class_data())
        else:
            await msg.edit(content="Course could not be found.")
    except KeyError:
        await msg.edit(content="Course could not be found.")"""